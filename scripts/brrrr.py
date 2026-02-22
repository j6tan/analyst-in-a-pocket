import streamlit as st
import os
import base64
from style_utils import inject_global_css, show_disclaimer, add_pdf_button
from data_handler import load_user_data, init_session_state

# --- 1. SESSION INITIALIZATION (BULLETPROOF STATE) ---
init_session_state()

# Load from the cloud exactly ONCE to prevent screen-wiping
if st.session_state.get('username') and not st.session_state.get('brrrr_sync_complete'):
    load_user_data(st.session_state.username)
    st.session_state['brrrr_sync_complete'] = True
    st.rerun()

inject_global_css()

# Top Navigation & Export Row
nav_col1, nav_col2 = st.columns([3, 1])
with nav_col1:
    if st.button("⬅️ Back to Home Dashboard"):
        st.switch_page("home.py")
with nav_col2:
    add_pdf_button()

st.divider()

# --- HELPER: SAFE FLOAT CONVERSION ---
def safe_float(val, default=0.0):
    try:
        if val is None or str(val).strip() == "":
            return float(default)
        return float(val)
    except (ValueError, TypeError):
        return float(default)

# --- HELPER: STICKY WIDGET STATE ---
db = st.session_state.get('app_db', {})

input_defaults = {
    "brrrr_buy_price_widget": ("brrrr_buy_price", 125000.0),
    "brrrr_rehab_budget_widget": ("brrrr_rehab_budget", 40000.0),
    "brrrr_arv_widget": ("brrrr_arv", 225000.0),
    "brrrr_holding_widget": ("brrrr_holding", 5000.0),
    "brrrr_rent_widget": ("brrrr_rent", 1850.0),
    "brrrr_refi_rate_widget": ("brrrr_refi_rate", 4.0),
    "brrrr_refi_costs_widget": ("brrrr_refi_costs", 4000.0),
    "brrrr_ltv_widget": ("brrrr_ltv", 75)
}

# Pre-fill Streamlit's session state to make typing sticky
for widget_key, (db_key, default_val) in input_defaults.items():
    if widget_key not in st.session_state:
        db_val = db.get(db_key, default_val)
        if isinstance(default_val, float):
            st.session_state[widget_key] = safe_float(db_val, default_val)
        else:
            st.session_state[widget_key] = int(safe_float(db_val, default_val))

# --- 2. THEME & LOGO ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
SLATE_ACCENT = "#4A4E5A"
OFF_WHITE = "#F8F9FA"

def get_logo():
    img_path = "logo.png"
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{encoded}" style="width: 75px;">'
    return "🏘️"

# Dynamic Greeting for the Storybox
prof = st.session_state.app_db.get('profile', {})
p1_name = prof.get('p1_name', 'Investor')
p2_name = prof.get('p2_name', '')
greeting = f"{p1_name} & {p2_name}" if p2_name else p1_name

st.markdown(f"<div style='display: flex; align-items: center; gap: 15px;'>{get_logo()} <h1 style='margin:0;'>The BRRRR Engine</h1></div>", unsafe_allow_html=True)

# --- THE STORYBOX ---
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-top: 20px; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">🔓 Recycled Wealth</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Listen up, <b>{greeting}</b>. The goal of this engine is to find the exact tipping point where you leave the absolute minimum amount of cash in the deal while ensuring the property still pays for itself. Enter your numbers below, and the engine will instantly grade your deal.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 3. THE INPUTS ---
st.header("🛠️ Phase 1: Buy & Rehab")
col1, col2 = st.columns(2)

with col1:
    buy_price = st.number_input("Purchase Price ($)", step=1000.0, key="brrrr_buy_price_widget")
    rehab_budget = st.number_input("Rehab Costs ($)", step=1000.0, key="brrrr_rehab_budget_widget")
    
with col2:
    arv = st.number_input("After Repair Value (ARV) ($)", step=1000.0, key="brrrr_arv_widget")
    holding = st.number_input("Holding & Closing ($)", step=1000.0, key="brrrr_holding_widget")

st.header("🏦 Phase 2: Rent & Refi")
col3, col4 = st.columns(2)

with col3:
    monthly_rent = st.number_input("Monthly Rent ($)", step=50.0, key="brrrr_rent_widget")
    refi_ltv_pct = st.slider("Refinance LTV (%)", 50, 85, key="brrrr_ltv_widget")
    refi_ltv = refi_ltv_pct / 100.0

