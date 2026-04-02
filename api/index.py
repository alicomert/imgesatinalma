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

# Config
CREDENTIALS = os.environ.get('GOOGLE_CREDENTIALS', '')
SHEETS_ID = os.environ.get('SHEETS_ID', '1Msa6QeeOW2mrnYnU1LrjNvOcpwBPUGPfbenD1L98-IY')

def get_creds():
    if CREDENTIALS:
        creds_dict = json.loads(CREDENTIALS)
        return Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
    return Credentials.from_service_account_file('credentials.json', scopes=[
        'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])

def get_gspread():
    return gspread.authorize(get_creds())

def get_spreadsheet():
    return get_gspread().open_by_key(SHEETS_ID)

def get_worksheet(name):
    sh = get_spreadsheet()
    try:
        return sh.worksheet(name)
    except:
        return sh.add_worksheet(title=name, rows=1000, cols=20)

def gen_id():
    return datetime.now().strftime('%Y%m%d') + '-' + str(uuid.uuid4())[:8]

def get_user(request):
    return request.headers.get('X-User', 'ACOMERT')

# ========== ROUTES ==========

@app.route('/')
def index():
    return send_from_directory('../public', 'index.html')

@app.route('/api/init', methods=['POST'])
def init_system():
    try:
        sh = get_spreadsheet()
        worksheets = {
            'Isler': ['ID', 'Kullanici', 'Hizmet', 'Firma', 'FirmaId', 'Baslangic', 'Bitis', 'Durum', 'Kanitlar', 'FaturaId', 'Notlar'],
            'Firmalar': ['ID', 'Kullanici', 'Ad', 'Telefon', 'Eposta', 'Adres', 'Konum', 'Hizmet', 'Web', 'Durum', 'Tarih', 'Notlar'],
            'Teklifler': ['ID', 'Kullanici', 'IsId', 'FirmaId', 'FirmaAd', 'Hizmet', 'Tutar', 'ParaBirimi', 'KDV', 'Kaynak', 'Tarih', 'Vade', 'Durum', 'Evraklar', 'Notlar'],
            'Faturalar': ['ID', 'Kullanici', 'IsId', 'FirmaId', 'FaturaNo', 'Tutar', 'ParaBirimi', 'Tarih', 'Vade', 'Durum', 'Evrak', 'Notlar'],
            'ArastirmaGecmisi': ['ID', 'Kullanici', 'Tarih', 'Query', 'Konum', 'SonucSayisi', 'Sonuclar']
        }
        existing = [ws.title for ws in sh.worksheets()]
        created = []
        for title, headers in worksheets.items():
            if title not in existing:
                ws = sh.add_worksheet(title=title, rows=1000, cols=len(headers))
                ws.append_row(headers)
                created.append(title)
        return jsonify({'success': True, 'created': created, 'existing': existing})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== İŞLER ==========

@app.route('/api/isler', methods=['GET'])
def list_isler():
    try:
        user = get_user(request)
        ws = get_worksheet('Isler')
        data = ws.get_all_records()
        data = [x for x in data if x.get('Kullanici') == user]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/is', methods=['POST'])
def create_is():
    try:
        user = get_user(request)
        ws = get_worksheet('Isler')
        data = request.json
        row = [gen_id(), user, data.get('hizmet', ''), data.get('firma', ''), data.get('firmaId', ''),
               data.get('baslangic', datetime.now().strftime('%d.%m.%Y')), data.get('bitis', ''),
               data.get('durum', 'DEVAM'), '', '', data.get('notlar', '')]
        ws.append_row(row)
        return jsonify({'success': True, 'id': row[0]})
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
            if row[0] == is_id and row[1] == user:
                ws.delete_row(i + 1)
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Bulunamadı'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== FİRMALAR ==========

@app.route('/api/firmalar', methods=['GET'])
def list_firmalar():
    try:
        user = get_user(request)
        ws = get_worksheet('Firmalar')
        data = ws.get_all_records()
        data = [x for x in data if x.get('Kullanici') == user]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/firma', methods=['POST'])
def create_firma():
    try:
        user = get_user(request)
        ws = get_worksheet('Firmalar')
        data = request.json
        row = [gen_id(), user, data.get('ad', ''), data.get('telefon', ''), data.get('eposta', ''),
               data.get('adres', ''), data.get('konum', ''), data.get('hizmet', ''), data.get('web', ''),
               data.get('durum', 'POTANSIYEL'), datetime.now().strftime('%d.%m.%Y'), data.get('notlar', '')]
        ws.append_row(row)
        return jsonify({'success': True, 'id': row[0]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/firma/<firma_id>', methods=['DELETE'])
def delete_firma(firma_id):
    try:
        user = get_user(request)
        ws = get_worksheet('Firmalar')
        all_data = ws.get_all_values()
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[0] == firma_id and row[1] == user:
                ws.delete_row(i + 1)
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Bulunamadı'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/firmalar/delete-many', methods=['POST'])
def delete_many_firmalar():
    try:
        user = get_user(request)
        ws = get_worksheet('Firmalar')
        ids = request.json.get('ids', [])
        all_data = ws.get_all_values()
        deleted = 0
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[0] in ids and row[1] == user:
                ws.delete_row(i + 1)
                deleted += 1
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== TEKLİFLER ==========

@app.route('/api/teklifler', methods=['GET'])
def list_teklifler():
    try:
        user = get_user(request)
        ws = get_worksheet('Teklifler')
        data = ws.get_all_records()
        data = [x for x in data if x.get('Kullanici') == user]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/teklif', methods=['POST'])
def create_teklif():
    try:
        user = get_user(request)
        ws = get_worksheet('Teklifler')
        data = request.json
        row = [gen_id(), user, '', data.get('firmaId', ''), data.get('firmaAd', ''), data.get('hizmet', ''),
               data.get('tutar', '0'), data.get('paraBirimi', 'TRY'), '20', data.get('kaynak', ''),
               datetime.now().strftime('%d.%m.%Y'), data.get('vade', '0'), data.get('durum', 'BEKLEMEDE'), '', data.get('notlar', '')]
        ws.append_row(row)
        return jsonify({'success': True, 'id': row[0]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/teklif/<teklif_id>', methods=['DELETE'])
def delete_teklif(teklif_id):
    try:
        user = get_user(request)
        ws = get_worksheet('Teklifler')
        all_data = ws.get_all_values()
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[0] == teklif_id and row[1] == user:
                ws.delete_row(i + 1)
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
        data = [x for x in data if x.get('Kullanici') == user]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/fatura', methods=['POST'])
def create_fatura():
    try:
        user = get_user(request)
        ws = get_worksheet('Faturalar')
        data = request.json
        row = [gen_id(), user, '', data.get('firmaId', ''), data.get('faturaNo', ''), data.get('tutar', '0'),
               data.get('paraBirimi', 'TRY'), datetime.now().strftime('%d.%m.%Y'), data.get('vade', '30'),
               data.get('durum', 'BEKLIYOR'), '', data.get('notlar', '')]
        ws.append_row(row)
        return jsonify({'success': True, 'id': row[0]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/fatura/<fatura_id>', methods=['DELETE'])
def delete_fatura(fatura_id):
    try:
        user = get_user(request)
        ws = get_worksheet('Faturalar')
        all_data = ws.get_all_values()
        for i, row in enumerate(all_data):
            if i == 0: continue
            if row[0] == fatura_id and row[1] == user:
                ws.delete_row(i + 1)
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Bulunamadı'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== ARAŞTIRMA ==========

@app.route('/api/arastirma', methods=['POST'])
def arastirma():
    try:
        user = get_user(request)
        data = request.json
        query = data.get('query', '')
        konum = data.get('konum', '')
        
        if not query:
            return jsonify({'success': False, 'error': 'Arama terimi gerekli'}), 400
        
        search_query = f"{query} {konum}".strip()
        results = []
        
        # Tavily API
        tavily_key = os.environ.get('TAVILY_API_KEY', '')
        if tavily_key:
            try:
                resp = requests.post('https://api.tavily.com/search',
                    headers={'Authorization': f'Bearer {tavily_key}'},
                    json={'query': search_query, 'max_results': 15}, timeout=30)
                if resp.status_code == 200:
                    for r in resp.json().get('results', []):
                        url = r.get('url', '')
                        contact = extract_contact(url) if url else {}
                        results.append({
                            'baslik': r.get('title', ''),
                            'url': url,
                            'telefon': contact.get('telefon', ''),
                            'eposta': contact.get('eposta', ''),
                            'aciklama': r.get('content', '')[:200]
                        })
            except Exception as e:
                print(f"Tavily error: {e}")
        
        # DuckDuckGo fallback
        if not results:
            try:
                with DDGS() as ddgs:
                    for r in ddgs.text(search_query, max_results=15):
                        url = r.get('href', '') or r.get('url', '')
                        contact = extract_contact(url) if url else {}
                        results.append({
                            'baslik': r.get('title', ''),
                            'url': url,
                            'telefon': contact.get('telefon', ''),
                            'eposta': contact.get('eposta', ''),
                            'aciklama': (r.get('body', '') or '')[:200]
                        })
            except Exception as e:
                print(f"DDGS error: {e}")
        
        return jsonify({'success': True, 'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def extract_contact(url):
    try:
        resp = requests.get(f"https://r.jina.ai/{url}", timeout=15)
        if resp.status_code != 200:
            return {}
        content = resp.text
        
        # Telefon
        telefon = ''
        for pattern in [r'\+90[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}', r'0\d{3}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}']:
                    match = re.search(pattern, content)
                    if match:
                        telefon = match.group(0)
                        break
        
        # Eposta
        match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
        eposta = match.group(0) if match else ''
        
        return {'telefon': telefon, 'eposta': eposta}
    except:
        return {}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8766, debug=True)