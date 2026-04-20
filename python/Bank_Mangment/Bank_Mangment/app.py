import streamlit as st
from bank_backend import AdvancedBank
from datetime import datetime

st.set_page_config(
    page_title="NovaPay — Banking",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

/* ─── Root tokens ─── */
:root {
  --gold:    #C9A84C;
  --gold-lt: #E8C97A;
  --gold-dk: #8A6F2E;
  --bg:      #0A0A0B;
  --bg2:     #111114;
  --bg3:     #18181D;
  --bg4:     #1F1F26;
  --border:  rgba(255,255,255,0.06);
  --border2: rgba(201,168,76,0.25);
  --text:    #F0EEE8;
  --muted:   #7A7A8A;
  --success: #2ECC71;
  --danger:  #E74C3C;
  --info:    #3498DB;
  --r:       12px;
  --r-lg:    18px;
}

html, body, [class*="css"] {
  font-family: 'Inter', sans-serif !important;
  color: var(--text) !important;
}
.stApp { background: var(--bg) !important; }
.main .block-container {
  padding: 2rem 2.5rem 4rem !important;
  max-width: 1000px !important;
}
section[data-testid="stSidebar"] {
  background: var(--bg2) !important;
  border-right: 0.5px solid var(--border) !important;
}
section[data-testid="stSidebar"] > div {
  padding: 2rem 1.5rem !important;
}
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
.stDeployButton { display: none !important; }

h1, h2, h3, h4 {
  font-family: 'Syne', sans-serif !important;
  color: var(--text) !important;
  letter-spacing: -0.02em !important;
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
  background: var(--bg3) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  color: var(--text) !important;
  padding: 0.6rem 1rem !important;
  font-size: 14px !important;
  transition: border-color 0.2s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
  border-color: var(--gold) !important;
  box-shadow: 0 0 0 2px rgba(201,168,76,0.15) !important;
}
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label {
  font-size: 11px !important;
  font-weight: 500 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: var(--muted) !important;
}

.stButton > button {
  background: var(--bg3) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: var(--r) !important;
  padding: 0.6rem 1.5rem !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  letter-spacing: 0.03em !important;
  transition: all 0.2s !important;
  width: 100% !important;
}
.stButton > button:hover {
  background: var(--bg4) !important;
  border-color: var(--border2) !important;
  color: var(--gold-lt) !important;
  transform: translateY(-1px) !important;
}
.stFormSubmitButton > button {
  background: linear-gradient(135deg, var(--gold-dk), var(--gold)) !important;
  border-color: var(--gold) !important;
  color: #0A0A0B !important;
  font-weight: 600 !important;
}
.stFormSubmitButton > button:hover {
  background: linear-gradient(135deg, var(--gold), var(--gold-lt)) !important;
  color: #0A0A0B !important;
  transform: translateY(-1px) !important;
}

[data-testid="stMetric"] {
  background: var(--bg3) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-lg) !important;
  padding: 1.25rem 1.5rem !important;
  transition: border-color 0.2s !important;
}
[data-testid="stMetric"]:hover { border-color: var(--border2) !important; }
[data-testid="stMetricLabel"] p {
  font-size: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  color: var(--muted) !important;
}
[data-testid="stMetricValue"] {
  font-family: 'Syne', sans-serif !important;
  font-size: 26px !important;
  font-weight: 700 !important;
  color: var(--text) !important;
}

[data-testid="stForm"] {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-lg) !important;
  padding: 2rem !important;
}

[data-testid="stExpander"] {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  margin-bottom: 6px !important;
}
[data-testid="stExpander"] summary {
  color: var(--text) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
}

hr { border-color: var(--border) !important; }
div[role="radiogroup"] label {
  border-radius: var(--r) !important;
  padding: 0.5rem 0.75rem !important;
  transition: background 0.15s !important;
  margin-bottom: 2px !important;
}
div[role="radiogroup"] label:hover { background: var(--bg3) !important; }

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--bg4); border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

