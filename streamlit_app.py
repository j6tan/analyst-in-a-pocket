import streamlit as st

# Initialize Global Session State
if 'is_pro' not in st.session_state:
    st.session_state.is_pro = False # Set to True to test the unlocked version

pages = [
    st.Page("home.py", title="Dashboard", icon="🏠", default=True),
    st.Page("scripts/profile.py", title="Profile", icon="👤"),
    st.Page("scripts/affordability.py", title="Affordability", icon="📊"),
    st.Page("scripts/smith_maneuver.py", title="Smith Maneuver", icon="🛡️"),
    st.Page("scripts/mortgage_scenario.py", title="Mortgage Scenarios", icon="📈"),
]

pg = st.navigation(pages, position="hidden")
pg.run()
