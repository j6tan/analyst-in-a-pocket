import streamlit as st
import datetime
from data_handler import supabase # Assuming your Supabase client is here

def get_membership_status():
    """
    Returns a dict with 'is_pro' (bool) and 'tier' (str).
    Checks expiry dates for 48h and Monthly members.
    """
    # 1. Check if user is even logged in
    username = st.session_state.get("username")
    if not username:
        return {"is_pro": False, "tier": "Public"}

    # 2. Fetch the user's record from Supabase
    try:
        response = supabase.table("profiles").select("membership_tier, pro_until").eq("username", username).execute()
        if not response.data:
            return {"is_pro": False, "tier": "Public"}
        
        user_record = response.data[0]
        tier = user_record.get("membership_tier", "Public")
        pro_until_str = user_record.get("pro_until")

        # 3. Handle Life Membership
        if tier == "Life":
            return {"is_pro": True, "tier": "Life"}

        # 4. Handle Time-Limited Memberships (48h and Monthly)
        if pro_until_str:
            pro_until = datetime.datetime.fromisoformat(pro_until_str)
            if datetime.datetime.now() < pro_until:
                return {"is_pro": True, "tier": tier}
            else:
                # OPTIONAL: Automatically demote them in DB if expired
                # supabase.table("profiles").update({"membership_tier": "Public"}).eq("username", username).execute()
                return {"is_pro": False, "tier": "Expired"}

    except Exception as e:
        print(f"Membership check error: {e}")
        return {"is_pro": False, "tier": "Error"}

    return {"is_pro": False, "tier": "Public"}

def require_pro(feature_name="this tool"):
    """
    Call this at the top of Pro pages. 
    If not Pro, it shows the paywall and STOPS the script.
    """
    status = get_membership_status()
    if not status["is_pro"]:
        st.markdown(f"""
            <div style="background-color: #F8F9FA; padding: 40px; border-radius: 15px; text-align: center; border: 1px solid #ddd;">
                <h2 style="color: #333;">🔒 {feature_name}</h2>
                <p style="color: #666;">This is a Premium feature available to our 48-hour, Monthly, and Life members.</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Upgrade My Account", use_container_width=True):
            st.switch_page("pages/membership.py") # Create this page for Stripe
        st.stop()

def smart_save(data_dict):
    """
    Only saves to Supabase if the user is a Pro member.
    """
    status = get_membership_status()
    if status["is_pro"] and st.session_state.get("username"):
        # Import your save function here to avoid circular imports
        from data_handler import save_user_data
        save_user_data(st.session_state.username, data_dict)
    else:
        # Public users: Data stays in st.session_state only
        pass