# ─── UI Helpers ─────────────────────────────────────────────────
def alert(msg, kind="success"):
    colors = {
        "success": ("#0D2818", "#2ECC71", "#1A4D30"),
        "error":   ("#2C0D0D", "#E74C3C", "#5C1A1A"),
        "info":    ("#0D1B2C", "#3498DB", "#1A3A5C"),
        "warning": ("#2C1F0D", "#F39C12", "#5C3E1A"),
    }
    bg, accent, border = colors.get(kind, colors["info"])
    icon = {"success": "✓", "error": "✕", "info": "◈", "warning": "⚠"}[kind]
    st.markdown(f"""
    <div style="background:{bg};border:1px solid {border};border-left:3px solid {accent};
    border-radius:10px;padding:0.9rem 1.2rem;margin:0.75rem 0;
    display:flex;align-items:center;gap:10px;">
      <span style="color:{accent};font-size:16px;font-weight:700">{icon}</span>
      <span style="color:{accent};font-size:13px;font-weight:500">{msg}</span>
    </div>""", unsafe_allow_html=True)

def section_title(title, subtitle=None):
    sub_html = f'<p style="color:var(--muted);font-size:13px;margin:0.3rem 0 0;">{subtitle}</p>' if subtitle else ""
    st.markdown(f"""
    <div style="margin-bottom:2rem;">
      <h2 style="font-family:\'Syne\',sans-serif;font-size:28px;font-weight:700;
      margin:0;letter-spacing:-0.03em;">{title}</h2>
      {sub_html}
    </div>""", unsafe_allow_html=True)

def balance_hero(name, balance, account_num):
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#16130C 0%,#1C1910 60%,#0F0F0A 100%);
    border:1px solid rgba(201,168,76,0.25);border-radius:20px;padding:2.5rem;
    margin-bottom:2rem;position:relative;overflow:hidden;">
      <div style="position:absolute;top:-80px;right:-80px;width:260px;height:260px;border-radius:50%;
      background:radial-gradient(circle,rgba(201,168,76,0.1),transparent 70%);pointer-events:none;"></div>
      <p style="font-size:10px;font-weight:600;letter-spacing:0.14em;color:#C9A84C;
      text-transform:uppercase;margin:0 0 1.25rem;">Total Balance</p>
      <h1 style="font-family:\'Syne\',sans-serif;font-size:52px;font-weight:800;
      color:#F0EEE8;margin:0;letter-spacing:-0.04em;line-height:1;">
        Rs {balance:,.0f}
      </h1>
      <div style="display:flex;justify-content:space-between;margin-top:2rem;
      padding-top:1.5rem;border-top:1px solid rgba(255,255,255,0.06);">
        <div>
          <p style="font-size:10px;color:#7A7A8A;margin:0;letter-spacing:0.08em;text-transform:uppercase;">Account Holder</p>
          <p style="font-size:15px;color:#F0EEE8;margin:0.3rem 0 0;font-weight:500;">{name}</p>
        </div>
        <div style="text-align:right;">
          <p style="font-size:10px;color:#7A7A8A;margin:0;letter-spacing:0.08em;text-transform:uppercase;">Account Number</p>
          <p style="font-size:16px;color:#C9A84C;margin:0.3rem 0 0;font-family:\'Syne\',sans-serif;
          font-weight:700;letter-spacing:0.06em;">{account_num}</p>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

