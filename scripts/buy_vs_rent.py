import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from style_utils import inject_global_css

# 1. Inject the Wealthsimple-inspired Editorial CSS
inject_global_css()

if st.button("⬅️ Back to Home Dashboard", kind="secondary"):
    st.switch_page("home.py")
st.divider()

# --- 1. THEME & BRANDING ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"

# --- 2. DATA RETRIEVAL (GLOBAL PROFILE) ---
prof = st.session_state.get('user_profile', {})
name1 = prof.get('p1_name') or "Primary Client"
name2 = prof.get('p2_name') or ""
household = f"{name1} and {name2}" if name2 else name1

# --- 3. PERSISTENCE INITIALIZATION ---
if "aff_rent_store" not in st.session_state:
    st.session_state.aff_rent_store = {
        "price": 800000, "dp": 200000, "rate": 4.0, "ann_tax": 2000,
        "mo_maint": 500, "apprec": 3.0, "rent": 3000, "rent_inc": 2.0,
        "inv_return": 6.0, "years": 25
    }

def sync_rent():
    # Helper to sync inputs to session state
    pass # State is auto-updated by key binding

st.markdown(f"<h1>⚖️ Buy vs. Rent Analysis</h1>", unsafe_allow_html=True)
st.caption(f"Comparing wealth trajectories for **{household}**.")

# --- 4. INPUTS SECTION ---
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("### 🏠 Purchase Scenario")
        st.session_state.aff_rent_store['price'] = st.number_input("Purchase Price ($)", value=st.session_state.aff_rent_store['price'], step=10000)
        st.session_state.aff_rent_store['dp'] = st.number_input("Down Payment ($)", value=st.session_state.aff_rent_store['dp'], step=5000)
        st.session_state.aff_rent_store['rate'] = st.number_input("Mortgage Rate (%)", value=st.session_state.aff_rent_store['rate'], step=0.1)
        st.session_state.aff_rent_store['years'] = st.slider("Time Horizon (Years)", 5, 30, st.session_state.aff_rent_store['years'])

    with c2:
        st.markdown("### 💸 Ownership Costs")
        st.session_state.aff_rent_store['ann_tax'] = st.number_input("Annual Property Tax ($)", value=st.session_state.aff_rent_store['ann_tax'], step=100)
        st.session_state.aff_rent_store['mo_maint'] = st.number_input("Monthly Maintenance ($)", value=st.session_state.aff_rent_store['mo_maint'], step=50)
        st.session_state.aff_rent_store['apprec'] = st.number_input("Home Appreciation (%)", value=st.session_state.aff_rent_store['apprec'], step=0.1)

    with c3:
        st.markdown("### 🔑 Rental Alternative")
        st.session_state.aff_rent_store['rent'] = st.number_input("Monthly Rent ($)", value=st.session_state.aff_rent_store['rent'], step=50)
        st.session_state.aff_rent_store['rent_inc'] = st.number_input("Rent Increase (%)", value=st.session_state.aff_rent_store['rent_inc'], step=0.1)
        st.session_state.aff_rent_store['inv_return'] = st.number_input("Inv. Return Rate (%)", value=st.session_state.aff_rent_store['inv_return'], help="Return on the difference invested", step=0.1)

# --- 5. CALCULATION ENGINE ---
P = st.session_state.aff_rent_store['price']
DP = st.session_state.aff_rent_store['dp']
r_mort = st.session_state.aff_rent_store['rate'] / 100 / 12
n_months = 300 # 25 years amortization fixed
Loan = P - DP
Monthly_PI = Loan * (r_mort * (1 + r_mort)**n_months) / ((1 + r_mort)**n_months - 1)

data = []
cum_own_sunk = 0
cum_rent_sunk = 0
home_val = P
rem_loan = Loan
rent_val = st.session_state.aff_rent_store['rent']
portfolio = DP # Renter starts with DP invested

