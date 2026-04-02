# Satın Alma ERP

AS400 tarzı terminal görünümünde satın alma yönetim sistemi.

## Özellikler

- 📋 **Talepler** - Satın alma talepleri oluştur ve takip et
- 🏢 **Firmalar** - Tedarikçi veritabanı (telefon, eposta, konum)
- 🔍 **Araştırma** - DuckDuckGo ile web araması, otomatik iletişim çekme
- 💵 **Teklifler** - Fiyat teklifleri yönetimi (WhatsApp, Eposta, SMS kaynakları)
- 🔧 **İşler** - İş süreci takibi, kanıt ekleme
- 📄 **Faturalar** - Fatura ve vade yönetimi

## Teknolojiler

- Frontend: HTML + Tailwind CSS
- Backend: Python Flask (Vercel Serverless)
- Veritabanı: Google Sheets
- Dosya: Google Drive

## Kurulum

### Local Development

```bash
# Gerekli paketler
pip install -r requirements.txt

# Credentials dosyasını koy
# credentials.json (Google Service Account)

# Çalıştır
python api/index.py
```

### Vercel Deploy

1. Vercel'de yeni proje oluştur
2. GitHub repo bağla
3. Environment variables ekle:
   - `GOOGLE_CREDENTIALS` - JSON string
   - `SHEETS_ID` - Google Sheets ID
   - `DRIVE_FOLDER_ID` - Google Drive klasör ID

4. Deploy!

## Google Setup

1. Google Cloud Console'da proje oluştur
2. Sheets API ve Drive API aktifleştir
3. Service Account oluştur
4. JSON key indir
5. Google Sheets'i Service Account ile paylaş (Editor)
6. Google Drive klasörünü paylaş (Editor)

## Kullanım

1. **F1** - Yeni talep aç
2. **F5** - Sayfayı yenile
3. **ESC** - Modal kapat

## Arama Özelliği

DuckDuckGo ile web'de arama yapar, Jina Reader ile sitelerden telefon/eposta çeker.

Örnek: "Ankara klima bakım" yaz ve ara.