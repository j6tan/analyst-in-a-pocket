import streamlit as st
import pandas as pd
import numpy as np
import os
from style_utils import inject_global_css, show_disclaimer
from data_handler import init_session_state, load_user_data

# --- 1. CONFIG & AUTH ---
init_session_state()
inject_global_css()

try:
    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent="analyst_in_a_pocket_v1")
except Exception:
    geolocator = None

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 2. BRANDING ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"

prof = st.session_state.app_db.get('profile', {})
p1_name = prof.get('p1_name', 'Client 1')
p2_name = prof.get('p2_name', 'Client 2')

st.title("Pro Rental Portfolio Analyzer")

# --- 3. GLOBAL SETTINGS PANEL (RE-ALIGNED) ---
with st.container(border=True):
    st.subheader("⚙️ Global Settings")
    
    # Row 1: Financing & Down Payment
    g_col1, g_col2, g_col3, g_col4 = st.columns([2, 1, 1, 1])
    with g_col1:
        dp_mode = st.radio("Down Payment Mode", ["Percentage (%)", "Fixed Amount ($)"], horizontal=True)
    with g_col2:
        # Centralized Down Payment Input
        dp_global_val = st.number_input(f"Global Down Payment ({'%' if 'Percent' in dp_mode else '$'})", value=20.0 if "Percent" in dp_mode else 100000.0)
    with g_col3:
        m_rate = st.number_input("Mortgage Interest Rate (%)", value=5.1, step=0.1)
    with g_col4:
        m_amort = st.number_input("Amortization (Years)", value=25, step=1)
    
    # Row 2: Management Logic
    g_col5, g_col6, g_col7 = st.columns([2, 1, 1])
    with g_col5:
        use_mgmt = st.checkbox("Will you use a Property Manager?")
    with g_col6:
        mgmt_fee = st.number_input("Property Management Fee (%)", value=8.0, step=0.5) if use_mgmt else 0.0
    with g_col7:
        st.write("") 

# --- 4. LISTING MANAGEMENT ---
if 'rental_listings' not in st.session_state:
    st.session_state.rental_listings = [
        {"address": "3399 Noel Drive, Burnaby, BC", "lat": 49.2667, "lon": -122.9000, "price": 800000, "tax": 3000, "strata": 400, "rent": 3500, "beds": 2, "baths": 2, "year": 2010, "ins": 100},
    ]

def geocode_address(index):
    if not geolocator: return
    addr = st.session_state.rental_listings[index]['address']
    if addr:
        try:
            location = geolocator.geocode(addr)
            if location:
                st.session_state.rental_listings[index]['lat'] = location.latitude
                st.session_state.rental_listings[index]['lon'] = location.longitude
                st.session_state.rental_listings[index]['address'] = location.address
                st.toast(f"📍 Added to Map: {location.address}")
        except: pass

st.subheader("🏠 Property Underwriting")

for i, listing in enumerate(st.session_state.rental_listings):
    with st.expander(f"#{i+1}: {listing['address'][:25]}...", expanded=(i==0)):
        
        # Row 1: Address (Reduced 20%) & Map Button
        r1_c1, r1_c2, r1_c3 = st.columns([2, 1, 1])
        with r1_c1:
            listing['address'] = st.text_input("Property Address", value=listing['address'], key=f"addr_{i}", label_visibility="collapsed")
        with r1_c2:
            st.button("📍 Add to Map", key=f"geo_{i}", on_click=geocode_address, args=(i,), use_container_width=True)
        with r1_c3:
            if st.button("🗑️ Remove", key=f"del_{i}", use_container_width=True):
                st.session_state.rental_listings.pop(i)
                st.rerun()

        # Row 2: Pricing (Increased 30%) & Rents
        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns([2, 1, 1, 1])
        with r2_c1: listing['price'] = st.number_input("Listing Price ($)", value=listing['price'], key=f"pr_{i}")
        with r2_c2: listing['rent'] = st.number_input("Monthly Rent ($)", value=listing['rent'], key=f"rt_{i}")
        with r2_c3: listing['beds'] = st.number_input("Beds", value=listing.get('beds', 1), key=f"bd_{i}")
        with r2_c4: listing['baths'] = st.number_input("Baths", value=listing.get('baths', 1), key=f"ba_{i}")

        # Row 3: Operational Costs
        r3_c1, r3_c2, r3_c3, r3_c4, r3_c5 = st.columns([1, 1, 1, 1, 1])
        with r3_c1: listing['tax'] = st.number_input("Property Tax ($)", value=listing['tax'], key=f"tx_{i}")
        with r3_c2: listing['strata'] = st.number_input("Strata Fee ($)", value=listing['strata'], key=f"st_{i}")
        with r3_c3: listing['ins'] = st.number_input("Est. Monthly Insurance ($)", value=listing.get('ins', 100), key=f"in_{i}")
        with r3_c4: listing['year'] = st.number_input("Year Built", value=listing.get('year', 2000), key=f"yr_{i}")
        with r3_c5: listing['sqft'] = st.number_input("Sqft", value=listing.get('sqft', 0), key=f"sq_{i}")

