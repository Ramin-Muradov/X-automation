# 🐦 X (Twitter) Automation

**Groq** ilə trend analizi → **DeepSeek** ilə məzmun yaratma → **X API** ilə paylaşım

```
Groq (compound-beta)        DeepSeek (deepseek-chat)     X API (tweepy)
son 24 saatın trendləri  →  tək post / thread qərarı  →  paylaşım
```

---

## Qurulum

### 1. API Açarları

#### X (Twitter) Developer API
1. [developer.twitter.com](https://developer.twitter.com) → Sign up
2. Yeni Layihə + App yarat
3. **App permissions**: `Read and write` seçin
4. Aşağıdakıları kopyalayın:
   - API Key, API Key Secret
   - Access Token, Access Token Secret, Bearer Token

#### Groq API
1. [console.groq.com](https://console.groq.com) → API Keys → Create API Key
2. **Pulsuz tier** mövcuddur

#### DeepSeek API
1. [platform.deepseek.com](https://platform.deepseek.com) → API Keys → Create API Key
2. Çox sərfəli qiymət (GPT-4-dən ~30x ucuz)

---

### 2. `.env` Faylını Hazırlayın

```bash
cp .env.example .env
# .env faylını redaktə edin və açarları daxil edin
```

### 3. Virtual Mühit və Paketlər

```bash
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

---

## İstifadə

```bash
# API bağlantılarını yoxla
python main.py --check

# Test rejimində işlət (real post göndərilmir)
python main.py --test

# Dərhal bir dəfə işlət (real post)
python main.py --run

# Scheduler işə sal (hər gün POST_TIME-da işləyir)
python main.py
```

---

## Axar

```
1. [Groq compound-beta]
   └─ Son 24 saatın Biznes/Startap/Maliyyə trendlərini tapır
   └─ JSON formatında strukturlaşdırılmış summary hazırlayır

2. [DeepSeek deepseek-chat — Mərhələ 1: Strategiya]
   └─ Ən güclü post ideyasını seçir
   └─ Tək post (single) yoxsa Thread qərarı verir

3. [DeepSeek deepseek-chat — Mərhələ 2: Yazım]
   └─ Tək post: 275 simvol, hashtag + emoji ilə
   └─ Thread: 3-8 tweet, məntiqi ardıcıllıq

4. [Media Handler]
   └─ data/media/ qovluğundan təsadüfi şəkil seçir (varsa)

5. [X API (tweepy)]
   └─ Tək post: create_tweet()
   └─ Thread: hər tweet əvvəlkinin cavabı kimi göndərilir

6. [history.json]
   └─ Nəticəni saxlayır (trend, postlar, tweet ID-ləri)
```

---

## VPS-də Yerləşdirmə (Ubuntu)

```bash
# Kodu VPS-ə köçür
git clone <repo-url> /home/ubuntu/x-automation
cd /home/ubuntu/x-automation

# Virtual mühit
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# .env faylını hazırla
cp .env.example .env
nano .env  # açarları daxil edin

# Systemd service yüklə
sudo cp deploy/x-automation.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable x-automation
sudo systemctl start x-automation

# Statusu yoxla
sudo systemctl status x-automation
sudo journalctl -u x-automation -f  # canlı log
```

---

## Media Şəkilləri

`data/media/` qovluğuna `.jpg`, `.png`, `.gif` faylları əlavə edin.
Skript hər postda bu qovluqdan təsadüfi bir şəkil seçib əlavə edəcək.
Qovluq boş olduqda şəkilsiz post göndərilir.

---

## Konfiqurasiya (`.env`)

| Dəyişən | Açıqlama | Nümunə |
|---------|----------|--------|
| `POST_TIME` | Gündəlik post vaxtı | `09:00` |
| `TIMEZONE` | Zaman zolağı | `Asia/Baku` |
| `POST_LANGUAGE` | Post dili | `Azerbaijani` |
| `BUSINESS_NICHE` | Trend axtarış sahəsi | `Biznes, Startap, Maliyyə` |
| `DRY_RUN` | Test rejimi | `false` |
| `LOG_LEVEL` | Log səviyyəsi | `INFO` |
