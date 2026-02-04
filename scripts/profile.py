import streamlit as st
import json
import os

# Link back to the save function in the main app context
def sync_data():
    # This calls the save logic to ensure the JSON file updates
    with open("user_profile_db.json", "w") as f:
        json.dump(st.session_state.user_profile, f, indent=4)

if st.button("⬅️ Back to Dashboard"):
    st.switch_page("home.py")

st.title("👤 General Client Information")
st.info("Changes are saved automatically to your local session.")

# --- SECTION 1: HOUSEHOLD INCOME ---
st.subheader("👥 Household Income Details")
c1, c2 = st.columns(2)

with c1:
    st.markdown("### Primary Client")
    st.session_state.user_profile['p1_name'] = st.text_input(
        "Full Name", 
        value=st.session_state.user_profile.get('p1_name', ""),
        on_change=sync_data
    )
    st.session_state.user_profile['p1_t4'] = st.number_input(
        "T4 (Employment Income)", 
        value=float(st.session_state.user_profile.get('p1_t4', 0.0)),
        on_change=sync_data
    )

with c2:
    st.markdown("### Co-Owner / Partner")
    st.session_state.user_profile['p2_name'] = st.text_input(
        "Full Name ", 
        value=st.session_state.user_profile.get('p2_name', ""),
        on_change=sync_data
    )
    st.session_state.user_profile['p2_t4'] = st.number_input(
        "T4 (Employment Income) ", 
        value=float(st.session_state.user_profile.get('p2_t4', 0.0)),
        on_change=sync_data
    )

st.divider()

# --- SECTION 2: HOUSING STATUS ---
st.subheader("🏠 Housing & Property Details")
h_toggle, h_data = st.columns([1, 2])

with h_toggle:
    current_status = st.session_state.user_profile.get('housing_status', "Renting")
    st.session_state.user_profile['housing_status'] = st.radio(
        "Current Status", 
        ["Renting", "Owning"], 
        index=0 if current_status == "Renting" else 1,
        on_change=sync_data
    )

with h_data:
    if st.session_state.user_profile['housing_status'] == "Renting":
        st.session_state.user_profile['rent_pmt'] = st.number_input(
            "Monthly Rent ($)", 
            value=float(st.session_state.user_profile.get('rent_pmt', 0.0)),
            on_change=sync_data
        )
    else:
        sub_c1, sub_c2 = st.columns(2)
        with sub_c1:
            st.session_state.user_profile['m_bal'] = st.number_input(
                "Mortgage Balance ($)", 
                value=float(st.session_state.user_profile.get('m_bal', 0.0)),
                on_change=sync_data
            )
        with sub_c2:
            st.session_state.user_profile['province'] = st.selectbox(
                "Province", 
                ["Ontario", "BC", "Alberta", "Quebec"],
                index=0,
                on_change=sync_data
            )

st.success("✅ Your profile is synchronized.")
