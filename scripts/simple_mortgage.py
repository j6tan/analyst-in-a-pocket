import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, load_user_data, init_session_state, supabase
import time

# --- 1. UNIVERSAL AUTO-LOADER ---
init_session_state()
if st.session_state.get('username') and not st.session_state.app_db.get('profile'):
    with st.spinner("🔄 restoring your data..."):
        load_user_data(st.session_state.username)
        time.sleep(0.1)
        st.rerun()

# 2. Inject Style
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 3. THEME ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

# --- 4. DATA BRIDGE: RECONSTRUCT AFFORDABILITY ---
# We need to re-calculate "Max Purchase" because it is a Result (not saved), 
# whereas Down Payment is an Input (saved).
def get_affordability_defaults():
    aff = st.session_state.app_db.get('affordability', {})
    
    # 1. Retrieve Saved Inputs
    t4 = float(aff.get('combined_t4', 0))
    bonus = float(aff.get('combined_bonus', 0))
    rental = float(aff.get('rental', 0))
    debts = float(aff.get('combined_debt', 0))
    dp_saved = float(aff.get('down_payment', 100000)) # Default if missing
    rate_saved = float(aff.get('bank_rate', 4.5))
    
    # 2. Quick Calc for Max Purchase (Simplified)
    # If income is 0, we return safe defaults
    total_income = t4 + bonus + (rental * 0.8)
    if total_income == 0:
        return 500000, 100000 # Fallback
        
    monthly_inc = total_income / 12
    stress_rate = max(5.25, rate_saved + 2.0)
    r_stress = (stress_rate / 100) / 12
    
    # GDS/TDS estimates (approximate for default)
    limit_gds = (monthly_inc * 0.39) - 400 # Assumed heat/tax
    limit_tds = (monthly_inc * 0.44) - 400 - debts
    max_payment = min(limit_gds, limit_tds)
    
    if max_payment <= 0:
        return dp_saved, dp_saved
        
    # Mortgage Amount capacity
    if r_stress > 0:
        max_loan = max_payment * (1 - (1 + r_stress)**-300) / r_stress
    else:
        max_loan = max_payment * 300
        
    calc_max_price = max_loan + dp_saved
    
    # Round to nice numbers
    return int(math.ceil(calc_max_price / 5000) * 5000), int(dp_saved)

# Get the defaults
default_price, default_dp = get_affordability_defaults()

# --- 5. INITIALIZE SIMPLE MORTGAGE ---
if 'simple_mortgage' not in st.session_state.app_db:
    st.session_state.app_db['simple_mortgage'] = {}

# PRE-FILL LOGIC: If simple_mortgage is empty, inject the Affordability numbers
sm_store = st.session_state.app_db['simple_mortgage']
if sm_store.get('purchase_price', 0) == 0:
    sm_store['purchase_price'] = default_price
    sm_store['down_payment'] = default_dp
    # Trigger save so we don't recalc every time
    if st.session_state.get('username'):
         supabase.table("user_vault").upsert({
            "id": st.session_state.username, 
            "data": st.session_state.app_db
        }).execute()

# --- 6. USER IDENTITY ---
prof = st.session_state.app_db.get('profile', {})
p1 = prof.get('p1_name', 'Client')
p2 = prof.get('p2_name', '')
household = f"{p1} & {p2}" if p2 else p1

# --- 7. HEADER & STORY (FIXED FORMATTING) ---
st.title("The Interest Curve")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 10px; border-left: 6px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.6; margin: 0;">
        <b>{household}</b>, most people focus on the monthly payment. Wealthy investors focus on the <b>Interest Curve</b>. 
        Use this tool to see how small 'micro-payments' can destroy your debt years ahead of schedule.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 8. INPUTS (FIXED: Integers) ---
c1, c2, c3 = st.columns(3)
with c1:
    price = cloud_input("Purchase Price ($)", "simple_mortgage", "purchase_price", step=5000)
    rate = cloud_input("Interest Rate (%)", "simple_mortgage", "rate", step=0.1)
with c2:
    dp = cloud_input("Down Payment ($)", "simple_mortgage", "down_payment", step=1000)
    amort = cloud_input("Amortization (Years)", "simple_mortgage", "amortization", step=1)
with c3:
    prepay = cloud_input("Monthly Prepayment ($)", "simple_mortgage", "prepayment", step=50)
    freq = st.selectbox("Payment Frequency", ["Monthly", "Bi-Weekly Accelerated"], key="sm_freq")

# --- 9. CALCULATIONS ---
loan_amount = price - dp
monthly_rate = (rate / 100) / 12
n_months = int(amort * 12)

if loan_amount > 0 and monthly_rate > 0:
    monthly_pmt = loan_amount * (monthly_rate * (1 + monthly_rate)**n_months) / ((1 + monthly_rate)**n_months - 1)
else:
    monthly_pmt = 0

# Accelerated Bi-Weekly Logic
if freq == "Bi-Weekly Accelerated":
    payment_per_period = monthly_pmt / 2
    periods_per_year = 26
else:
    payment_per_period = monthly_pmt
    periods_per_year = 12

actual_pmt = payment_per_period + prepay

# Amortization Schedule Loop
balance = loan_amount
total_interest = 0
months_passed = 0
data = []

while balance > 0 and months_passed < (amort * 12):
    # Convert everything to monthly steps for plotting simplicity
    # (Bi-weekly is approximated as 2.16 payments per month for interest calc in this simple view, 
    # but strictly speaking we just track the balance reduction)
    
    interest = balance * monthly_rate
    principal = (actual_pmt * (periods_per_year/12)) - interest
    
    if principal > balance: principal = balance
    
    balance -= principal
    total_interest += interest
    months_passed += 1
    
    data.append({"Month": months_passed, "Balance": balance, "Interest Paid": total_interest})

df = pd.DataFrame(data)

# --- 10. VISUALS ---
st.divider()
k1, k2, k3 = st.columns(3)
k1.metric("Standard Payment", f"${monthly_pmt:,.2f}")
k2.metric("Your Payment (with Prepay)", f"${actual_pmt:,.2f} / {freq}")
k3.metric("Total Interest Cost", f"${total_interest:,.0f}")

st.subheader("📉 The Payoff Trajectory")
if not df.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Month']/12, y=df['Balance'], fill='tozeroy', name='Mortgage Balance', line=dict(color=PRIMARY_GOLD)))
    fig.update_layout(height=400, xaxis_title="Years", yaxis_title="Balance ($)", margin=dict(l=0,r=0,t=20,b=20))
    st.plotly_chart(fig, use_container_width=True)
    
    years_saved = amort - (months_passed / 12)
    if years_saved > 0.5:
        st.success(f"🎉 By adding prepayments, you become mortgage-free **{years_saved:.1f} years early**!")

show_disclaimer()