if len(st.session_state.rental_listings) < 10:
    st.button("➕ Add Listing", on_click=lambda: st.session_state.rental_listings.append({"address": "", "lat": 0.0, "lon": 0.0, "price": 0, "tax": 0, "strata": 0, "rent": 0}))

# --- 5. CALCULATIONS ---
results = []
for l in st.session_state.rental_listings:
    if l['price'] > 0 and l['lat'] != 0.0:
        mgmt_cost = (l['rent'] * 12 * (mgmt_fee / 100))
        reserves = (l['rent'] * 12 * 0.05) # 5% vacancy/maintenance reserve
        gross_inc = l['rent'] * 12
        # Operating Expenses include tax, strata, monthly insurance (x12), management, and reserves
        op_ex = l['tax'] + (l['strata'] * 12) + (l['ins'] * 12) + mgmt_cost + reserves
        noi = gross_inc - op_ex
        
        # Financing logic tied to Global Settings
        dp_amt = (l['price'] * (dp_global_val / 100)) if "Percent" in dp_mode else dp_global_val
        loan = l['price'] - dp_amt
        r = (m_rate / 100) / 12
        n = m_amort * 12
        pmt = loan * (r * (1 + r)**n) / ((1 + r)**n - 1) if r > 0 else loan / n
        ann_mtg = pmt * 12
        net_cf = noi - ann_mtg
        
        results.append({
            "Address": l['address'], "Price": l['price'], "DP": dp_amt,
            "Gross": gross_inc, "OpEx": op_ex, "Mtg": ann_mtg,
            "Cap Rate %": (noi / l['price']) * 100,
            "CoC %": (net_cf / dp_amt) * 100 if dp_amt > 0 else 0,
            "Net $": net_cf, "lat": l['lat'], "lon": l['lon']
        })

# --- 6. OUTPUTS ---
if results:
    df_res = pd.DataFrame(results)
    st.divider()
    st.subheader("🗺️ Portfolio Map")
    st.map(df_res)

    st.subheader("📊 Comparative Ranking")
    sort_by = st.radio("Metric:", ["CoC %", "Cap Rate %", "Net $"], horizontal=True)
    df_ranked = df_res.sort_values(by=sort_by, ascending=False)
    
    st.dataframe(
        df_ranked.drop(columns=['lat', 'lon', 'DP', 'Gross', 'OpEx', 'Mtg']), 
        use_container_width=True, hide_index=True,
        column_config={"Price": st.column_config.NumberColumn(format="$%d"), "Net $": st.column_config.NumberColumn(format="$%d"),
                       "Cap Rate %": st.column_config.NumberColumn(format="%.2f%%"), "CoC %": st.column_config.ProgressColumn(min_value=0, max_value=15, format="%.2f%%")}
    )

    # Deep Underwriting Summary
    top = df_ranked.iloc[0]
    st.success(f"🏆 **Top Underwritten Selection:** {top['Address']}")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Down Payment Required", f"${top['DP']:,.0f}")
    r2.metric("Gross Annual Income", f"${top['Gross']:,.0f}")
    r3.metric("Annual Operating Ex", f"${top['OpEx']:,.0f}")
    r4.metric("Annual Mortgage", f"${top['Mtg']:,.0f}")

show_disclaimer()
