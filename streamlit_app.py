import streamlit as st

# --- 1. INITIALIZE GLOBAL VAULT ---
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        "p1_name": "Investor", "p1_t4": 95000.0, "province": "BC",
        "is_pro": False 
    }

# --- 2. DEV TOOLS (Sidebar Toggle) ---
with st.sidebar:
    st.title("🛠️ Dev Tools")
    st.session_state.is_pro = st.checkbox("Simulate Paid Account", value=st.session_state.is_pro)
    st.divider()

# --- 3. OPTION C NAVIGATION (Grouped Sidebar) ---
pages = {
    "Overview": [
        st.Page("home.py", title="Home Dashboard", icon="🏠", default=True),
        st.Page("scripts/profile.py", title="Client Profile", icon="👤"),
    ],
    "🏠 Foundations & Budgeting": [
        st.Page("scripts/budget_tracker.py", title="Monthly Budget Tracker", icon="📊"),
        st.Page("scripts/affordability.py", title="Simple Affordability", icon="🤔"),
        st.Page("scripts/buy_vs_rent.py", title="Buy vs Rent", icon="⚖️"),
    ],
    "💰 Buying & Selling Process": [
        st.Page("scripts/buying_costs.py", title="House Buying Costs", icon="💸"),
        st.Page("scripts/selling_proceeds.py", title="Selling & Proceeds", icon="💰"),
        st.Page("scripts/mortgage_simple.py", title="Simple Mortgage Calc", icon="🧮"),
        st.Page("scripts/listing_comparison.py", title="Buying Analysis (Compare)", icon="🏘️"),
    ],
    "🚀 Advanced Wealth Strategy": [
        st.Page("scripts/mortgage_scenario.py", title="Mortgage Scenarios 🔒", icon="📈"),
        st.Page("scripts/smith_maneuver.py", title="Smith Maneuver 🔒", icon="🛡️"),
        st.Page("scripts/affordability_second.py", title="Secondary Property 🔒", icon="🏢"),
        st.Page("scripts/renewal_scenario.py", title="Renewal Scenario 🔒", icon="🔄"),
        st.Page("scripts/rental_vs_stock.py", title="Rental vs Stock 🔒", icon="📉"),
        st.Page("scripts/rental_analysis.py", title="Rental Analysis 🔒", icon="📋"),
        st.Page("scripts/refinance.py", title="Refinance 🔒", icon="🏦"),
    ],
    "🛠️ Developer Toolkit": [
        st.Page("scripts/land_residual.py", title="Land Residual", icon="🏗️"),
        st.Page("scripts/income_proforma.py", title="Income Proforma", icon="📈"),
        st.Page("scripts/comparable_analysis.py", title="Comparable Analysis", icon="📋"),
    ]
}

pg = st.navigation(pages)
pg.run()
