from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import re
import uuid
from datetime import datetime
import requests
from duckduckgo_search import DDGS
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__, static_folder='../public')
CORS(app)

CREDENTIALS = os.environ.get('GOOGLE_CREDENTIALS', '')
SHEETS_ID = os.environ.get('SHEETS_ID', '1Msa6QeeOW2mrnYnU1LrjNvOcpwBPUGPfbenD1L98-IY')
TAVILY_KEY = os.environ.get('TAVILY_API_KEY', '')

USERS = {
    'NVARNALI': {'ad': 'N. VARNALI', 'rol': 'KULLANICI'},
    'ACOMERT': {'ad': 'A. COMERT', 'rol': 'KULLANICI'},
    'CTURHAN': {'ad': 'C. TURHAN', 'rol': 'GOZLEMCI'}
}

# 5 satın alma safhası
SAFHALAR = [
    {'id': 1, 'kod': 'ARASTIRMA', 'ad': 'Fiyat Teklifi Toplanması'},
    {'id': 2, 'kod': 'SECIM',     'ad': 'En Doğru Fiyat Seçimi'},
    {'id': 3, 'kod': 'CARI',      'ad': 'Cari Hesap / AS400 İşlemi'},
    {'id': 4, 'kod': 'KONTROL',   'ad': 'İş Bitimi Kontrol & Teyit'},
    {'id': 5, 'kod': 'FATURA',    'ad': 'Fatura & Ödeme Takibi'},
]

