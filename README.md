# 🏪 TeleStore — Production Telegram Store Bot Platform

A full-featured, production-ready multi-store e-commerce bot for Telegram.
Built with **aiogram 3.x**, **MongoDB**, async Python, and a premium UI.

---

## ✨ Features

### 🛍️ Customer Experience
- **Store discovery** via deep-links or referrals
- **Category browsing** with product pagination
- **Shopping cart** with quantity management
- **Coupon/discount** codes at checkout
- **3 payment methods**: UPI, OxaPay (crypto), Telegram Stars
- **Order tracking** with real-time status updates
- **Auto-delivery** of digital products after payment
- **Review system** (star rating + comment)
- **Support tickets** with media support
- **Referral program** with rewards

### 🏪 Store Owner Panel
- **Dashboard** — revenue, orders, customers, daily/monthly analytics
- **Product management** — add/edit/delete, price, description, image, delivery link
- **Order management** — confirm, update status, view customer details
- **Payment confirmation** — UPI proof review with quick confirm/reject
- **Analytics** — revenue graph (ASCII), best seller, top customers
- **Coupon system** — fixed/percentage, expiry, usage limits
- **Referral config** — choose reward type and value, leaderboard
- **Support tickets** — reply with text/media, close with notification
- **Broadcast** — send text/photo/video/document/GIF to all customers
- **Store settings** — name, logo, banner, welcome text, support, payment keys

### 🛡️ Admin Panel
- **Platform analytics** — daily/weekly/monthly/yearly revenue
- **Store management** — list, view, suspend, activate, delete stores
- **User management** — search by ID or username, ban/unban
- **Broadcast** — all users, all stores, selected stores, single store
- **Payment overview** — pending confirmations, recent transactions

### 🔒 Security
- Rate limiting (sliding window) + anti-spam (flood detection + auto-mute)
- Token validation and webhook signature verification
- OxaPay webhook HMAC verification
- Encrypted configuration (Fernet)
- Admin permission checks on every protected handler
- Audit logs for sensitive operations
- Banned user middleware (blocks all requests)

---

## 🚀 Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/yourname/telestore.git
cd telestore
cp .env.example .env
```

Edit `.env` with your values:
- `BOT_TOKEN` — from [@BotFather](https://t.me/BotFather)
- `BOT_USERNAME` — your bot's username (without @)
- `SUPER_ADMIN_IDS` — comma-separated Telegram user IDs
- `MONGODB_URI` — MongoDB Atlas or local URI
- `ENCRYPTION_KEY` — generate with:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

### 2. Run with Docker (Recommended)

```bash
docker compose up -d
```

This starts:
- The bot (polling mode by default)
- MongoDB 7.0 with automatic init

To enable the MongoDB web UI:
```bash
docker compose --profile debug up -d
# Visit http://localhost:8081
```

### 3. Run Locally

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m bot.main
```

---

## ☁️ Deployment

### Render

1. Connect your GitHub repo to Render
2. Create a **Background Worker** service
3. Set environment variables from `.env.example`
4. Deploy — uses `render.yaml` automatically

### Railway

1. Connect repo to Railway
2. Configure secrets in dashboard (BOT_TOKEN, MONGODB_URI, etc.)
3. Deploy — uses `railway.toml` automatically

### VPS / Ubuntu

```bash
# Install Python 3.11+
sudo apt update && sudo apt install python3.11 python3.11-venv -y

# Clone and setup
git clone https://github.com/yourname/telestore.git /opt/telestore
cd /opt/telestore
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env

# Run with systemd
sudo cp scripts/telestore.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now telestore
```

### Webhook Mode

Set in `.env`:
```env
USE_WEBHOOK=true
WEBHOOK_BASE_URL=https://your-domain.com
WEBHOOK_PATH=/webhook
WEBHOOK_SECRET=your_secret_32chars
```

---

## 🗄️ Database

**MongoDB Collections:**