def transaction_row(t_type, amount, balance_after, timestamp):
    is_dep = t_type == "deposit"
    color  = "#2ECC71" if is_dep else "#E74C3C"
    bg     = "rgba(46,204,113,0.08)" if is_dep else "rgba(231,76,60,0.08)"
    sign   = "+" if is_dep else "−"
    icon   = "↑" if is_dep else "↓"
    try:
        ts = datetime.fromisoformat(timestamp).strftime("%d %b %Y  %H:%M")
    except Exception:
        ts = timestamp
    st.markdown(f"""
    <div style="background:#111114;border:1px solid rgba(255,255,255,0.06);border-radius:12px;
    padding:1rem 1.25rem;margin-bottom:6px;display:flex;align-items:center;
    justify-content:space-between;">
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="background:{bg};color:{color};width:36px;height:36px;border-radius:10px;
        display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:700;
        flex-shrink:0;">{icon}</div>
        <div>
          <p style="margin:0;font-size:13px;font-weight:500;color:#F0EEE8;">
            {'Deposit' if is_dep else 'Withdrawal'}</p>
          <p style="margin:0.2rem 0 0;font-size:11px;color:#7A7A8A;">{ts}</p>
        </div>
      </div>
      <div style="text-align:right;">
        <p style="margin:0;font-family:\'Syne\',sans-serif;font-size:15px;
        font-weight:700;color:{color};">{sign}Rs {amount:,.0f}</p>
        <p style="margin:0.2rem 0 0;font-size:11px;color:#7A7A8A;">
          Balance: Rs {balance_after:,.0f}</p>
      </div>
    </div>""", unsafe_allow_html=True)

def sidebar_logo():
    st.markdown("""
    <div style="margin-bottom:2.5rem;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.35rem;">
        <div style="background:linear-gradient(135deg,#8A6F2E,#C9A84C);width:34px;height:34px;
        border-radius:10px;display:flex;align-items:center;justify-content:center;
        font-size:16px;font-weight:800;color:#0A0A0B;font-family:\'Syne\',sans-serif;">◈</div>
        <span style="font-family:\'Syne\',sans-serif;font-size:20px;font-weight:800;
        color:#F0EEE8;letter-spacing:-0.03em;">NovaPay</span>
      </div>
      <p style="font-size:11px;color:#7A7A8A;margin:0;letter-spacing:0.06em;">Premium Banking</p>
    </div>""", unsafe_allow_html=True)

def info_card(label, value, accent=False):
    color = "#C9A84C" if accent else "#F0EEE8"
    fsize = "22px" if accent else "15px"
    ffam  = "font-family:'Syne',sans-serif;" if accent else ""
    return f"""
    <div>
      <p style="font-size:10px;font-weight:600;letter-spacing:0.1em;color:#7A7A8A;
      text-transform:uppercase;margin:0 0 0.3rem;">{label}</p>
      <p style="{ffam}font-size:{fsize};font-weight:{'700' if accent else '500'};
      color:{color};margin:0;">{value}</p>
    </div>"""

# ─── Session init ───────────────────────────────────────────────
if "bank" not in st.session_state:
    st.session_state.bank = AdvancedBank()
bank = st.session_state.bank

# ─── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    sidebar_logo()

    if bank.is_logged_in():
        u = bank.current_user
        st.markdown(f"""
        <div style="background:#18181D;border:1px solid rgba(201,168,76,0.2);
        border-radius:14px;padding:1rem 1.25rem;margin-bottom:2rem;">
          <p style="font-size:10px;font-weight:600;letter-spacing:0.1em;
          color:#C9A84C;text-transform:uppercase;margin:0 0 0.3rem;">Signed In</p>
          <p style="font-size:14px;font-weight:600;color:#F0EEE8;margin:0;">{u['name']}</p>
          <p style="font-size:11px;color:#7A7A8A;margin:0.2rem 0 0;
          font-family:'Syne',sans-serif;letter-spacing:0.04em;">{u['account_num']}</p>
        </div>""", unsafe_allow_html=True)

        page = st.radio("", [
            "◈  Overview",
            "↑  Deposit",
            "↓  Withdraw",
            "↻  Transactions",
            "✎  Update Profile",
            "○  Account",
            "→  Sign Out",
        ], label_visibility="collapsed")
    else:
        page = st.radio("", [
            "⊕  Sign In",
            "◻  Create Account",
        ], label_visibility="collapsed")

    st.markdown("""
    <div style="margin-top:3rem;padding-top:1.5rem;border-top:1px solid rgba(255,255,255,0.06);">
      <p style="font-size:10px;color:#3A3A4A;text-align:center;letter-spacing:0.05em;">
        © 2025 NovaPay · v2.0
      </p>
    </div>""", unsafe_allow_html=True)

