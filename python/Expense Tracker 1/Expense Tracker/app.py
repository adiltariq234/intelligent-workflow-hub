import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import hashlib
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
import warnings
warnings.filterwarnings("ignore")

# ───────────────────────── CONFIG ─────────────────────────
st.set_page_config("FinTrack AI", "💰", layout="wide")

DB_PATH = "fintrack.db"

CATEGORIES = ["Food","Transport","Shopping","Entertainment","Health","Utilities","Education","Travel","Other"]
CURRENCIES = ["USD","EUR","GBP","PKR","INR"]
ACCOUNTS = ["Main","Savings","Cash","Card"]

# ───────────────────────── DB LAYER (OPTIMIZED) ─────────────────────────
class DB:
    @staticmethod
    def conn():
        return sqlite3.connect(DB_PATH)

    @staticmethod
    def execute(query, params=()):
        with DB.conn() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()

    @staticmethod
    def fetch(query, params=()):
        with DB.conn() as conn:
            return pd.read_sql_query(query, conn, params=params)

# ───────────────────────── INIT DB ─────────────────────────
def init_db():
    DB.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)""")

    DB.execute("""CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY,
        user_id INTEGER, date TEXT, category TEXT,
        amount REAL, currency TEXT, notes TEXT, account TEXT)""")

    DB.execute("""CREATE TABLE IF NOT EXISTS incomes(
        id INTEGER PRIMARY KEY,
        user_id INTEGER, date TEXT, source TEXT,
        amount REAL, currency TEXT, notes TEXT)""")

# ───────────────────────── AUTH ─────────────────────────
def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

def register(u,p):
    try:
        DB.execute("INSERT INTO users(username,password) VALUES(?,?)",(u,hash_pw(p)))
        return True
    except:
        return False

def login(u,p):
    df = DB.fetch("SELECT * FROM users WHERE username=? AND password=?",(u,hash_pw(p)))
    return not df.empty

# ───────────────────────── CACHE LOADERS ─────────────────────────
@st.cache_data(ttl=60)
def load_expenses(uid):
    return DB.fetch("SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC",(uid,))

@st.cache_data(ttl=60)
def load_incomes(uid):
    return DB.fetch("SELECT * FROM incomes WHERE user_id=? ORDER BY date DESC",(uid,))

# ───────────────────────── HELPERS ─────────────────────────
def usd(amount): return float(amount)

def preprocess(df):
    if df.empty: return df
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].astype(float)
    return df

def kpi(df):
    return df["amount"].sum() if not df.empty else 0

# ───────────────────────── DB OPS ─────────────────────────
def add_exp(uid,d,cat,amt,cur,notes,acc):
    DB.execute("""INSERT INTO expenses
    (user_id,date,category,amount,currency,notes,account)
    VALUES (?,?,?,?,?,?,?)""",(uid,str(d),cat,amt,cur,notes,acc))
    st.cache_data.clear()

def add_income(uid,d,src,amt,cur,notes):
    DB.execute("""INSERT INTO incomes
    (user_id,date,source,amount,currency,notes)
    VALUES (?,?,?,?,?,?)""",(uid,str(d),src,amt,cur,notes))
    st.cache_data.clear()

# ───────────────────────── VISUALS ─────────────────────────
def chart_category(df):
    if df.empty: return
    c = df.groupby("category")["amount"].sum().reset_index()
    fig = px.bar(c,x="category",y="amount",color="category")
    st.plotly_chart(fig,use_container_width=True)

def chart_trend(df):
    if df.empty: return
    m = df.groupby("date")["amount"].sum().reset_index()
    fig = px.line(m,x="date",y="amount")
    st.plotly_chart(fig,use_container_width=True)

# ───────────────────────── UI ─────────────────────────
def dashboard(uid):
    st.title("💰 Dashboard")

    e = preprocess(load_expenses(uid))
    i = preprocess(load_incomes(uid))

    col1,col2,col3 = st.columns(3)
    col1.metric("Income", f"${kpi(i):,.0f}")
    col2.metric("Expense", f"${kpi(e):,.0f}")
    col3.metric("Balance", f"${kpi(i)-kpi(e):,.0f}")

    chart_trend(e)
    chart_category(e)

def add_page(uid):
    st.title("➕ Add Expense")

    with st.form("f"):
        d = st.date_input("Date")
        c = st.selectbox("Category",CATEGORIES)
        a = st.number_input("Amount",1.0)
        cur = st.selectbox("Currency",CURRENCIES)
        acc = st.selectbox("Account",ACCOUNTS)
        n = st.text_input("Notes")

        if st.form_submit_button("Save"):
            add_exp(uid,d,c,a,cur,n,acc)
            st.success("Added!")

# ───────────────────────── LOGIN UI ─────────────────────────
def login_page():
    st.title("💰 FinTrack AI")

    u = st.text_input("Username")
    p = st.text_input("Password",type="password")

    if st.button("Login"):
        if login(u,p):
            st.session_state["user"]=u
            st.rerun()
        else:
            st.error("Invalid")

    if st.button("Register"):
        register(u,p)
        st.success("Created!")

# ───────────────────────── MAIN ─────────────────────────
def main():
    init_db()

    if "user" not in st.session_state:
        login_page()
        return

    uid = 1  # simplified demo user

    menu = st.sidebar.selectbox("Menu",["Dashboard","Add Expense"])

    if menu=="Dashboard":
        dashboard(uid)
    elif menu=="Add Expense":
        add_page(uid)

if __name__ == "__main__":
    main()