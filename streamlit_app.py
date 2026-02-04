import streamlit as st

# 1. THIS MUST BE FIRST
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        "p1_name": "Investor",
        "is_pro": False,
        # ... include all other default keys here ...
    }

# 2. Define pages
pages = [
    st.Page("home.py", title="Dashboard", icon="🏠", default=True),
    st.Page("scripts/profile.py", title="Profile", icon="👤"),
    # ... other pages
]

# 3. Create and Run navigation
pg = st.navigation(pages, position="hidden")
pg.run()
