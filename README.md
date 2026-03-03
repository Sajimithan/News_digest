# Tech News Chatbot

A full-stack AI-powered news aggregation and chat application.

**Stack**: FastAPI · Python 3.12 · React 18 · Vite 6 · TypeScript · LangChain · Groq LLM · SQLite · Nginx · Systemd

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Local Development](#local-development)
3. [Docker Quick Start](#docker-quick-start)
4. [Production Deployment (AWS Lightsail)](#production-deployment)
   - [1 — GitHub repository setup](#1--github-repository-setup)
   - [2 — Lightsail instance](#2--lightsail-instance)
   - [3 — Server first-time setup](#3--server-first-time-setup)
   - [4 — Deploy application files](#4--deploy-application-files)
   - [5 — Nginx & SSL](#5--nginx--ssl)
   - [6 — GitHub Actions CI/CD](#6--github-actions-cicd)
5. [Environment Variables](#environment-variables)
6. [API Routes](#api-routes)
7. [Troubleshooting](#troubleshooting)

---

## Project Structure

```
.
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── main.py       # App factory, provider wiring
│   │   ├── config.py     # Runtime settings (env-driven)
│   │   ├── routes/       # HTTP route definitions
│   │   ├── services/     # Business logic, LLM, SSE, news fetchers
│   │   ├── repositories/ # SQLite access layer
│   │   └── models/       # Pydantic data models
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             # React + Vite SPA
│   ├── src/
│   ├── Dockerfile        # Multi-stage: node builder → nginx server
│   └── nginx.conf        # Nginx config used inside the container
├── deploy/               # Server config templates (copy to server)
│   ├── technews-backend.service   # systemd unit
│   └── nginx-technews.conf        # Nginx site config
├── .github/
│   └── workflows/
│       └── ci-cd.yml     # GitHub Actions CI + deploy
├── docker-compose.yml
└── backend/.env.example  # Copy to backend/.env and fill in keys
```

---

## Local Development

### Prerequisites
- Python 3.12+
- Node 20+

### Backend
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # fill in your API keys
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev                   # dev server on http://localhost:5173
```

The Vite dev server proxies all backend routes to `http://localhost:8000` via `vite.config.ts`.

---

## Docker Quick Start

```bash
# Copy and fill in keys first
cp backend/.env.example backend/.env

docker compose up --build
```

- Frontend: http://localhost:3000
- Backend health check: http://localhost:8000/health

---

## Production Deployment

> **Target**: AWS Lightsail Ubuntu 22.04, systemd + Nginx (no Docker in production)

### 1 — GitHub repository setup

```powershell
# In your project root (Windows PowerShell)
git init
git add .
git commit -m "Initial commit"

# Create a new repository on https://github.com/new
# Then push:
git remote add origin https://github.com/<your-user>/<your-repo>.git
git branch -M main
git push -u origin main
```

---

### 2 — Lightsail instance

1. Open [AWS Lightsail](https://lightsail.aws.amazon.com/) → **Create instance**
2. Platform: **Linux / Unix** → Blueprint: **Ubuntu 22.04 LTS**
3. Instance plan: **$10/month** (2 GB RAM) or higher is recommended
4. Key pair: download and save the `.pem` file securely
5. After creation → **Networking** tab → attach a **Static IP**
6. Open ports in the Lightsail firewall:

   | Port | Protocol | Purpose        |
   |------|----------|----------------|
   | 22   | TCP      | SSH            |
   | 80   | TCP      | HTTP           |
   | 443  | TCP      | HTTPS          |

---

### 3 — Server first-time setup

SSH into the instance:
```bash
ssh -i /path/to/key.pem ubuntu@<STATIC_IP>
```

Run the following once:
```bash
# System packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3-pip nginx certbot python3-certbot-nginx git

# Application directories
sudo mkdir -p /var/www/technews/backend/data
sudo mkdir -p /var/www/technews/frontend/dist

# Give your user write access (used by GitHub Actions rsync)
sudo chown -R ubuntu:ubuntu /var/www/technews

# www-data needs to read the backend files (systemd runs as www-data)
sudo usermod -aG www-data ubuntu
```

---

### 4 — Deploy application files

**Copy deploy configs from your local machine:**
```bash
# From your local machine:
scp -i /path/to/key.pem deploy/technews-backend.service ubuntu@<IP>:/tmp/
scp -i /path/to/key.pem deploy/nginx-technews.conf     ubuntu@<IP>:/tmp/

# On the server:
sudo mv /tmp/technews-backend.service /etc/systemd/system/
sudo mv /tmp/nginx-technews.conf      /etc/nginx/sites-available/technews
```

**Upload backend and create the .env:**
```bash
# From local machine — copy backend source:
rsync -az --exclude '__pycache__' --exclude '.env' --exclude 'data/' \
  backend/ ubuntu@<IP>:/var/www/technews/backend/

# On the server — create venv and install deps:
cd /var/www/technews/backend
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# Create the production .env (fill in your real keys):
cp .env.example .env
nano .env
```

**Build and copy frontend:**
```bash
# From local machine:
cd frontend && npm ci && npx vite build --outDir dist
rsync -az dist/ ubuntu@<IP>:/var/www/technews/frontend/dist/
```

**Enable and start the backend service:**
```bash
# On the server:
sudo systemctl daemon-reload
sudo systemctl enable  technews-backend
sudo systemctl start   technews-backend
sudo systemctl status  technews-backend
```

---

### 5 — Nginx & SSL

```bash
# On the server:

# Enable site (remove the default site first)
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/technews /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Reload
sudo systemctl reload nginx

# Obtain a free Let's Encrypt certificate
# Replace example.com with your real domain (DNS must already point to the server IP)
sudo certbot --nginx -d example.com -d www.example.com

# Certbot sets up auto-renewal; verify:
sudo systemctl status certbot.timer
```

---

### 6 — GitHub Actions CI/CD

Add these **repository secrets** in  
`GitHub → Settings → Secrets and variables → Actions → New repository secret`:

| Secret name         | Value                                          |
|---------------------|------------------------------------------------|
| `LIGHTSAIL_HOST`    | Your Lightsail static IP or hostname           |
| `LIGHTSAIL_USER`    | `ubuntu`                                       |
| `LIGHTSAIL_SSH_KEY` | Full content of your `.pem` private key file   |

The workflow (`.github/workflows/ci-cd.yml`) will then:

1. **On every push / PR** — type-check TypeScript, run Vite build, smoke-test the Python import
2. **On push to `main`** — rsync backend source → server, pip install, restart systemd service, rsync frontend dist, reload nginx

> **Important**: The server's `.env` file is **not** managed by CI. Update it manually via SSH when you add or rotate API keys.

---

## Environment Variables

See `backend/.env.example` for all variables with descriptions.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Groq LLM API key |
| `GROQ_INTENT_MODEL` | No | `llama-3.1-8b-instant` | Intent classification model |
| `GROQ_STREAM_MODEL` | No | `llama-3.3-70b-versatile` | Primary streaming chat model |
| `GROQ_FALLBACK_STREAM_MODEL` | No | `llama-3.1-8b-instant` | Rate-limit fallback model |
| `GUARDIAN_API_KEY` | Yes | — | The Guardian news API |
| `NEWSAPI_API_KEY` | No | — | NewsAPI.org |
| `NEWSAPIAI_API_KEY` | No | — | NewsAPI.ai |
| `ALPHAVANTAGE_API_KEY` | No | — | Stock price data |
| `FINNHUB_API_KEY` | No | — | Real-time stock quotes |
| `POLYGON_API_KEY` | No | — | Market data (future use) |
| `DB_PATH` | No | `news.db` | SQLite database file path |

---

## API Routes

All routes are served at the root (no `/api/` prefix).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/chat` | AI news chat (streaming) |
| POST | `/update` | Trigger news fetch |
| GET | `/news` | List cached articles |
| GET | `/job` | Background job status |
| GET | `/debug` | Debug info |
| GET | `/events` | SSE event stream (`?client_id=<id>`) |
| POST | `/stock/chat` | AI stock analysis chat (streaming) |
| GET | `/stock` | Stock market data |

---

## Troubleshooting

### Backend service won't start
```bash
sudo journalctl -u technews-backend -n 50 --no-pager
```
Check that `/var/www/technews/backend/.env` exists and all required keys are filled in.

### Nginx 502 Bad Gateway
The backend service is probably not running:
```bash
sudo systemctl status technews-backend
sudo systemctl restart technews-backend
```

### SSE / streaming stops immediately
Confirm the `/events` location block in the Nginx config has:
```nginx
proxy_buffering    off;
proxy_read_timeout 3600s;
proxy_http_version 1.1;
proxy_set_header   Connection '';
```

### Frontend shows blank page after deploy
Make sure the `try_files $uri $uri/ /index.html` fallback is in the `location /` block so React Router routes work.

### Permission errors in CI rsync
The SSH user (`ubuntu`) must own `/var/www/technews/`:
```bash
sudo chown -R ubuntu:ubuntu /var/www/technews
```

### Certbot certificate renewal fails
```bash
sudo certbot renew --dry-run
```
Ensure ports 80 and 443 are open in the Lightsail firewall.

### Check running service logs live
```bash
sudo journalctl -u technews-backend -f
```
