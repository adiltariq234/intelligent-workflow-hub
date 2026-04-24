# FinTrack AI — Deployment Guide & Documentation

## 🚀 Quick Start (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py

# 3. Open browser at http://localhost:8501
# Demo login: username=demo  password=demo123
```

---

## ☁️ Deploy on Streamlit Cloud

1. Push your project to a GitHub repo
2. Go to https://share.streamlit.io
3. Click **New app** → select your repo → set `app.py` as main file
4. Click **Deploy**

> ⚠️ SQLite on Streamlit Cloud is ephemeral (resets on restart).  
> For production, upgrade to PostgreSQL (see below).

---

## 🐘 PostgreSQL Upgrade (Production)

Replace `DB_PATH = "fintrack.db"` and all `sqlite3.connect(DB_PATH)` calls:

```python
import psycopg2, os
def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")
```

Set `DATABASE_URL` in Streamlit Cloud Secrets or your `.env` file.

---

## 📁 Project Structure

```
expense_tracker/
├── app.py              ← Main Streamlit app (all modules)
├── requirements.txt    ← Python dependencies
├── README.md           ← This file
└── fintrack.db         ← SQLite DB (auto-created on first run)
```

---

## 🧠 Architecture Overview

| Module | Functions |
|--------|-----------|
| **Data Layer** | `load_expenses`, `add_expense`, `edit_expense`, `delete_expense`, `add_income` |
| **Preprocessing** | `convert_date`, `add_time_features`, `clean_data`, `preprocess` |
| **Calculation Engine** | `calculate_totals`, `calculate_budget`, `category_summary`, `monthly_summary` |
| **AI Insights** | `generate_insights`, `budget_recommendation`, `detect_anomalies` |
| **Prediction** | `predict_expense` (linear regression on monthly totals) |
| **Goals** | `set_saving_goal`, `track_goal_progress`, `calculate_savings` |
| **Visualization** | `plot_category_chart`, `plot_monthly_trend`, `plot_income_vs_expense`, `plot_daily_heatmap`, `plot_cashflow` |
| **Auth** | `login`, `register`, `logout`, `init_session` |
| **Export** | `download_data` (CSV + Excel) |

---

## 🔐 Auth System

- Session-based via `st.session_state`
- Passwords hashed with SHA-256
- Multi-user isolation by `user_id` in all DB queries

---

## 💡 Features Checklist

- [x] Add / Edit / Delete expenses
- [x] Multi-income support (Salary, Freelance, Passive)
- [x] Real-time KPI cards (income, expenses, savings)
- [x] Category-wise breakdown (pie + bar)
- [x] Monthly trend + forecast chart
- [x] Income vs Expense cashflow chart
- [x] Daily spending heatmap
- [x] AI insights (overspending, trend alerts)
- [x] Budget recommendations (50/30/20 rule)
- [x] Anomaly detection (2.5σ threshold)
- [x] Next-month expense prediction
- [x] Savings goals + progress bars
- [x] Per-category budget limits + alerts
- [x] Recurring expense tracking
- [x] Multi-account support
- [x] Multi-currency (USD, EUR, GBP, PKR, INR, AED, CAD)
- [x] CSV + Excel export
- [x] Search & filter
- [x] Dark-themed responsive UI
- [x] Session-based login/signup
- [x] Demo data auto-seeded
