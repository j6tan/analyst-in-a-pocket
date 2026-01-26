import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- 1. THEME & BRANDING ---
SCENARIO_COLORS = ["#CEB36F", "#706262", "#2E2B28", "#C0A385", "#E7E7E7"]
PRINCIPAL_COLOR = "#CEB36F" # Gold for Equity/Portfolio
INTEREST_COLOR = "#2E2B28"  # Charcoal for Interest/Debt
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"

# --- 2. PAGE HEADER ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=140)
with header_col2:
    st.title("The Smith Maneuver Strategy")

# --- 3. STORYTELLING: SARAH & JAMES ---
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRINCIPAL_COLOR}; margin-bottom: 20px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.5em;">🛡️ Sarah & James: The Wealth Accelerator</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Sarah wants the security of a paid-off home, while James wants to grow their net worth. By <b>converting</b> their mortgage into a tax-deductible investment loan, they can satisfy both. This tool tracks their journey from "Bad Debt" to "Good Debt."
    </p>
</div>
""", unsafe_allow_html=True)

# --- 4. CALCULATION ENGINE ---
def run_smith_maneuver_v4(m_bal, m_rate, m_amort_rem, invested_heloc, idle_heloc, tax_rate, roi, reinvest_refunds):
    mo_m_rate = (m_rate / 100) / 12
    mo_h_rate = ((m_rate + 0.5) / 100) / 12 # Assuming HELOC is Prime + Spread
    mo_roi = (roi / 100) / 12
    total_months = m_amort_rem * 12
    
    # Calculate Payment based on REMAINING amortization
    base_pmt = m_bal * (mo_m_rate * (1 + mo_m_rate)**total_months) / ((1 + mo_m_rate)**total_months - 1)
    
    curr_m_bal = m_bal
    curr_h_invested = invested_heloc
    curr_h_idle = idle_heloc
    curr_portfolio = invested_heloc
    cum_tax_savings = 0
    data = []
    
    for m in range(1, total_months + 1):
        if curr_m_bal <= 0:
            curr_portfolio *= (1 + mo_roi)
        else:
            m_int = curr_m_bal * mo_m_rate
            m_prin = base_pmt - m_int
            
            # Reinvest tax refunds from previous year back into mortgage
            extra_pay = (cum_tax_savings / 12) if (reinvest_refunds and m > 12) else 0
            
            total_reduction = m_prin + extra_pay
            curr_m_bal -= total_reduction
            
            # All principal paid unlocks HELOC room
            curr_h_idle += total_reduction
            
            # USER LOGIC: Most SM users invest the room as it opens
            # (If saving for a rental, user can toggle ROI or timing manually)
            curr_h_invested += curr_h_idle
            curr_portfolio += curr_h_idle
            curr_h_idle = 0 # Room is now deployed
            
            curr_portfolio *= (1 + mo_roi)
            
            # Tax deduction only applies to the INVESTED portion
            h_int_mo = curr_h_invested * mo_h_rate
            tax_sav_mo = h_int_mo * (tax_rate / 100)
            cum_tax_savings += tax_sav_mo

        if m % 12 == 0 or curr_m_bal <= 0:
            data.append({
                "Year": round(m/12, 1),
                "Mortgage": max(0, curr_m_bal),
                "Deductible HELOC": curr_h_invested,
                "Portfolio Value": curr_portfolio,
                "Tax Refunds": cum_tax_savings
            })
            if curr_m_bal <= 0: break 

    return pd.DataFrame(data)

# --- 5. INPUT SIDEBAR (CLEAR & AMBIGUITY-FREE) ---
with st.sidebar:
    st.header("🏠 Mortgage (Bad Debt)")
    m_bal = st.number_input("Remaining Mortgage Balance ($)", value=500000, help="What you owe the bank TODAY.")
    m_rate = st.number_input("Mortgage Rate (%)", value=4.5, step=0.1, help="Assuming your current fixed or variable rate.")
    m_amort = st.slider("Remaining Amortization (Years)", 1, 30, 20, help="Years left until the mortgage is $0.")
    
    st.header("💰 Tax & Income")
    tax_rate = st.slider("Marginal Tax Rate (%)", 20, 54, 35, 
                         help="The tax applied to your HIGHEST dollar earned. Look up your 2024 provincial bracket.")
    
    st.header("🛡️ HELOC Setup")
    invested_h = st.number_input("Existing Invested HELOC ($)", value=0, help="Money already borrowed and sitting in assets.")
    idle_h = st.number_input("Available Idle HELOC ($)", value=0, help="Equity paid down but NOT yet borrowed/invested.")

    st.header("📈 Investment Return")
    roi = st.number_input("Total Expected Return (%)", value=7.0, 
                          help="Stocks: Div + Growth | Rental: Net Rent + Appreciation")
    
    reinvest = st.toggle("🚀 Reinvest Tax Refunds?", value=True)

# --- 6. EXECUTION & VISUALS ---
df = run_smith_maneuver_v4(m_bal, m_rate, m_amort, invested_h, idle_h, tax_rate, roi, reinvest)

# Metrics
m_payoff = df[df['Mortgage'] == 0]['Year'].iloc[0] if (df['Mortgage'] == 0).any() else m_amort
col1, col2, col3 = st.columns(3)
col1.metric("Debt-Free Home", f"{m_payoff} Years", delta=f"{m_payoff - m_amort:.1f} Years" if reinvest else None, delta_color="inverse")
col2.metric("Final Portfolio", f"${df['Portfolio Value'].iloc[-1]:,.0f}")
col3.metric("Total Tax Cash-Back", f"${df['Tax Refunds'].iloc[-1]:,.0f}")

st.divider()

# CHART 1: Debt Conversion
st.subheader("1. The Debt Conversion Journey")
fig_debt = go.Figure()
fig_debt.add_trace(go.Scatter(x=df["Year"], y=df["Mortgage"], name="Non-Deductible (Bad Debt)", fill='tozeroy', line=dict(color=INTEREST_COLOR, width=3)))
fig_debt.add_trace(go.Scatter(x=df["Year"], y=df["Deductible HELOC"], name="Tax-Deductible (Good Debt)", fill='tonexty', line=dict(color=PRINCIPAL_COLOR, width=3)))
fig_debt.update_layout(hovermode="x unified", plot_bgcolor="white", height=400, yaxis=dict(tickprefix="$"))
st.plotly_chart(fig_debt, use_container_width=True)

# CHART 2: Wealth Accumulation
st.subheader("2. Total Wealth Growth")
fig_wealth = go.Figure()
fig_wealth.add_trace(go.Bar(x=df["Year"], y=df["Portfolio Value"], name="Portfolio (Stocks/Rental)", marker_color=PRINCIPAL_COLOR))
fig_wealth.add_trace(go.Scatter(x=df["Year"], y=df["Tax Refunds"], name="Cumulative Tax Refunds", line=dict(color=INTEREST_COLOR, width=4)))
fig_wealth.update_layout(hovermode="x unified", plot_bgcolor="white", height=400, yaxis=dict(tickprefix="$"))
st.plotly_chart(fig_wealth, use_container_width=True)

# --- 7. STRATEGIC INSIGHT ---
st.info(f"**Analyst Insight:** By using the Smith Maneuver, Sarah and James convert their largest expense (mortgage interest) into a tax refund. By Year {m_payoff}, they own the home outright and have built a ${df['Portfolio Value'].iloc[-1]:,.0f} investment nest egg.")

# --- 8. LEGAL DISCLAIMER ---
st.markdown("---")
st.markdown("""
<div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
    <p style='font-size: 11px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
        <strong>⚠️ Disclaimer:</strong> The Smith Maneuver involves investment risk and leverage. If your portfolio return is lower than your HELOC interest rate, you may lose money. This tool is for educational purposes only.
    </p>
</div>
""", unsafe_allow_html=True)