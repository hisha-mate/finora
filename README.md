# Finora - Personal Finance & Expense Tracker

A modern, full-featured personal finance and expense management web application built with Python Flask and SQLite. Finora helps individuals track daily income and expenses, set monthly budgets with visual progress indicators, plan savings goals, and analyze bank statements directly from PDF files.

---

## 🌟 Key Features

- **Dashboard & Insights**: Real-time financial health score, current month income vs. expenses overview, net balance, and actionable spending tips.
- **Transaction Management**: Add, view, categorize, and delete income and expense transactions.
- **Budgeting**: Set monthly spending limits per category (Food, Shopping, Bills, Transport, etc.) with spent vs. remaining tracking.
- **Savings Goals**: Track savings targets, progress bars, and completion deadlines.
- **PDF Statement Analyzer**: Upload bank statements in PDF format, automatically parse dates and amounts, auto-categorize transactions using keyword matching, and preview before importing into your transaction ledger.
- **Secure Authentication**: User registration and login with salted password hashing via Werkzeug security.
- **Deployment Ready**: Fully configured with `gunicorn`, `Procfile`, `Dockerfile`, `render.yaml`, and environment variable support for cloud deployment.

---

## 📁 Project Structure

```text
FLASK/
├── app.py                 # Core Flask application and route controllers
├── Dockerfile             # Container configuration for Docker/Cloud deployments
├── .dockerignore          # Ignored files for Docker builds
├── .env.example           # Template for environment variables
├── .gitignore             # Git ignore configuration
├── Procfile               # Cloud process command for Render/Railway/Heroku
├── render.yaml            # Render Blueprint deployment configuration
├── requirements.txt       # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css      # Custom styles and dark/light UI components
│   └── js/
│       └── main.js        # Frontend interactions and client-side logic
├── templates/
│   ├── auth.html          # Login and sign-up pages
│   ├── base.html          # Base layout template
│   ├── dashboard.html     # Main financial dashboard
│   ├── transactions.html  # Transaction ledger & new entry form
│   ├── budgets.html       # Monthly budget manager
│   ├── goals.html         # Savings goals manager
│   ├── analytics.html     # Spending trends and category distribution
│   └── pdf_analyzer.html  # PDF statement upload and preview
└── uploads/               # Temporary storage for statement uploads (.gitkeep)
```

---

## 🚀 Local Development Setup

### 1. Prerequisites
- Python 3.10+ installed
- Git installed

### 2. Clone the Repository
```bash
git clone <your-repository-url>
cd <repository-directory>
```

### 3. Create and Activate Virtual Environment
On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

On macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy the example environment file:
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```
Optionally customize the values in `.env`:
```ini
FINORA_SECRET_KEY=your-random-secret-key-here
FLASK_DEBUG=1
PORT=5000
```

### 6. Run the Application
```bash
python app.py
```
Open your browser and navigate to `http://localhost:5000`.

---

## ⚙️ Environment Variables Reference

| Variable | Description | Default Value |
|---|---|---|
| `SECRET_KEY` / `FINORA_SECRET_KEY` | Secret key used for session signing and security | `dev-only-change-this-key` |
| `FLASK_DEBUG` | Enable Flask debug mode (`1` for development, `0` for production) | `0` |
| `PORT` | Port number the application listens on | `5000` |
| `DATABASE_PATH` | File path to SQLite database file | `<project_root>/finora.db` |
| `UPLOAD_FOLDER` | Directory where uploaded files are stored | `<project_root>/uploads` |

---

## 🌐 Production Deployment Guide

### Option 1: Render (Recommended - Free / Easy)
1. Push your repository to GitHub.
2. Sign in to [Render](https://render.com).
3. Click **New +** -> **Web Service** -> Connect your GitHub repository.
4. Render will automatically detect `render.yaml` or use these settings:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. In **Environment Variables**, add:
   - `FINORA_SECRET_KEY`: Set to a strong random key (or click Generate).
   - `FLASK_DEBUG`: `0`
6. Click **Deploy Web Service**.

> **Note on Data Persistence**: Free tier cloud hosts (Render, Heroku) use ephemeral filesystems where SQLite resets on redeploy. For persistent data, attach a Render Persistent Disk mounted at `/data` and set `DATABASE_PATH=/data/finora.db`.

---

### Option 2: Railway
1. Push your repository to GitHub.
2. Sign in to [Railway](https://railway.app).
3. Click **New Project** -> **Deploy from GitHub repo**.
4. Select your repository. Railway detects the `Procfile` and `requirements.txt` automatically.
5. In the project settings, add the environment variable `FINORA_SECRET_KEY`.

---

### Option 3: Docker Container
1. **Build the Docker Image**:
   ```bash
   docker build -t finora:latest .
   ```
2. **Run the Container**:
   ```bash
   docker run -d -p 5000:5000 \
     -e FINORA_SECRET_KEY="production-secret-key" \
     -v finora_data:/app \
     --name finora-app finora:latest
   ```
3. Access the app at `http://localhost:5000`.

---

### Option 4: Linux VPS (Ubuntu / Debian + Nginx + Systemd)
1. Clone the repo onto your server in `/var/www/finora`.
2. Set up virtual environment and install dependencies:
   ```bash
   cd /var/www/finora
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create a Systemd service file `/etc/systemd/system/finora.service`:
   ```ini
   [Unit]
   Description=Gunicorn instance to serve Finora
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/var/www/finora
   Environment="PATH=/var/www/finora/venv/bin"
   Environment="FINORA_SECRET_KEY=your-production-secret"
   ExecStart=/var/www/finora/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app

   [Install]
   WantedBy=multi-user.target
   ```
4. Start and enable the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start finora
   sudo systemctl enable finora
   ```
5. Configure Nginx to reverse proxy port 80/443 to `http://127.0.0.1:5000`.

---

## 🔒 Security & Best Practices
- Never commit `.env` or sensitive `.db` files with real user data to GitHub.
- Keep `FLASK_DEBUG=0` in production environments.
- Always use a strong, unique secret key for `FINORA_SECRET_KEY` in production.
