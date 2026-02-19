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

# --- 3. GLOBAL SETTINGS PANEL (Compact) ---
with st.container(border=True):
    st.subheader("⚙️ Global Settings")
    g_col1, g_col2, g_col3, g_col4, g_col5 = st.columns([2, 1, 1, 1, 1])
    with g_col1:
        dp_mode = st.radio("Down Payment Mode", ["%", "$"], horizontal=True)
    with g_col2:
        m_rate = st.number_input("Mtg %", value=5.1, step=0.1)
    with g_col3:
        m_amort = st.number_input("Amort (Yr)", value=25, step=1)
    with g_col4:
        use_mgmt = st.checkbox("Mgmt?")
        mgmt_fee = st.number_input("Fee %", value=8.0, step=0.5) if use_mgmt else 0.0
    with g_col5:
        st.write("") # Spacer

# --- 4. LISTING MANAGEMENT ---
if 'rental_listings' not in st.session_state:
    st.session_state.rental_listings = [
        {"address": "3399 Noel Drive, Burnaby, BC", "lat": 49.2667, "lon": -122.9000, "price": 800000, "tax": 3000, "strata": 400, "rent": 3500},
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
                st.toast(f"📍 Mapped: {location.address}")
        except: pass

st.subheader("🏠 Property Underwriting")

for i, listing in enumerate(st.session_state.rental_listings):
    with st.expander(f"#{i+1}: {listing['address'][:30]}...", expanded=(i==0)):
        
        # Row 1: Address (Compact) & Map Button
        r1_c1, r1_c2, r1_c3 = st.columns([3, 1, 1])
        with r1_c1:
            listing['address'] = st.text_input("Address", value=listing['address'], key=f"addr_{i}", label_visibility="collapsed")
        with r1_c2:
            st.button("📍 Add to Map", key=f"geo_{i}", on_click=geocode_address, args=(i,), use_container_width=True)
        with r1_c3:
            if st.button("🗑️", key=f"del_{i}", use_container_width=True):
                st.session_state.rental_listings.pop(i)
                st.rerun()

        # Row 2: Financials (50% size reduction via 6-column split)
        r2_c1, r2_c2, r2_c3, r2_c4, r2_c5, r2_c6 = st.columns(6)
        with r2_c1: listing['price'] = st.number_input("Price ($)", value=listing['price'], key=f"pr_{i}")
        with r2_c2: 
            dp_label = "DP (%)" if dp_mode == "%" else "DP ($)"
            listing['dp_val'] = st.number_input(dp_label, value=listing.get('dp_val', 20.0), key=f"dp_{i}")
        with r2_c3: listing['rent'] = st.number_input("Rent ($)", value=listing['rent'], key=f"rt_{i}")
        with r2_c4: listing['beds'] = st.number_input("Beds", value=listing.get('beds', 1), key=f"bd_{i}")
        with r2_c5: listing['baths'] = st.number_input("Baths", value=listing.get('baths', 1), key=f"ba_{i}")
        with r2_c6: listing['sqft'] = st.number_input("Sqft", value=listing.get('sqft', 0), key=f"sq_{i}")

        # Row 3: Recurring Costs (50% size reduction)
        r3_c1, r3_c2, r3_c3, r3_c4, r3_c5, r3_c6 = st.columns(6)
        with r3_c1: listing['tax'] = st.number_input("Tax ($)", value=listing['tax'], key=f"tx_{i}")
        with r3_c2: listing['strata'] = st.number_input("Condo ($)", value=listing['strata'], key=f"st_{i}")
        with r3_c3: listing['ins'] = st.number_input("Ins ($)", value=listing.get('ins', 1000), key=f"in_{i}")
        with r3_c4: listing['year'] = st.number_input("Year", value=listing.get('year', 2000), key=f"yr_{i}")
        with r3_c5: st.write("")
        with r3_c6: st.write("")

if len(st.session_state.rental_listings) < 10:
    st.button("➕ Add Listing", on_click=lambda: st.session_state.rental_listings.append({"address": "", "lat": 0.0, "lon": 0.0, "price": 0, "tax": 0, "strata": 0, "rent": 0}))

# --- 5. CALCULATIONS ---
results = []
for l in st.session_state.rental_listings:
    if l['price'] > 0 and l['lat'] != 0.0:
        mgmt_cost = (l['rent'] * 12 * (mgmt_fee / 100))
        reserves = (l['rent'] * 12 * 0.05) 
        gross_inc = l['rent'] * 12
        op_ex = l['tax'] + (l['strata'] * 12) + l.get('ins', 1000) + mgmt_cost + reserves
        noi = gross_inc - op_ex
        
        dp_amt = (l['price'] * (l.get('dp_val', 20.0) / 100)) if dp_mode == "%" else l.get('dp_val', 0)
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
    st.subheader("🗺️ Geographic View")
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

    # Summary Row
    top = df_ranked.iloc[0]
    st.success(f"🏆 **Top Selection:** {top['Address']}")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("DP Required", f"${top['DP']:,.0f}")
    r2.metric("Gross Income", f"${top['Gross']:,.0f}")
    r3.metric("Operating Ex", f"${top['OpEx']:,.0f}")
    r4.metric("Annual Mtg", f"${top['Mtg']:,.0f}")

show_disclaimer()
