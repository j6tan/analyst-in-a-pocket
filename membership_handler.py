import streamlit as st
import datetime
from data_handler import supabase # Assuming your Supabase client is here

# ==========================================
# 📂 THE MASTER PAGE ORGANIZER
# ==========================================
# Define which pages are 'public' and which require 'pro'
PAGE_ACCESS_CONFIG = {
    "home": "public",
    "affordability": "public",
    "flip_analyzer": "public", # Example
    "brrrr": "pro",
    "smith_manoeuvre": "pro",
    "proforma_builder": "pro" # Example
}

# ==========================================
# 🧠 MEMBERSHIP LOGIC
# ==========================================
def get_membership_status():
    """Returns a dict checking if the user has an active Pro membership."""
    username = st.session_state.get("username")
    if not username:
        return {"is_pro": False, "tier": "Public"}

    try:
        response = supabase.table("profiles").select("membership_tier, pro_until").eq("username", username).execute()
        if not response.data:
            return {"is_pro": False, "tier": "Public"}
        
        user_record = response.data[0]
        tier = user_record.get("membership_tier", "Public")
        pro_until_str = user_record.get("pro_until")

        if tier == "Life":
            return {"is_pro": True, "tier": "Life"}

        if pro_until_str:
            pro_until = datetime.datetime.fromisoformat(pro_until_str)
            if datetime.datetime.now() < pro_until:
                return {"is_pro": True, "tier": tier}
            else:
                return {"is_pro": False, "tier": "Expired"}

    except Exception as e:
        print(f"Membership check error: {e}")
        return {"is_pro": False, "tier": "Error"}

    return {"is_pro": False, "tier": "Public"}

# ==========================================
# 🛑 THE GATEKEEPER
# ==========================================
def enforce_page_access(page_id, pretty_name="This tool"):
    """
    Checks the Master Organizer. If the page is 'pro', verifies membership.
    If the user is not a member, drops the paywall and stops the app.
    """
    access_level = PAGE_ACCESS_CONFIG.get(page_id, "public")
    
    if access_level == "public":
        return # Let them pass immediately

    # If it's a Pro page, check their status
    status = get_membership_status()
    if not status["is_pro"]:
        st.markdown(f"""
            <div style="background-color: #F8F9FA; padding: 40px; border-radius: 15px; text-align: center; border: 1px solid #ddd; margin-top: 20px;">
                <div style="font-size: 50px; margin-bottom: 10px;">🔒</div>
                <h2 style="color: #333; margin-top: 0;">{pretty_name} is a Pro Feature</h2>
                <p style="color: #666; font-size: 1.1em;">Upgrade to a 48-Hour, Monthly, or Life membership to unlock this strategy and save your scenarios.</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("🚀 View Upgrade Options", type="primary", use_container_width=True):
                st.switch_page("pages/membership.py") # Directs to your pricing page
        
        st.stop() # CRITICAL: This hides the rest of the calculator from free users

# ==========================================
# 💾 SMART SYNC
# ==========================================
def smart_save(data_dict):
    """Only saves to Supabase if the user is a Pro member."""
    status = get_membership_status()
    if status["is_pro"] and st.session_state.get("username"):
        from data_handler import save_user_data
        save_user_data(st.session_state.username, data_dict)