for year in range(1, st.session_state.aff_rent_store['years'] + 1):
    # OWNER COSTS
    yr_tax = st.session_state.aff_rent_store['ann_tax'] * (1.02**(year-1)) # Assume 2% tax inflation
    yr_maint = st.session_state.aff_rent_store['mo_maint'] * 12 * (1.02**(year-1))
    
    # Mortgage Split
    yr_interest = 0
    yr_principal = 0
    for m in range(12):
        if rem_loan > 0:
            inte = rem_loan * r_mort
            prin = Monthly_PI - inte
            yr_interest += inte
            yr_principal += prin
            rem_loan -= prin
    
    # Total Owner Cash Outflow this year
    total_own_outflow = (Monthly_PI * 12) + yr_tax + yr_maint
    
    # Owner Sunk Cost (Money gone forever: Interest + Tax + Maint)
    # Principal payment is NOT a sunk cost (it's forced savings)
    annual_own_sunk = yr_interest + yr_tax + yr_maint
    cum_own_sunk += annual_own_sunk
    
    # RENTER COSTS
    yr_rent = rent_val * 12
    # Renter Sunk Cost (Rent is 100% sunk)
    cum_rent_sunk += yr_rent
    
    # OPPORTUNITY COST / INVESTMENT
    # Did the owner spend more cash than the renter?
    diff = total_own_outflow - yr_rent
    
    if diff > 0:
        # Owner spent more. Renter invests the difference.
        portfolio = (portfolio * (1 + st.session_state.aff_rent_store['inv_return']/100)) + diff
    else:
        # Renter spent more (Rent > Mortgage+Costs). Owner invests the savings?
        # For simplicity in this model, we usually just reduce the renter's portfolio growth 
        # or assume renter withdraws from portfolio to pay rent.
        # Here we assume Renter Portfolio grows, but reduced by the shortfall if any.
        portfolio = (portfolio * (1 + st.session_state.aff_rent_store['inv_return']/100)) + diff

    # Asset Growth
    home_val = home_val * (1 + st.session_state.aff_rent_store['apprec']/100)
    owner_equity = home_val - rem_loan
    
    # Rent increase for next year
    rent_val = rent_val * (1 + st.session_state.aff_rent_store['rent_inc']/100)

    data.append({
        "Year": year,
        "Owner Net Wealth": owner_equity,
        "Renter Wealth": portfolio,
        "Cum Owner Sunk": cum_own_sunk,
        "Cum Renter Sunk": cum_rent_sunk
    })

df = pd.DataFrame(data)

# --- 6. VISUALIZATION ---
st.write("")
st.subheader("1. Cumulative Wealth Trajectory")
st.write("Comparing the Net Worth of the Homeowner (Home Equity) vs. the Renter (Investment Portfolio) over time.")

fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=df['Year'], y=df['Owner Net Wealth'], name='Homeowner Net Worth', 
                         line=dict(color=CHARCOAL, width=4)))
fig1.add_trace(go.Scatter(x=df['Year'], y=df['Renter Wealth'], name='Renter Net Worth', 
                         line=dict(color=PRIMARY_GOLD, width=4, dash='dash')))

fig1.update_layout(
    height=500,
    plot_bgcolor="white",
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=True, gridcolor='#F0F0F0', tickprefix="$"),
    margin=dict(t=50, l=50, r=20, b=50), # Increased Top Margin to fix cut-off
    legend=dict(orientation="h", y=1.1, x=0),
    title="Cumulative Wealth Over Time"
)
st.plotly_chart(fig1, use_container_width=True)

st.write("")
st.subheader("2. Cumulative Sunk Costs (The 'Unrecoverable' Money)")
st.write("Total money 'thrown away' over time. For Owners: Interest + Tax + Maint. For Renters: 100% of Rent.")

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=df['Year'], y=df['Cum Owner Sunk'], name='Owner Cumulative Sunk Costs',
                         fill='tozeroy', line=dict(color=SLATE_ACCENT, width=2)))
fig2.add_trace(go.Scatter(x=df['Year'], y=df['Cum Renter Sunk'], name='Renter Cumulative Sunk Costs',
                         fill='tozeroy', line=dict(color="#A52A2A", width=2))) # Red for high rent burn

fig2.update_layout(
    height=500,
    plot_bgcolor="white",
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=True, gridcolor='#F0F0F0', tickprefix="$"),
    margin=dict(t=60, l=50, r=20, b=50), # Extra margin for title safety
    legend=dict(orientation="h", y=1.1, x=0),
    title="Cumulative Sunk Costs (Running Total)"
)
st.plotly_chart(fig2, use_container_width=True)

# --- 7. ANALYSIS SUMMARY ---
final_yr = df.iloc[-1]
net_diff = final_yr['Owner Net Wealth'] - final_yr['Renter Wealth']
winner = "Homeowner" if net_diff > 0 else "Renter"

st.markdown("### 💡 Analyst Verdict")
with st.container(border=True):
    if winner == "Homeowner":
        st.success(f"**The Homeowner Wins by ${net_diff:,.0f}** after {st.session_state.aff_rent_store['years']} years.")
        st.write("The forced savings of mortgage principal and tax-free capital gains outweighed the flexibility of renting.")
    else:
        st.warning(f"**The Renter Wins by ${abs(net_diff):,.0f}** after {st.session_state.aff_rent_store['years']} years.")
        st.write("The opportunity cost of the down payment (invested in the market) outperformed the real estate appreciation.")

# --- 8. DISCLAIMER ---
st.markdown("---")
st.caption("Figures are estimates based on constant rates of return. Inflation and variable rates are not modeled.")
