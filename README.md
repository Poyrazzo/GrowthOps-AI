# GrowthOps AI

**Büyüme Otomasyonu ve Yapay Zeka Tabanlı İş Operasyonları Sistemi**

---

## Sistem Nedir?

GrowthOps AI, B2B şirketleri için satış sürecinin en üst katmanını (top-of-funnel) uçtan uca otomatize eden bir yapay zeka ve otomasyon platformudur. Geleneksel lead listeleme araçlarından farklı olarak bu sistem; potansiyel müşteri (lead) verilerini toplamakla kalmaz, temizler, zenginleştirir, kişiselleştirilmiş mesajlar oluşturur ve çok kanallı iletişimi (e-posta, LinkedIn) yönetir.

### Ne İçin Yapıldı?

Sistem şu temel problemi çözmek için tasarlanmıştır:

> Satış ekipleri zamanlarının büyük bölümünü potansiyel müşteri araştırmasına, e-posta taslağı yazmaya ve yanıtları takip etmeye harcar. Bu süreçlerin büyük çoğunluğu tekrarlı ve otomatize edilebilir niteliktedir.

GrowthOps AI bu süreçleri otomatize ederek satış ekibinin yalnızca en kritik anlara (onay, toplantı, müzakere) odaklanmasını sağlar.

### Temel Özellikler

- **Akıllı Lead Toplama:** Hedef sektör, pozisyon ve şirket büyüklüğüne göre web sitelerinden otomatik veri toplama (scraping)
- **AI ile Lead Zenginleştirme:** Her lead için otomatik persona tespiti (örn. "HR Manager"), lead skoru (0–100) ve önerilen mesaj açısı üretimi
- **Kişiselleştirilmiş E-posta Taslakları:** OpenAI API ile her lead için özgün, insan benzeri e-posta taslağı oluşturma
- **İnsan Onay Kuyruğu:** Yüksek riskli işlemler (ilk e-posta gönderimi, belirsiz AI çıktıları) insan onayından geçer; hiçbir şey otomatik olarak gönderilmez
- **AI Yanıt Sınıflandırıcı:** Gelen e-posta yanıtlarını otomatik olarak kategorize eder (Toplantı Talebi, İlgilenmiyor, Fiyat Sorusu vb.) ve CRM'i günceller
- **LinkedIn Görev Yönetimi:** Bot yasağı riskine karşı LinkedIn etkileşimleri tamamen insan eliyle yapılır; sistem yalnızca bağlantı ve mesaj taslakları üretir
- **Denetim Kaydı:** Tüm işlemler (scraping, e-posta gönderimi, durum değişiklikleri) `activities` tablosunda kayıt altına alınır

---

## Teknik Yapı

```
┌─────────────────────────────────────────────────────────┐
│                     Next.js Frontend                    │
│        (Dashboard · Kampanya Yönetimi · Onay Kuyruğu)  │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────┐
│                Django + DRF Backend                      │
│        (İş Mantığı · CRM · Kimlik Doğrulama)           │
└──────┬────────────────┬────────────────┬────────────────┘
       │                │                │
┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐
│  PostgreSQL │  │    Redis    │  │   OpenAI   │
│  (Veritab.) │  │  (Kuyruk)   │  │  (AI Kat.) │
└─────────────┘  └──────┬──────┘  └────────────┘
                        │
              ┌─────────▼──────────┐
              │   Celery Workers   │
              │  (Scraper · AI ·   │
              │   E-posta · IMAP)  │
              └────────────────────┘
```

| Katman | Teknoloji |
|---|---|
| Backend | Python, Django, Django REST Framework |
| Frontend | Next.js, TypeScript, Tailwind CSS, shadcn/ui |
| Veritabanı | PostgreSQL |
| AI | OpenAI API, Pydantic, Langfuse |
| Arka Plan İşler | Celery, Celery Beat, Redis |
| Web Scraping | Playwright, BeautifulSoup, httpx |
| Workflow Otomasyon | n8n |
| Altyapı | Docker, Docker Compose |

