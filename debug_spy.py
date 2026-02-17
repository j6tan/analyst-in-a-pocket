import streamlit as st
import os

st.set_page_config(layout="wide")
st.title("🔑 Secrets Detective")

st.write("### 1. Diagnostics")

# A. Check if secrets file exists (Internal check)
try:
    # List all top-level keys (Masking values for safety)
    keys_found = list(st.secrets.keys())
    
    if not keys_found:
        st.error("❌ NO SECRETS FOUND. The app sees an empty secrets file.")
    else:
        st.success(f"✅ Found {len(keys_found)} keys in secrets.")
        st.write("**Keys detected:**")
        st.code(keys_found) # <--- THIS IS WHAT I NEED TO SEE

        # B. Check for the specific key we need
        if "SUPABASE_URL" in st.secrets:
            st.success("✅ SUPABASE_URL is present.")
            val = st.secrets["SUPABASE_URL"]
            st.write(f"Value starts with: `{val[:10]}...`") 
            # Check for quotes in the value (Common error)
            if val.startswith('"') or val.startswith("'"):
                st.error("⚠️ WARNING: The value includes quotes inside the string! In TOML, you don't need double quotes if you already used them in the dashboard.")
        else:
            st.error("❌ SUPABASE_URL is MISSING from the top level.")

        # C. Check for nested sections (e.g. [supabase])
        if "supabase" in st.secrets:
            st.info("ℹ️ Found a '[supabase]' section. Checking inside...")
            nested_keys = list(st.secrets["supabase"].keys())
            st.code(nested_keys)
            
except Exception as e:
    st.error(f"Error reading secrets: {e}")

st.divider()
st.write("### 2. How to Fix")
st.markdown("""
If the list above is empty or does not contain `SUPABASE_URL`, you must:
1. Go to **Manage App** (bottom right) -> **⋮** -> **Settings** -> **Secrets**.
2. **DELETE EVERYTHING** in the box.
3. Type the following **MANUALLY** (Do not copy-paste, to avoid invisible characters):
""")
st.code("""
SUPABASE_URL = "https://your-url.supabase.co"
SUPABASE_KEY = "your-key"
""", language="toml")
