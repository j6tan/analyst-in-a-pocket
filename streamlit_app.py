import streamlit as st

# --- 1. INITIALIZE GLOBAL VAULT (Must be before pg.run) ---
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        "p1_name": "Investor", "p1_t4": 0.0, "p2_t4": 0.0, 
        "province": "Ontario", "is_pro": False # Change to True to unlock everything
    }

# --- 2. DEFINE NAVIGATION ---
pages = [
    st.Page("home.py", title="Home Dashboard", icon="🏠", default=True),
    st.Page("scripts/profile.py", title="Client Profile", icon="👤"),
    # Free Tier Tools
    st.Page("scripts/affordability.py", title="Affordability Primary", icon="📊"),
    st.Page("scripts/buy_vs_rent.py", title="Buy vs Rent", icon="⚖️"),
    # Pro Tier Tools
    st.Page("scripts/affordability_second.py", title="Secondary Home", icon="🏢"),
    st.Page("scripts/mortgage_scenario.py", title="Mortgage Scenarios", icon="📈"),
    st.Page("scripts/renewal_analysis.py", title="Renewal Dilemma", icon="🔄"),
    st.Page("scripts/rental_vs_stock.py", title="Rental vs Stock", icon="🏠")
]

pg = st.navigation(pages, position="hidden")
pg.run()
