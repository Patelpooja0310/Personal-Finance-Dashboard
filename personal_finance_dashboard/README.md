# 💰 Personal Finance Dashboard

A production-ready Personal Finance Dashboard built with **Streamlit**, **MySQL**, **Plotly**, and **Scikit-Learn**.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🔐 Authentication | Register / Login / Logout with bcrypt password hashing |
| 💳 Transactions | Add, Edit, Delete, bulk CSV Import |
| 📊 Dashboard | KPI cards, budget tracker, top expenses, category breakdown |
| 📈 Visualisations | Pie, Bar, Line, Area, Waterfall, Sunburst, Heatmap, Scatter |
| 🤖 ML Forecasting | Linear Regression · Random Forest · Decision Tree |
| 💰 Savings Forecast | 6-month projection with confidence bands |
| 🔍 Anomaly Detection | Z-score based spending anomaly flagging |
| 📋 Reports | Monthly, Expense, Budget reports — CSV & TXT download |
| ⚙️ Settings | Profile, password change, custom categories |

---

## 🚀 Quick Start

### 1. Clone / download the project

```bash
git clone <repo-url>
cd personal-finance-dashboard
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up MySQL

```bash
# Start MySQL and run the schema script
mysql -u root -p < schema.sql
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your MySQL credentials
```

### 5. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🔑 Demo Login

| Username | Password |
|---|---|
| `demo` | `Demo@1234` |
| `admin` | `Admin@1234` |

> Passwords are stored as bcrypt hashes. Change them via Settings → Password.

---

## 📁 Project Structure

```
personal-finance-dashboard/
│
├── app.py              # Main entry point & sidebar navigation
├── auth.py             # Registration, login, session management
├── database.py         # MySQL connection pool, CRUD operations
├── dashboard.py        # KPI cards, charts, budget status
├── transactions.py     # Add / Edit / Delete / Import transactions
├── reports.py          # Monthly, expense, budget reports + downloads
├── ml_models.py        # ML training, prediction, savings forecasting
├── visualization.py    # All Plotly chart builders
│
├── schema.sql          # Complete MySQL schema with seed data
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
│
└── .streamlit/
    └── config.toml     # Streamlit theme & server config
```

---

## 🗄️ Database Schema

| Table | Purpose |
|---|---|
| `users` | Registered users with bcrypt password hashes |
| `categories` | Income/expense categories per user |
| `transactions` | All financial transactions |
| `budgets` | Monthly budget limits per category |

---

## 🤖 ML Models

Three models are compared side-by-side:

- **Linear Regression** — baseline trend extrapolation
- **Random Forest** — ensemble tree model with lag features
- **Decision Tree** — interpretable non-linear model

Features used: `month_num`, `lag1/2/3` (previous months), `rolling_avg3`, `rolling_std3`

Evaluation metrics: **MAE**, **RMSE**, **R² Score**