with col4:
    refi_rate = st.number_input("Refi Interest Rate (%)", step=0.1, key="brrrr_refi_rate_widget")
    refi_costs = st.number_input("Refi Closing Costs ($)", step=500.0, key="brrrr_refi_costs_widget")

# UPDATE DATABASE SILENTLY 
for widget_key, (db_key, _) in input_defaults.items():
    st.session_state.app_db[db_key] = st.session_state[widget_key]

# --- 4. MATH ENGINE ---
total_invested = buy_price + rehab_budget + holding
new_loan = 0.0
net_proceeds = 0.0
cash_left = total_invested
monthly_piti = 0.0
opex = monthly_rent * 0.25 
monthly_net = monthly_rent - opex
dscr = 0.0
equity = 0.0

if arv > 0:
    new_loan = round(arv * refi_ltv, -3)
    net_proceeds = round(new_loan - refi_costs, -3)
    cash_left = round(total_invested - net_proceeds, -3)
    equity = round(arv - new_loan, -3)

    if refi_rate > 0:
        r_monthly = (refi_rate / 100.0) / 12.0
        monthly_piti = (new_loan * r_monthly) / (1 - (1 + r_monthly)**-360)
    else:
        monthly_piti = new_loan / 360.0
    
    monthly_net = round(monthly_rent - monthly_piti - opex, 0)
    dscr = ((monthly_rent - opex) * 12) / (monthly_piti * 12) if monthly_piti > 0 else 99.0

