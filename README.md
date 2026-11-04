# 🌾 Smart Agriculture Management System

A full-stack agricultural management and recommendation platform built with Python (Flask) and PostgreSQL, engineered for seamless deployment on **Vercel** serverless functions or local development.

---

## 🚀 Features

- **Farm & Field Management:** Track farmers, fields, crop seasons, plantings, and harvest yields.
- **Rule-Based Crop Advisor:** Intelligent recommendation engine analyzing soil tests (pH, moisture, N-P-K), current agricultural season (Kharif, Rabi, Summer), and local weather data (rainfall, temperature) to suggest optimal crops, fertilizers, and irrigation advice.
- **Full Generic CRUD Interface:** Clean forms with input validation, dropdowns for enums, and foreign-key lookup labels across 11 relational tables.
- **Vercel Ready:** Configured for Vercel Serverless Functions with connection pooling, auto-reconnect on idle socket timeouts, and cloud PostgreSQL (Neon, Supabase, Vercel Postgres) compatibility.
- **Self-Healing / Auto-Init:** Automatically detects and creates missing database tables and sample seeds on first run or via `/init-db`.

---

## 📋 Project Structure

```text
├── api/
│   └── index.py         # Vercel Serverless entrypoint
├── static/
│   └── style.css        # Responsive styling
├── templates/
│   ├── base.html        # Layout & navigation
│   ├── index.html       # Farm overview dashboard
│   ├── list.html        # Table data viewer
│   ├── form.html        # Add / Edit record form
│   ├── recommend.html   # Crop advisor interface
│   └── setup.html       # Database connection status screen
├── app.py               # Core Flask application
├── requirements.txt     # Python dependencies
├── schema.sql           # Complete PostgreSQL DDL (11 tables)
├── seed.sql             # Sample data (idempotent ON CONFLICT)
├── vercel.json          # Vercel rewrite configuration
├── .env.example         # Environment variables template
└── .gitignore           # Git ignore rules (.env, __pycache__, etc.)
```

---

## ☁️ How to Deploy on Vercel

### Step 1: Push Project to GitHub
```bash
git add .
git commit -m "Initial commit for Vercel deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/agri_project.git
git push -u origin main
```

### Step 2: Set Up a Free Cloud Database
Create a free PostgreSQL instance in under 1 minute on either:
- **[Neon.tech](https://neon.tech)** (Recommended — fast serverless Postgres)
- **[Supabase.com](https://supabase.com)**

Copy your PostgreSQL connection URL. It looks like:
```text
postgresql://user:password@ep-cool-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
```

### Step 3: Import Project into Vercel
1. Go to your [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** &rarr; **Project** and select your GitHub repository.
3. In **Environment Variables**, add:
   - **`DATABASE_URL`**: `postgresql://user:password@host/dbname?sslmode=require`
   - **`SECRET_KEY`**: Any random string (e.g. `your-random-secret-key-32-chars`)
4. Click **Deploy**.

### Step 4: First Visit & Initialization
Once deployed, open your live Vercel URL.
The application will automatically detect the database and set up the schema and initial seed data. You can also manually visit `/init-db` at any time to re-verify tables.

---

## 💻 Running Locally

1. Create and activate a virtual environment (optional):
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and configure your local PostgreSQL credentials:
   ```env
   DB_NAME=SmartAgricultureDB
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   SECRET_KEY=local-dev-secret-key
   ```
4. Run the app:
   ```bash
   python app.py
   ```
5. Open `http://localhost:5001` in your browser.