| Collection | Purpose |
|-----------|---------|
| `users` | All bot users |
| `stores` | Store profiles & settings |
| `products` | Store products |
| `orders` | Customer orders |
| `payments` | Payment records & proofs |
| `coupons` | Discount coupons |
| `referrals` | Referral tracking |
| `tickets` | Support threads |
| `broadcasts` | Broadcast history |
| `analytics` | Event-based analytics |
| `reviews` | Product/store reviews |
| `carts` | Active shopping carts |
| `expired_stores` | Archived stores |
| `audit_logs` | Admin action logs |

---

## 💾 Backups

```bash
# Manual backup
./scripts/backup.sh

# Restore from backup
./scripts/backup.sh --restore ./backups/telestore_20240101_020000.tar.gz

# Automated (cron) — runs at 2 AM daily
0 2 * * * /opt/telestore/scripts/backup.sh
```

---

## 📁 Project Structure

```
telestore/
├── bot/
│   └── main.py              # Entry point
├── config/
│   └── settings.py          # Pydantic settings (env vars)
├── database/
│   ├── connection.py        # Motor client & index creation
│   ├── models.py            # Pydantic v2 document models
│   └── repos.py             # Repository layer (all DB ops)
├── handlers/
│   ├── start.py             # /start, /help, deep-links
│   ├── store.py             # Store browsing
│   ├── products.py          # Product detail & add-to-cart
│   ├── cart.py              # Cart management
│   ├── payments.py          # Checkout flow
│   ├── orders.py            # Order history
│   ├── coupons.py           # Coupon apply
│   ├── referrals.py         # Referral links & leaderboard
│   ├── tickets.py           # Support tickets
│   ├── reviews.py           # Product reviews
│   ├── search.py            # Product search
│   ├── owner/               # Store owner panel
│   │   ├── dashboard.py
│   │   ├── products.py
│   │   ├── orders.py
│   │   ├── payments.py
│   │   ├── analytics.py
│   │   ├── coupons.py
│   │   ├── referrals.py
│   │   ├── settings.py
│   │   ├── tickets.py
│   │   └── broadcast.py
│   └── admin/               # Super-admin panel
│       ├── panel.py
│       ├── stores.py
│       ├── users.py
│       ├── analytics.py
│       ├── payments.py
│       └── broadcast.py
├── keyboards/
│   └── builders.py          # All inline keyboard builders
├── middlewares/
│   ├── auth.py              # User resolution & ban check
│   ├── anti_spam.py         # Rate limiting & flood control
│   ├── store_context.py     # Owner store injection
│   └── logging.py
├── services/
│   ├── payments.py          # UPI, OxaPay, Stars services
│   ├── delivery.py          # Auto digital delivery
│   ├── notifications.py     # Owner/customer notifications
│   └── referral.py          # Referral processing
├── states/
│   └── forms.py             # All FSM StatesGroups
├── utils/
│   └── helpers.py           # Utility functions
├── scripts/
│   ├── backup.sh            # MongoDB backup/restore
│   └── mongo-init.js        # DB initialization
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── railway.toml
├── requirements.txt
├── .env.example
└── README.md
```

---

## 💳 Payment Methods

### UPI (Manual)
1. Customer selects UPI at checkout
2. Bot shows UPI ID + optional QR image
3. Customer pays and sends screenshot/UTR
4. Owner reviews proof and confirms
5. Digital product delivered automatically

### OxaPay (Crypto — Automatic)
1. Customer selects OxaPay
2. Bot creates invoice via OxaPay API
3. Customer pays via crypto
4. Webhook confirms automatically
5. Order confirmed + product delivered

### Telegram Stars (Automatic)
1. Customer selects Stars
2. Bot sends native Telegram invoice
3. Payment handled by Telegram
4. Bot receives `successful_payment` update
5. Order confirmed + product delivered

---

## ⚙️ Store Setup Flow

1. Owner sends `/start` to bot
2. Bot detects no store → starts `StoreSetupStates` FSM
3. Owner provides: name → description → logo → support username → UPI ID
4. Store created and owner redirected to dashboard

---

## 📝 License

MIT License — Free to use, modify, and deploy commercially.

---

*Built with ❤️ using aiogram 3.x + MongoDB*
