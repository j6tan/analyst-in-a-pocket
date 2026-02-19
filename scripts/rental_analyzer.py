import streamlit as st
import pandas as pd
import numpy as np
import time
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, init_session_state, load_user_data

# --- 1. CONFIG & AUTH ---
init_session_state()
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 2. BRANDING ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"

st.title("Pro Rental Portfolio Analyzer")
st.markdown(f"""
<div style="background-color: #F8F9FA; padding: 20px; border-radius: 10px; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: #4A4E5A; margin-top: 0;">🏢 Multi-Listing Underwriter</h3>
    <p style="color: #4A4E5A; margin-bottom: 0;">
        Compare up to 10 investment properties side-by-side. We factor in <b>Cap Rates</b>, <b>Net Operating Income (NOI)</b>, 
        and 20% down mortgage costs to rank the best opportunities in your market.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 3. GLOBAL INPUTS ---
with st.expander("⚙️ Global Financing Assumptions", expanded=True):
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        m_rate = st.number_input("Mortgage Rate (%)", value=5.1, step=0.1)
    with col_g2:
        m_amort = st.number_input("Amortization (Years)", value=25, step=1)

# --- 4. LISTING INPUTS ---
if 'rental_listings' not in st.session_state:
    st.session_state.rental_listings = [
        {"address": "123 Main St", "lat": 49.2827, "lon": -123.1207, "price": 800000, "tax": 3000, "strata": 400, "rent": 3500},
    ]

def add_listing():
    if len(st.session_state.rental_listings) < 10:
        st.session_state.rental_listings.append({"address": "", "lat": 49.2, "lon": -123.1, "price": 0, "tax": 0, "strata": 0, "rent": 0})

def remove_listing(index):
    if len(st.session_state.rental_listings) > 1:
        st.session_state.rental_listings.pop(index)

st.subheader("📍 Property Details")
for i, listing in enumerate(st.session_state.rental_listings):
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        with c1:
            listing['address'] = st.text_input(f"Address #{i+1}", value=listing['address'], key=f"addr_{i}")
        with c2:
            listing['price'] = st.number_input(f"Price #{i+1}", value=listing['price'], step=10000, key=f"pr_{i}")
        with c3:
            listing['rent'] = st.number_input(f"Monthly Rent #{i+1}", value=listing['rent'], step=100, key=f"rt_{i}")
        with c4:
            st.write("##")
            if st.button("🗑️", key=f"del_{i}"):
                remove_listing(i)
                st.rerun()
        
        # Details row
        d1, d2, d3, d4, d5 = st.columns(5)
        with d1: listing['tax'] = st.number_input(f"Annual Tax", value=listing['tax'], key=f"tx_{i}")
        with d2: listing['strata'] = st.number_input(f"Monthly Strata", value=listing['strata'], key=f"st_{i}")
        with d3: listing['lat'] = st.number_input(f"Latitude", value=listing['lat'], format="%.4f", key=f"lat_{i}")
        with d4: listing['lon'] = st.number_input(f"Longitude", value=listing['lon'], format="%.4f", key=f"lon_{i}")
        with d5: st.write(""); st.write("") # Placeholder

if len(st.session_state.rental_listings) < 10:
    st.button("➕ Add Another Listing", on_click=add_listing)

# --- 5. CALCULATIONS ---
results = []
for l in st.session_state.rental_listings:
    if l['price'] == 0: continue
    
    # Expenses
    annual_expenses = l['tax'] + (l['strata'] * 12) + (l['rent'] * 12 * 0.05) # Incl 5% maintenance
    noi = (l['rent'] * 12) - annual_expenses
    cap_rate = (noi / l['price']) * 100
    
    # Financing (20% Down)
    loan = l['price'] * 0.80
    r = (m_rate / 100) / 12
    n = m_amort * 12
    pmt = loan * (r * (1 + r)**n) / ((1 + r)**n - 1)
    
    annual_mortgage = pmt * 12
    net_cashflow = noi - annual_mortgage
    
    results.append({
        "Address": l['address'],
        "Price": l['price'],
        "Rent": l['rent'],
        "NOI": noi,
        "Cap Rate (%)": round(cap_rate, 2),
        "Annual Net ($)": round(net_cashflow),
        "lat": l['lat'],
        "lon": l['lon']
    })

df_results = pd.DataFrame(results)

# --- 6. VISUALS ---
st.divider()
st.subheader("🗺️ Geographic Distribution")
st.map(df_results[['lat', 'lon']])

st.subheader("📊 Comparison Table")
# Sorting
sort_pref = st.selectbox("Rank by:", ["Best Cap Rate", "Highest Net Cashflow"])
if sort_pref == "Best Cap Rate":
    df_results = df_results.sort_values(by="Cap Rate (%)", ascending=False)
else:
    df_results = df_results.sort_values(by="Annual Net ($)", ascending=False)

st.dataframe(
    df_results.drop(columns=['lat', 'lon']),
    use_container_width=True,
    column_config={
        "Price": st.column_config.NumberColumn(format="$%d"),
        "Rent": st.column_config.NumberColumn(format="$%d"),
        "NOI": st.column_config.NumberColumn(format="$%d"),
        "Annual Net ($)": st.column_config.NumberColumn(format="$%d"),
    }
)

show_disclaimer()