# ─── Guest Pages ────────────────────────────────────────────────
if not bank.is_logged_in():

    if "Create Account" in page:
        section_title("Open Account", "Join NovaPay — Premium banking for everyone")
        with st.form("create_form"):
            c1, c2 = st.columns(2)
            with c1:
                name  = st.text_input("Full Name",     placeholder="Ali Ahmed")
                email = st.text_input("Email Address", placeholder="ali@email.com")
            with c2:
                age   = st.number_input("Age", min_value=18, max_value=120, value=25)
                pin   = st.text_input("4-Digit PIN", type="password",
                                      placeholder="••••", max_chars=4)
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            sub = st.form_submit_button("Create Account  →", use_container_width=True)

        if sub:
            if name and email and pin:
                ok, msg, user = bank.create_account(name, age, email, pin)
                if ok:
                    alert(f"Account created! Your number: {user['account_num']}", "success")
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#16130C,#1C1910);
                    border:1px solid rgba(201,168,76,0.25);border-radius:16px;
                    padding:1.75rem 2rem;margin-top:1rem;">
                      <p style="font-size:10px;font-weight:600;letter-spacing:0.12em;
                      color:#C9A84C;text-transform:uppercase;margin:0 0 1.25rem;">Your Credentials</p>
                      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.25rem;">
                        {info_card("Name", user['name'])}
                        {info_card("Account Number", user['account_num'], accent=True)}
                        {info_card("Email", user['email'])}
                        {info_card("PIN", user['pin'])}
                      </div>
                      <div style="margin-top:1.25rem;padding-top:1rem;
                      border-top:1px solid rgba(255,255,255,0.06);">
                        <p style="font-size:11px;color:#7A7A8A;margin:0;">
                          ⚠  Save these details — especially your Account Number and PIN.</p>
                      </div>
                    </div>""", unsafe_allow_html=True)
                else:
                    alert(msg, "error")
            else:
                alert("Please fill in all fields", "error")

    else:  # Sign In
        section_title("Sign In", "Access your NovaPay account")
        _, c, _ = st.columns([1, 2, 1])
        with c:
            with st.form("login_form"):
                acc = st.text_input("Account Number", placeholder="e.g. AB1!X23")
                pin = st.text_input("PIN", type="password",
                                    placeholder="••••", max_chars=4)
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                sub = st.form_submit_button("Sign In  →", use_container_width=True)
            if sub:
                if acc and pin:
                    ok, msg = bank.login(acc, pin)
                    if ok:
                        alert(msg, "success")
                        st.rerun()
                    else:
                        alert(msg, "error")
                else:
                    alert("Please enter your credentials", "error")

# ─── Authenticated Pages ─────────────────────────────────────────
else:
    u = bank.current_user

    # Overview
    if "Overview" in page:
        s = bank.get_account_summary()
        balance_hero(u['name'], u['balance'], u['account_num'])

        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Transactions",      s['total_transactions'])
        with c2: st.metric("Deposited (recent)",  f"Rs {s['recent_deposits']:,.0f}")
        with c3: st.metric("Withdrawn (recent)",  f"Rs {s['recent_withdrawals']:,.0f}")

        st.markdown("""
        <p style="font-size:10px;font-weight:600;letter-spacing:0.1em;color:#7A7A8A;
        text-transform:uppercase;margin:2rem 0 0.75rem;">Quick Actions</p>""",
        unsafe_allow_html=True)

        qa1, qa2, qa3 = st.columns(3)
        with qa1:
            if st.button("↑  Deposit", use_container_width=True):
                st.session_state["_nav"] = "deposit"; st.rerun()
        with qa2:
            if st.button("↓  Withdraw", use_container_width=True):
                st.session_state["_nav"] = "withdraw"; st.rerun()
        with qa3:
            if st.button("↻  History", use_container_width=True):
                st.session_state["_nav"] = "txn"; st.rerun()

        txns = bank.get_transactions(5)
        if txns:
            st.markdown("""
            <p style="font-size:10px;font-weight:600;letter-spacing:0.1em;color:#7A7A8A;
            text-transform:uppercase;margin:2rem 0 0.75rem;">Recent Transactions</p>""",
            unsafe_allow_html=True)
            for t in txns:
                transaction_row(t["type"], t["amount"], t["balance_after"], t["timestamp"])
        else:
            st.markdown("""
            <div style="background:#111114;border:1px solid rgba(255,255,255,0.06);
            border-radius:16px;padding:3rem;text-align:center;margin-top:1.5rem;">
              <p style="font-size:30px;margin:0 0 0.75rem;color:#3A3A4A;">◈</p>
              <p style="color:#7A7A8A;font-size:14px;margin:0;">
                No transactions yet — make your first deposit!</p>
            </div>""", unsafe_allow_html=True)

    # Deposit
    elif "Deposit" in page or st.session_state.get("_nav") == "deposit":
        st.session_state.pop("_nav", None)
        section_title("Deposit Funds", "Per-transaction limit: Rs 10,000")
        c1, c2 = st.columns([3, 2])
        with c1:
            with st.form("dep_form"):
                amount = st.number_input("Amount (Rs)", min_value=1,
                                         max_value=10000, value=5000, step=500)
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                sub = st.form_submit_button("Confirm Deposit  →", use_container_width=True)
            if sub:
                ok, msg, bal = bank.deposit(amount)
                alert(f"Rs {amount:,.0f} deposited. New balance: Rs {bal:,.0f}" if ok else msg,
                      "success" if ok else "error")
        with c2:
            st.markdown(f"""
            <div style="background:#111114;border:1px solid rgba(255,255,255,0.06);
            border-radius:16px;padding:1.5rem;">
              <p style="font-size:10px;font-weight:600;letter-spacing:0.1em;
              color:#7A7A8A;text-transform:uppercase;margin:0 0 0.5rem;">Current Balance</p>
              <p style="font-family:'Syne',sans-serif;font-size:30px;font-weight:800;
              color:#C9A84C;margin:0;">Rs {u['balance']:,.0f}</p>
              <div style="margin-top:1rem;padding-top:1rem;
              border-top:1px solid rgba(255,255,255,0.06);">
                <p style="font-size:11px;color:#7A7A8A;margin:0;">Limit: Rs 1 – Rs 10,000</p>
              </div>
            </div>""", unsafe_allow_html=True)

    # Withdraw
    elif "Withdraw" in page or st.session_state.get("_nav") == "withdraw":
        st.session_state.pop("_nav", None)
        bal = bank.get_balance() or 0
        section_title("Withdraw Funds", f"Available balance: Rs {bal:,.0f}")
        c1, c2 = st.columns([3, 2])
        with c1:
            with st.form("with_form"):
                mx = max(1, int(bal))
                amount = st.number_input("Amount (Rs)", min_value=1,
                                         max_value=mx, value=min(1000, mx), step=500)
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                sub = st.form_submit_button("Confirm Withdrawal  →", use_container_width=True)
            if sub:
                ok, msg, new_bal = bank.withdraw(amount)
                alert(f"Rs {amount:,.0f} withdrawn. Remaining: Rs {new_bal:,.0f}" if ok else msg,
                      "success" if ok else "error")
        with c2:
            st.markdown(f"""
            <div style="background:#111114;border:1px solid rgba(255,255,255,0.06);
            border-radius:16px;padding:1.5rem;">
              <p style="font-size:10px;font-weight:600;letter-spacing:0.1em;
              color:#7A7A8A;text-transform:uppercase;margin:0 0 0.5rem;">Available</p>
              <p style="font-family:'Syne',sans-serif;font-size:30px;font-weight:800;
              color:#2ECC71;margin:0;">Rs {bal:,.0f}</p>
            </div>""", unsafe_allow_html=True)

    # Transactions
    elif "Transactions" in page or st.session_state.get("_nav") == "txn":
        st.session_state.pop("_nav", None)
        txns = bank.get_transactions(50)
        section_title("Transaction History", f"{len(txns)} records")
        if txns:
            deps  = [t for t in txns if t["type"] == "deposit"]
            withs = [t for t in txns if t["type"] == "withdrawal"]
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Total Records",    len(txns))
            with c2: st.metric("Total Deposited",  f"Rs {sum(t['amount'] for t in deps):,.0f}")
            with c3: st.metric("Total Withdrawn",  f"Rs {sum(t['amount'] for t in withs):,.0f}")
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            for t in txns:
                transaction_row(t["type"], t["amount"], t["balance_after"], t["timestamp"])
        else:
            st.markdown("""
            <div style="text-align:center;padding:4rem 2rem;">
              <p style="font-size:36px;margin:0 0 1rem;color:#3A3A4A;">◈</p>
              <p style="color:#7A7A8A;font-size:14px;">No transactions found.</p>
            </div>""", unsafe_allow_html=True)

    # Update Profile
    elif "Update" in page:
        section_title("Update Profile", "Edit your account information")
        with st.form("upd_form"):
            c1, c2 = st.columns(2)
            with c1:
                name  = st.text_input("Full Name",  value=u['name'])
                email = st.text_input("Email",      value=u['email'])
            with c2:
                age   = st.number_input("Age", min_value=18,
                                        max_value=120, value=u['age'])
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            sub = st.form_submit_button("Save Changes  →", use_container_width=True)
        if sub:
            ok, msg = bank.update_details(name, age, email)
            alert(msg, "success" if ok else "error")

    # Account Details
    elif "Account" in page:
        section_title("Account Details", "Your personal & account information")
        d = bank.get_user_details()
        try:
            created = datetime.fromisoformat(d['created_at']).strftime('%d %b %Y')
        except Exception:
            created = "N/A"

        st.markdown(f"""
        <div style="background:#111114;border:1px solid rgba(255,255,255,0.06);
        border-radius:18px;padding:2rem;margin-bottom:1.5rem;">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem 2rem;">
            {info_card("Full Name",       d['name'])}
            {info_card("Account Number",  d['account_num'], accent=True)}
            {info_card("Email",           d['email'])}
            {info_card("Balance",         f"Rs {d['balance']:,.0f}", accent=True)}
            {info_card("Age",             str(d['age']))}
            {info_card("Member Since",    created)}
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <p style="font-size:10px;font-weight:600;letter-spacing:0.1em;color:#E74C3C;
        text-transform:uppercase;margin:2rem 0 0.75rem;">Danger Zone</p>
        <div style="background:rgba(231,76,60,0.05);border:1px solid rgba(231,76,60,0.15);
        border-radius:14px;padding:1.25rem 1.5rem;margin-bottom:1rem;">
          <p style="font-size:13px;color:#7A7A8A;margin:0;">
            Deleting your account is permanent and irreversible. All data will be lost.</p>
        </div>""", unsafe_allow_html=True)

        confirm = st.checkbox("I understand — permanently delete my account")
        if confirm:
            if st.button("Delete Account Permanently", use_container_width=True):
                ok, msg = bank.delete_account(True)
                if ok:
                    alert(msg, "success")
                    st.rerun()
                else:
                    alert(msg, "error")

    # Sign Out
    elif "Sign Out" in page:
        section_title("Sign Out", "End your current session")
        _, c, _ = st.columns([1, 2, 1])
        with c:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            if st.button("Confirm Sign Out  →", use_container_width=True):
                bank.logout()
                st.rerun()
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Go Back", use_container_width=True):
                st.rerun()