---

## Kurulum ve Çalıştırma

### Gereksinimler

- Docker ve Docker Compose
- OpenAI API anahtarı
- E-posta sağlayıcısı (Postmark veya SendGrid)

### 1. Ortam Değişkenlerini Ayarla

```bash
cp backend/.env.example backend/.env
# .env dosyasını düzenle: veritabanı, OpenAI anahtarı, e-posta bilgileri vb.
```

### 2. Tüm Servisleri Başlat

```bash
docker compose up --build
```

Bu komut şu container'ları ayağa kaldırır:
- `postgres` — Veritabanı
- `redis` — Kuyruk ve önbellek
- `django` — Ana API (varsayılan: `http://localhost:8000`)
- `celery-worker` — Arka plan iş işleyicisi
- `celery-beat` — Zamanlı görev tetikleyicisi
- `playwright-worker` — Tarayıcı otomasyon düğümü
- `n8n` — Harici entegrasyon iş akışları

### 3. Veritabanı Migration

```bash
docker compose exec django python manage.py migrate
```

### 4. Admin Kullanıcısı Oluştur

```bash
docker compose exec django python manage.py createsuperuser
```

### 5. Frontend'i Başlat

```bash
cd frontend
npm install
npm run dev
# Uygulama http://localhost:3000 adresinde açılır
```

---

## Nasıl Kullanılır?

### Adım 1 — Kampanya Oluştur

Dashboard üzerinden yeni bir kampanya tanımla: hedef sektör, pozisyon başlığı ve coğrafya belirle.

### Adım 2 — Lead Toplama

Kampanyaya bağlı scraper'ı çalıştır. Sistem, hedef URL'lerden şirket ve kişi verilerini otomatik toplar.

### Adım 3 — AI Zenginleştirme

Toplanan ham veriler AI katmanına gönderilir. Her lead için şunlar hesaplanır:
- **Lead Skoru** (0–100) — 75 altı leadler filtrelenir
- **Persona** — "HR Manager", "CTO" vb.
- **Mesaj Açısı** — Hangi değer önerisiyle yaklaşılmalı

### Adım 4 — Onay Kuyruğu

AI'ın oluşturduğu e-posta taslakları **İnsan Onay Kuyruğu**'na düşer. Sen taslağı gözden geçirir, düzenler ve onaylarsın. Onaysız hiçbir şey gönderilmez.

### Adım 5 — Yanıt Yönetimi

Gelen e-posta yanıtları otomatik olarak okunur ve AI tarafından kategorize edilir. Satış ekibi yalnızca ilgili yanıtlar için bildirim alır.

### Adım 6 — LinkedIn Görevleri

Sistem LinkedIn bağlantı isteği ve DM taslakları üretir. Sen bu görevleri manuel olarak uygularsın; sistem yalnızca içerik ve organizasyonu sağlar.

---

## Proje Yapısı

```
GrowthOps AI/
├── backend/
│   ├── core/          # Kampanya, lead, mesaj modelleri
│   ├── crm/           # CRM iş mantığı, onay kuyruğu
│   ├── scraper/       # Web scraping ve Playwright görevleri
│   ├── ai_engine/     # OpenAI entegrasyonu, zenginleştirme
│   └── outreach/      # E-posta gönderimi, IMAP okuma
├── frontend/          # Next.js dashboard uygulaması
├── n8n_workflows/     # Slack ve webhook şablonları
├── Docs/              # Mimari, teknik stack ve yol haritası belgeleri
└── docker-compose.yml
```

---

## Önemli Notlar

- **LinkedIn otomasyonu yoktur.** Platform politikaları nedeniyle LinkedIn modülü yalnızca taslak ve görev üretir; botu yoktur.
- **AI emin olmadığında sorar.** Güven skoru %85 altına düşen tüm AI çıktıları otomatik olarak insan incelemesine yönlendirilir.
- **Her işlem kayıt altında.** `activities` tablosu tüm sistem eylemlerinin tam denetim geçmişini tutar.
