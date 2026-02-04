import streamlit as st

st.title("🚀 FIRE Investor Hub")

# Passport Summary
with st.container(border=True):
    st.write(f"### 👤 Financial Passport: {st.session_state.user_profile.get('p1_name', 'Investor')}")
    if st.button("Edit Profile"):
        st.switch_page("scripts/profile.py")

st.divider()

# Tool Grid
c1, c2 = st.columns(2)

with c1:
    with st.container(border=True):
        st.write("#### 📊 Affordability (Free)")
        if st.button("Open Analysis", key="go_aff"):
            st.switch_page("scripts/affordability.py")

with c2:
    with st.container(border=True):
        st.write("#### 🛡️ Smith Maneuver (Pro) 🔒")
        st.caption("Tax-deductible interest strategy.")
        if st.button("View Tool", key="go_smith"):
            st.switch_page("scripts/smith_maneuver.py")