# --- 5. THE SMART VERDICT ENGINE ---
if arv > 0:
    st.divider()
    st.header("⚖️ The Verdict")

    # Grading Logic
    if cash_left <= 0 and monthly_net > 0:
        grade_letter = "A"
        grade_title = "GRADE A: The Holy Grail 🏆"
        grade_color = "#2e7d32" # Dark Green
        grade_desc = "You recovered 100% of your capital, created equity, AND the property pays you every month. Execute this deal and immediately repeat."
    elif cash_left > 0 and monthly_net > 0 and dscr >= 1.2:
        grade_letter = "B"
        grade_title = "GRADE B: The Wealth Builder 📈"
        grade_color = "#2B5C8F" # Blue
        grade_desc = "You left some cash in the deal, but it generates positive cash flow and easily passes the bank's stress test (DSCR). A solid, safe rental."
    elif equity > 0 and (monthly_net < 0 or dscr < 1.2):
        grade_letter = "C"
        grade_title = "GRADE C: The Equity Trap ⚠️"
        grade_color = "#D97706" # Amber
        grade_desc = "You created great net worth, but the property loses money monthly or fails the bank's DSCR test. This will drain your personal income and block your next loan."
    else:
        grade_letter = "F"
        grade_title = "GRADE F: The Money Pit 🚨"
        grade_color = "#d9534f" # Red
        grade_desc = "You are leaving cash in the deal, you lack equity, and it loses money every month. Walk away or drastically renegotiate."

    # Display Verdict Box (Font size bumped up by 5% to 1.58em)
    st.markdown(f"""
    <div style="background-color: {grade_color}10; padding: 25px; border-radius: 12px; border: 2px solid {grade_color}; margin-bottom: 10px;">
        <h2 style="color: {grade_color}; margin-top: 0; font-weight: 800; font-size: 1.58em;">{grade_title}</h2>
        <p style="color: {SLATE_ACCENT}; font-size: 1.15em; line-height: 1.5; margin-bottom: 0;">{grade_desc}</p>
    </div>
    """, unsafe_allow_html=True)

    # --- THE REPORT CARD SCALE (Expandable) ---
    with st.expander("📊 How is this deal graded? (View Full Scale)"):
        def get_op(target): return "1.0" if grade_letter == target else "0.3"
        def get_bd(target, color): return f"3px solid {color}" if grade_letter == target else f"1px solid {color}50"

        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; gap: 10px; text-align: center; margin-top: 10px; margin-bottom: 20px;">
            <div style="flex: 1; padding: 10px; background-color: #2e7d3215; border: {get_bd('A', '#2e7d32')}; opacity: {get_op('A')}; border-radius: 8px;">
                <b style="color: #2e7d32; font-size: 1.1em;">A: Holy Grail</b>
            </div>
            <div style="flex: 1; padding: 10px; background-color: #2B5C8F15; border: {get_bd('B', '#2B5C8F')}; opacity: {get_op('B')}; border-radius: 8px;">
                <b style="color: #2B5C8F; font-size: 1.1em;">B: Wealth Builder</b>
            </div>
            <div style="flex: 1; padding: 10px; background-color: #D9770615; border: {get_bd('C', '#D97706')}; opacity: {get_op('C')}; border-radius: 8px;">
                <b style="color: #D97706; font-size: 1.1em;">C: Equity Trap</b>
            </div>
            <div style="flex: 1; padding: 10px; background-color: #d9534f15; border: {get_bd('F', '#d9534f')}; opacity: {get_op('F')}; border-radius: 8px;">
                <b style="color: #d9534f; font-size: 1.1em;">F: Money Pit</b>
            </div>
        </div>
        <div style="color: {SLATE_ACCENT}; font-size: 0.95em; line-height: 1.6; background: {OFF_WHITE}; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
            <b>Grade A:</b> $0 cash left in the deal AND positive monthly cash flow.<br>
            <b>Grade B:</b> You leave some cash in the deal, but cash flow is positive and DSCR is over 1.20.<br>
            <b>Grade C:</b> You created positive equity, but the property has negative cash flow or a low DSCR.<br>
            <b>Grade F:</b> You have cash trapped, no equity, and negative cash flow.
        </div>
        """, unsafe_allow_html=True)

    # --- 6. METRICS & TRANSLATIONS ---
    st.write("")
    st.subheader("📊 The Core Metrics")
    m1, m2, m3, m4 = st.columns(4)
    
    m1.metric("Cash Left in Deal", f"${max(0, cash_left):,.0f}")
    m2.metric("Equity Created", f"${equity:,.0f}")
    m3.metric("Monthly Net", f"${monthly_net:,.0f}")
    m4.metric("DSCR (Bank Ratio)", f"{dscr:.2f}")

    # Plain English Explanations
    st.markdown(f"""
    <div style="background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; margin-top: 15px;">
        <h4 style="color: {CHARCOAL}; margin-top: 0;">📖 How to read your results:</h4>
        <ul style="color: {SLATE_ACCENT}; line-height: 1.7; margin-bottom: 0;">
            <li><b>Cash Left (Velocity):</b> If this is $0, you can recycle your money infinitely. If it's high, your money is stuck.</li>
            <li><b>Equity (Wealth):</b> The 'sweat equity' you built. Great for your net worth, but it doesn't pay the bills.</li>
            <li><b>Monthly Net (Survival):</b> Cash in your pocket after mortgage, taxes, insurance, and repairs. Must be positive to be safe.</li>
            <li><b>DSCR (The Bank's Metric):</b> Lenders demand a <b>1.20</b> or higher. If you drop below this, banks may refuse your next loan.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # --- 7. ACTIONABLE LEVERS ---
    if grade_letter in ["C", "F"]:
        st.write("")
        st.subheader("🛠️ How to fix this deal:")
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div style="background: {OFF_WHITE}; padding: 15px; border-radius: 8px; border-left: 5px solid {PRIMARY_GOLD};">
                <b style="color: {CHARCOAL};">1. Lower the LTV (Currently {refi_ltv_pct}%)</b><br>
                <span style="font-size: 0.9em; color: {SLATE_ACCENT};">Drag the LTV slider down. You will leave more cash in the deal, but your Monthly Net and DSCR will turn positive.</span>
            </div>
            <div style="background: {OFF_WHITE}; padding: 15px; border-radius: 8px; border-left: 5px solid {PRIMARY_GOLD};">
                <b style="color: {CHARCOAL};">2. Increase the Rent</b><br>
                <span style="font-size: 0.9em; color: {SLATE_ACCENT};">Can you add a bedroom or upgrade finishes to command $200 more per month?</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
show_disclaimer()
# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; color: #adb5bd; font-size: 0.85em; margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        &copy; 2026 FIRE Calculator. All rights reserved. <br>
        <span style="font-size: 0.9em; font-style: italic;">Empowering Canadian professionals to build wealth.</span>
    </div>
""", unsafe_allow_html=True)