def get_creds():
    if CREDENTIALS:
        creds_dict = json.loads(CREDENTIALS)
        return Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'])
    return Credentials.from_service_account_file('credentials.json', scopes=[
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'])

def get_gspread():
    return gspread.authorize(get_creds())

def get_spreadsheet():
    return get_gspread().open_by_key(SHEETS_ID)

def get_worksheet(name):
    sh = get_spreadsheet()
    try:
        return sh.worksheet(name)
    except:
        return sh.add_worksheet(title=name, rows=2000, cols=30)

def gen_id():
    return datetime.now().strftime('%Y%m%d') + '-' + str(uuid.uuid4())[:8].upper()

def get_user(request):
    return request.headers.get('X-User', 'ACOMERT')

def now_str():
    return datetime.now().strftime('%d.%m.%Y %H:%M')

def today_str():
    return datetime.now().strftime('%d.%m.%Y')

# ========== INIT ==========

@app.route('/')
def index():
    return send_from_directory('../public', 'index.html')

@app.route('/api/init', methods=['POST'])
def init_system():
    try:
        sh = get_spreadsheet()
        # Tüm mevcut sayfaları sil, temiz başlat
        existing = sh.worksheets()
        
        sheets_def = {
            'Personel': ['ID','KullaniciAdi','Ad','Rol','AktifMi','EklemeTarihi'],
            'Isler': [
                'ID','Olusturan','AtananKisiler','Hizmet','Aciklama',
                'Baslangic','HedefBitis','GercekBitis',
                'MevcutSafha','Durum',
                'FirmaId','FirmaAd',
                'TeklifId','FaturaId',
                'AS400Islendi','Notlar','GuncellenmeTarihi'
            ],
            'Firmalar': [
                'ID','Ekleyen','Ad','Telefon','Eposta','Adres',
                'Konum','Hizmet','Web','Durum','Tarih','Notlar'
            ],
            'Teklifler': [
                'ID','IsId','Ekleyen','FirmaId','FirmaAd','Hizmet',
                'Tutar','ParaBirimi','KDVOrani','KDVTutar','ToplamTutar',
                'Kaynak','Tarih','Vade','Durum','Secildi','Notlar'
            ],
            'Faturalar': [
                'ID','IsId','Ekleyen','FirmaId','FirmaAd','FaturaNo',
                'Tutar','ParaBirimi','KDVOrani','KDVTutar','ToplamTutar',
                'FaturaTarihi','VadeTarihi','OdemeDurumu','OdemeTarihi',
                'AS400Ref','Notlar'
            ],
            'ZamanCizelgesi': [
                'ID','IsId','Kullanici','Safha','SafhaKod',
                'Aksiyon','Aciklama','Tarih','Tip'
            ],
            'OnayGozlemler': [
                'ID','IsId','Gozlemci','Tarih','Yorum','SafhaDurumu'
            ],
            'ArastirmaGecmisi': [
                'ID','Kullanici','Tarih','Query','Konum','SonucSayisi','Sonuclar'
            ],
        }
        
        existing_titles = [ws.title for ws in existing]
        # Sheet1 varsa koru (silemeyiz tek sayfa varsa)
        created = []
        for title, headers in sheets_def.items():
            if title in existing_titles:
                ws = sh.worksheet(title)
                ws.clear()
                ws.append_row(headers)
            else:
                ws = sh.add_worksheet(title=title, rows=2000, cols=len(headers))
                ws.append_row(headers)
            created.append(title)
        
        # Varsayılan personel ekle
        ws_p = sh.worksheet('Personel')
        for u, info in USERS.items():
            ws_p.append_row([gen_id(), u, info['ad'], info['rol'], 'EVET', today_str()])
        
        return jsonify({'success': True, 'created': created})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/safhalar', methods=['GET'])
def get_safhalar():
    return jsonify({'success': True, 'data': SAFHALAR})

@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify({'success': True, 'data': USERS})

# ========== PERSONEL ==========

@app.route('/api/personel', methods=['GET'])
def list_personel():
    try:
        ws = get_worksheet('Personel')
        data = ws.get_all_records()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/personel', methods=['POST'])
def create_personel():
    try:
        user = get_user(request)
        if USERS.get(user, {}).get('rol') != 'GOZLEMCI':
            return jsonify({'success': False, 'error': 'Yetki yok'}), 403
        ws = get_worksheet('Personel')
        data = request.json
        row = [gen_id(), data.get('kullaniciAdi',''), data.get('ad',''),
               data.get('rol','KULLANICI'), 'EVET', today_str()]
        ws.append_row(row)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== İŞLER ==========

@app.route('/api/isler', methods=['GET'])
def list_isler():
    try:
        user = get_user(request)
        ws = get_worksheet('Isler')
        data = ws.get_all_records()
        # GOZLEMCI tüm işleri görür, kullanıcılar kendi işlerini
        if USERS.get(user, {}).get('rol') == 'GOZLEMCI':
            pass
        else:
            data = [x for x in data if
                    x.get('Olusturan') == user or
                    user in str(x.get('AtananKisiler', ''))]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/is', methods=['POST'])
def create_is():
    try:
        user = get_user(request)
        ws = get_worksheet('Isler')
        d = request.json
        is_id = gen_id()
        atanan = d.get('atananKisiler', user)
        row = [
            is_id, user, atanan,
            d.get('hizmet',''), d.get('aciklama',''),
            d.get('baslangic', today_str()), d.get('hedefBitis',''), '',
            'ARASTIRMA', 'DEVAM',
            d.get('firmaId',''), d.get('firmaAd',''),
            '', '', 'HAYIR',
            d.get('notlar',''), now_str()
        ]
        ws.append_row(row)
        # Zaman çizelgesine ilk kayıt
        _zaman_ekle(is_id, user, 'ARASTIRMA', 'ARASTIRMA', 'İŞ OLUŞTURULDU', d.get('hizmet',''), 'BASLANGIÇ')
        return jsonify({'success': True, 'id': is_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/is/<is_id>/safha', methods=['POST'])
def update_safha(is_id):
    try:
        user = get_user(request)
        ws = get_worksheet('Isler')
        d = request.json
        yeni_safha = d.get('safha')
        aciklama = d.get('aciklama','')
        
        all_data = ws.get_all_values()
        headers = all_data[0]
        safha_col = headers.index('MevcutSafha') + 1
        guncelleme_col = headers.index('GuncellenmeTarihi') + 1
        
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[0] == is_id:
                ws.update_cell(i+1, safha_col, yeni_safha)
                ws.update_cell(i+1, guncelleme_col, now_str())
                safha_ad = next((s['ad'] for s in SAFHALAR if s['kod']==yeni_safha), yeni_safha)
                _zaman_ekle(is_id, user, safha_ad, yeni_safha, 'SAFHA GÜNCELLENDİ', aciklama, 'SAFHA')
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'İş bulunamadı'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/is/<is_id>/as400', methods=['POST'])
def mark_as400(is_id):
    try:
        user = get_user(request)
        ws = get_worksheet('Isler')
        d = request.json
        ref = d.get('ref','')
        all_data = ws.get_all_values()
        headers = all_data[0]
        as400_col = headers.index('AS400Islendi') + 1
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[0] == is_id:
                ws.update_cell(i+1, as400_col, f'EVET - {ref} - {now_str()}')
                _zaman_ekle(is_id, user, 'Cari Hesap / AS400', 'CARI', 'AS400 İŞLENDİ', f'Ref: {ref}', 'AS400')
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Bulunamadı'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/is/<is_id>', methods=['DELETE'])
def delete_is(is_id):
    try:
        user = get_user(request)
        ws = get_worksheet('Isler')
        all_data = ws.get_all_values()
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[0] == is_id and (row[1] == user or USERS.get(user,{}).get('rol')=='GOZLEMCI'):
                ws.delete_row(i+1)
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Bulunamadı'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== FİRMALAR ==========

@app.route('/api/firmalar', methods=['GET'])
def list_firmalar():
    try:
        ws = get_worksheet('Firmalar')
        data = ws.get_all_records()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/firma', methods=['POST'])
def create_firma():
    try:
        user = get_user(request)
        ws = get_worksheet('Firmalar')
        d = request.json
        row = [gen_id(), user, d.get('ad',''), d.get('telefon',''), d.get('eposta',''),
               d.get('adres',''), d.get('konum',''), d.get('hizmet',''), d.get('web',''),
               'AKTIF', today_str(), d.get('notlar','')]
        ws.append_row(row)
        return jsonify({'success': True, 'id': row[0]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/firma/<firma_id>', methods=['DELETE'])
def delete_firma(firma_id):
    try:
        ws = get_worksheet('Firmalar')
        all_data = ws.get_all_values()
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[0] == firma_id:
                ws.delete_row(i+1)
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Bulunamadı'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/firmalar/delete-many', methods=['POST'])
def delete_many_firmalar():
    try:
        ws = get_worksheet('Firmalar')
        ids = request.json.get('ids', [])
        all_data = ws.get_all_values()
        rows_to_delete = []
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[0] in ids:
                rows_to_delete.append(i+1)
        for row_idx in sorted(rows_to_delete, reverse=True):
            ws.delete_row(row_idx)
        return jsonify({'success': True, 'deleted': len(rows_to_delete)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== TEKLİFLER ==========

@app.route('/api/teklifler', methods=['GET'])
def list_teklifler():
    try:
        user = get_user(request)
        ws = get_worksheet('Teklifler')
        data = ws.get_all_records()
        if USERS.get(user,{}).get('rol') != 'GOZLEMCI':
            data = [x for x in data if x.get('Ekleyen') == user]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/teklif', methods=['POST'])
def create_teklif():
    try:
        user = get_user(request)
        ws = get_worksheet('Teklifler')
        d = request.json
        tutar = float(d.get('tutar', 0))
        kdv = float(d.get('kdvOrani', 20))
        kdv_tutar = tutar * kdv / 100
        toplam = tutar + kdv_tutar
        teklif_id = gen_id()
        row = [
            teklif_id, d.get('isId',''), user,
            d.get('firmaId',''), d.get('firmaAd',''), d.get('hizmet',''),
            tutar, d.get('paraBirimi','TRY'), kdv, kdv_tutar, toplam,
            d.get('kaynak',''), today_str(), d.get('vade','30'),
            'BEKLEMEDE', 'HAYIR', d.get('notlar','')
        ]
        ws.append_row(row)
        if d.get('isId'):
            _zaman_ekle(d['isId'], user, 'Fiyat Teklifi Toplanması', 'ARASTIRMA',
                        f'TEKLİF ALINDI: {d.get("firmaAd","")}',
                        f'{toplam} {d.get("paraBirimi","TRY")} (KDV dahil)', 'TEKLİF')
        return jsonify({'success': True, 'id': teklif_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/teklif/<teklif_id>/sec', methods=['POST'])
def sec_teklif(teklif_id):
    try:
        user = get_user(request)
        ws = get_worksheet('Teklifler')
        d = request.json
        is_id = d.get('isId','')
        all_data = ws.get_all_values()
        headers = all_data[0]
        secildi_col = headers.index('Secildi') + 1
        durum_col = headers.index('Durum') + 1
        
        # Önce aynı işteki diğer teklifleri HAYIR yap
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[headers.index('IsId')] == is_id:
                ws.update_cell(i+1, secildi_col, 'HAYIR')
                ws.update_cell(i+1, durum_col, 'RED')
        
        # Seçilen teklifi güncelle
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[0] == teklif_id:
                ws.update_cell(i+1, secildi_col, 'EVET')
                ws.update_cell(i+1, durum_col, 'KABUL')
                firma_ad = row[headers.index('FirmaAd')]
                toplam = row[headers.index('ToplamTutar')]
                para = row[headers.index('ParaBirimi')]
                _zaman_ekle(is_id, user, 'En Doğru Fiyat Seçimi', 'SECIM',
                            f'TEKLİF SEÇİLDİ: {firma_ad}',
                            f'{toplam} {para} tutarlı teklif kabul edildi', 'SECIM')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/teklif/<teklif_id>', methods=['DELETE'])
def delete_teklif(teklif_id):
    try:
        ws = get_worksheet('Teklifler')
        all_data = ws.get_all_values()
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[0] == teklif_id:
                ws.delete_row(i+1)
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Bulunamadı'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== FATURALAR ==========

@app.route('/api/faturalar', methods=['GET'])
def list_faturalar():
    try:
        user = get_user(request)
        ws = get_worksheet('Faturalar')
        data = ws.get_all_records()
        if USERS.get(user,{}).get('rol') != 'GOZLEMCI':
            data = [x for x in data if x.get('Ekleyen') == user]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/fatura', methods=['POST'])
def create_fatura():
    try:
        user = get_user(request)
        ws = get_worksheet('Faturalar')
        d = request.json
        tutar = float(d.get('tutar', 0))
        kdv = float(d.get('kdvOrani', 20))
        kdv_tutar = tutar * kdv / 100
        toplam = tutar + kdv_tutar
        fatura_id = gen_id()
        row = [
            fatura_id, d.get('isId',''), user,
            d.get('firmaId',''), d.get('firmaAd',''), d.get('faturaNo',''),
            tutar, d.get('paraBirimi','TRY'), kdv, kdv_tutar, toplam,
            today_str(), d.get('vadeTarihi',''), 'BEKLIYOR', '', '', d.get('notlar','')
        ]
        ws.append_row(row)
        if d.get('isId'):
            _zaman_ekle(d['isId'], user, 'Fatura & Ödeme Takibi', 'FATURA',
                        f'FATURA GİRİLDİ: No {d.get("faturaNo","")}',
                        f'{toplam} {d.get("paraBirimi","TRY")} - Vade: {d.get("vadeTarihi","")}', 'FATURA')
        return jsonify({'success': True, 'id': fatura_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/fatura/<fatura_id>/odeme', methods=['POST'])
def odeme_isle(fatura_id):
    try:
        user = get_user(request)
        ws = get_worksheet('Faturalar')
        d = request.json
        all_data = ws.get_all_values()
        headers = all_data[0]
        od_col = headers.index('OdemeDurumu') + 1
        ot_col = headers.index('OdemeTarihi') + 1
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[0] == fatura_id:
                ws.update_cell(i+1, od_col, 'ODENDI')
                ws.update_cell(i+1, ot_col, today_str())
                is_id = row[headers.index('IsId')]
                fatura_no = row[headers.index('FaturaNo')]
                if is_id:
                    _zaman_ekle(is_id, user, 'Fatura & Ödeme Takibi', 'FATURA',
                                f'ÖDEME YAPILDI: {fatura_no}', d.get('not',''), 'ODEME')
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Bulunamadı'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/fatura/<fatura_id>', methods=['DELETE'])
def delete_fatura(fatura_id):
    try:
        ws = get_worksheet('Faturalar')
        all_data = ws.get_all_values()
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[0] == fatura_id:
                ws.delete_row(i+1)
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Bulunamadı'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== ZAMAN ÇİZELGESİ ==========

def _zaman_ekle(is_id, kullanici, safha, safha_kod, aksiyon, aciklama, tip):
    try:
        ws = get_worksheet('ZamanCizelgesi')
        ws.append_row([gen_id(), is_id, kullanici, safha, safha_kod,
                       aksiyon, aciklama, now_str(), tip])
    except Exception as e:
        print(f"Zaman çizelgesi hatası: {e}")

@app.route('/api/zaman/<is_id>', methods=['GET'])
def get_zaman(is_id):
    try:
        ws = get_worksheet('ZamanCizelgesi')
        data = ws.get_all_records()
        data = [x for x in data if x.get('IsId') == is_id]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/zaman/<is_id>', methods=['POST'])
def add_zaman(is_id):
    try:
        user = get_user(request)
        d = request.json
        safha_ad = next((s['ad'] for s in SAFHALAR if s['kod']==d.get('safhaKod')), d.get('safhaKod',''))
        _zaman_ekle(is_id, user, safha_ad, d.get('safhaKod',''), d.get('aksiyon',''), d.get('aciklama',''), d.get('tip','NOT'))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== ONAY / GÖZLEM ==========

@app.route('/api/onay/<is_id>', methods=['GET'])
def get_onaylar(is_id):
    try:
        ws = get_worksheet('OnayGozlemler')
        data = ws.get_all_records()
        data = [x for x in data if x.get('IsId') == is_id]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/onay/<is_id>', methods=['POST'])
def add_onay(is_id):
    try:
        user = get_user(request)
        d = request.json
        ws = get_worksheet('OnayGozlemler')
        ws.append_row([gen_id(), is_id, user, now_str(),
                       d.get('yorum',''), d.get('safhaDurumu','GORULDU')])
        _zaman_ekle(is_id, user, 'Gözlem', 'GOZLEM',
                    f'GÖRÜLDÜ & ONAYLANDI ({user})', d.get('yorum',''), 'GOZLEM')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== ARAŞTIRMA ==========

@app.route('/api/arastirma', methods=['POST'])
def arastirma():
    try:
        user = get_user(request)
        d = request.json
        query = d.get('query','')
        konum = d.get('konum','')
        if not query:
            return jsonify({'success': False, 'error': 'Arama terimi gerekli'}), 400
        
        search_query = f"{query} {konum}".strip()
        results = []
        
        if TAVILY_KEY:
            try:
                resp = requests.post('https://api.tavily.com/search',
                    headers={'Authorization': f'Bearer {TAVILY_KEY}'},
                    json={'query': search_query, 'max_results': 15}, timeout=30)
                if resp.status_code == 200:
                    for r in resp.json().get('results', []):
                        url = r.get('url','')
                        contact = extract_contact(url) if url else {}
                        results.append({
                            'baslik': r.get('title',''),
                            'url': url,
                            'telefon': contact.get('telefon',''),
                            'eposta': contact.get('eposta',''),
                            'aciklama': r.get('content','')[:200]
                        })
            except Exception as e:
                print(f"Tavily error: {e}")
        
        if not results:
            try:
                with DDGS() as ddgs:
                    for r in ddgs.text(search_query, max_results=15):
                        url = r.get('href','') or r.get('url','')
                        contact = extract_contact(url) if url else {}
                        results.append({
                            'baslik': r.get('title',''),
                            'url': url,
                            'telefon': contact.get('telefon',''),
                            'eposta': contact.get('eposta',''),
                            'aciklama': (r.get('body','') or '')[:200]
                        })
            except Exception as e:
                print(f"DDGS error: {e}")
        
        # Geçmişe kaydet
        try:
            ws = get_worksheet('ArastirmaGecmisi')
            ws.append_row([gen_id(), user, now_str(), query, konum,
                           len(results), json.dumps(results[:5], ensure_ascii=False)])
        except:
            pass
        
        return jsonify({'success': True, 'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def extract_contact(url):
    try:
        resp = requests.get(f"https://r.jina.ai/{url}", timeout=15)
        if resp.status_code != 200:
            return {}
        content = resp.text
        telefon = ''
        for pattern in [r'\+90[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}',
                        r'0\d{3}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}']:
            match = re.search(pattern, content)
            if match:
                telefon = match.group(0)
                break
        match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
        eposta = match.group(0) if match else ''
        return {'telefon': telefon, 'eposta': eposta}
    except:
        return {}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8766, debug=True)
