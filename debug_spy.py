import streamlit as st
from supabase import create_client

st.set_page_config(layout="wide")
st.title("🕵️ Data Detective")

# 1. Connect
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
    st.success("✅ Connected to Cloud")
except Exception:
    st.error("❌ Connection failed (but we know secrets exist now).")
    st.stop()

# 2. Input
st.write("### Check User Data")
target_user = st.text_input("Enter Username to find:", value="dori")

if st.button("🔎 Search Database"):
    st.write(f"Searching for ID: `{target_user}`...")
    
    # Attempt A: Exact Match (dori)
    res_exact = supabase.table('user_data').select('*').eq('user_id', target_user).execute()
    
    # Attempt B: Capitalized (Dori)
    res_cap = supabase.table('user_data').select('*').eq('user_id', target_user.capitalize()).execute()
    
    # Report Results
    if res_exact.data:
        st.success(f"✅ Found EXACT match for '{target_user}'!")
        st.json(res_exact.data[0])
    elif res_cap.data:
        st.warning(f"⚠️ Found match for '{target_user.capitalize()}' (Capitalized)!")
        st.info("The app is sending lowercase 'dori', but DB has 'Dori'. I need to fix the casing in the code.")
        st.json(res_cap.data[0])
    else:
        st.error(f"❌ No data found for '{target_user}' OR '{target_user.capitalize()}'.")
        st.write("Here are the first 5 IDs that ACTUALLY exist in your table:")
        all_users = supabase.table('user_data').select('user_id').limit(5).execute()
        st.write([row['user_id'] for row in all_users.data])
