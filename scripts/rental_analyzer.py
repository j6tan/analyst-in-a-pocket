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
SLATE_ACCENT = "#4A4E5A"

prof = st.session_state.app_db.get('profile', {})
p1_name = prof.get('p1_name', 'Client 1')
p2_name = prof.get('p2_name', 'Client 2')

st.title("Pro Rental Portfolio Analyzer")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px; border-radius: 10px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {CHARCOAL}; margin-top: 0; font-size: 1.5em;">🏢 {p1_name} & {p2_name}: Portfolio Underwriter</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Underwrite up to 10 listings. We factor in <b>Cash-on-Cash (CoC) Return</b> to show you exactly how hard your down payment is working.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 3. GLOBAL ASSUMPTIONS ---
with st.container(border=True):
    col_g1, col_g2 = st.columns(2)
    with col_g1: m_rate = st.number_input("Mortgage Rate (%)", value=5.1, step=0.1)
    with col_g2: m_amort = st.number_input("Amortization (Years)", value=25, step=1)

# --- 4. LISTING MANAGEMENT ---
if 'rental_listings' not in st.session_state:
    st.session_state.rental_listings = [
        {"address": "3399 Noel Drive, Burnaby, BC", "lat": 49.2667, "lon": -122.9000, "price": 800000, "tax": 3000, "strata": 400, "rent": 3500},
    ]

def add_listing():
    if len(st.session_state.rental_listings) < 10:
        st.session_state.rental_listings.append({"address": "", "lat": 0.0, "lon": 0.0, "price": 0, "tax": 0, "strata": 0, "rent": 0})

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
                st.toast(f"📍 Pinned: {location.address}")
        except: pass

# --- 5. INTERFACE ---
for i, listing in enumerate(st.session_state.rental_listings):
    with st.expander(f"🏠 Listing #{i+1}: {listing['address'][:40] if listing['address'] else 'New Entry'}", expanded=(i==0)):
        c1, c2 = st.columns([4, 1])
        with c1: listing['address'] = st.text_input("Property Address", value=listing['address'], key=f"addr_{i}")
        with c2: 
            st.write("##")
            st.button("📍 Fetch Pin", key=f"geo_{i}", on_click=geocode_address, args=(i,))
        
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1: listing['price'] = st.number_input("Listing Price ($)", value=listing['price'], key=f"pr_{i}")
        with col_d2: listing['rent'] = st.number_input("Projected Rent ($)", value=listing['rent'], key=f"rt_{i}")
        with col_d3: 
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.rental_listings.pop(i)
                st.rerun()

        col_e1, col_e2 = st.columns(2)
        with col_e1: listing['tax'] = st.number_input("Annual Property Tax", value=listing['tax'], key=f"tx_{i}")
        with col_e2: listing['strata'] = st.number_input("Monthly Strata", value=listing['strata'], key=f"st_{i}")

if len(st.session_state.rental_listings) < 10:
    st.button("➕ Add Listing", on_click=add_listing)

# --- 6. CALCULATIONS & RANKING ---
results = []
for l in st.session_state.rental_listings:
    if l['price'] > 0 and l['lat'] != 0.0:
        # 5% Maintenance/Vacancy Reserve
        reserves = (l['rent'] * 12 * 0.05)
        gross_income = l['rent'] * 12
        operating_expenses = l['tax'] + (l['strata'] * 12) + reserves
        noi = gross_income - operating_expenses
        cap_rate = (noi / l['price']) * 100
        
        # Financing
        down_payment = l['price'] * 0.20
        loan = l['price'] * 0.80
        r = (m_rate / 100) / 12
        n = m_amort * 12
        pmt = loan * (r * (1 + r)**n) / ((1 + r)**n - 1) if r > 0 else loan / n
        annual_mortgage = pmt * 12
        net_cashflow = noi - annual_mortgage
        
        # Cash-on-Cash Return
        coc_return = (net_cashflow / down_payment) * 100 if down_payment > 0 else 0
        
        results.append({
            "Address": l['address'], "Price": l['price'], "Down Payment": down_payment,
            "Gross Income": gross_income, "Op Expenses": operating_expenses,
            "Mtg Payment (Annual)": annual_mortgage, "Cap Rate (%)": cap_rate,
            "CoC Return (%)": coc_return, "Annual Net ($)": net_cashflow,
            "lat": l['lat'], "lon": l['lon']
        })

if results:
    df_results = pd.DataFrame(results)
    st.divider()
    st.subheader("🗺️ Geographic Portfolio Distribution")
    st.map(df_results) # Plots pins using 'lat' and 'lon'

    st.subheader("📊 Comparative Ranking")
    sort_by = st.radio("Primary Metric:", ["Best CoC Return", "Best Cap Rate", "Highest Cashflow"], horizontal=True)
    
    sort_map = {"Best CoC Return": "CoC Return (%)", "Best Cap Rate": "Cap Rate (%)", "Highest Cashflow": "Annual Net ($)"}
    df_ranked = df_results.sort_values(by=sort_map[sort_by], ascending=False)
    
    st.dataframe(
        df_ranked.drop(columns=['lat', 'lon', 'Down Payment', 'Gross Income', 'Op Expenses', 'Mtg Payment (Annual)']), 
        use_container_width=True, hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn(format="$%d"),
            "Annual Net ($)": st.column_config.NumberColumn(format="$%d"),
            "Cap Rate (%)": st.column_config.NumberColumn(format="%.2f%%"),
            "CoC Return (%)": st.column_config.ProgressColumn(min_value=0, max_value=15, format="%.2f%%")
        }
    )

    # --- NEW: DETAILED FINANCIAL ROW BELOW ---
    st.subheader("💰 Deep Underwriting (Top Pick)")
    top_pick = df_ranked.iloc[0]
    
    st.markdown(f"**Selected Listing:** {top_pick['Address']}")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Down Payment Req", f"${top_pick['Down Payment']:,.0f}")
    r2.metric("Gross Income", f"${top_pick['Gross Income']:,.0f}")
    r3.metric("Operating Expenses", f"${top_pick['Op Expenses']:,.0f}")
    r4.metric("Mtg Payment (Annual)", f"${top_pick['Mtg Payment (Annual)']:,.0f}")

else:
    st.info("💡 Add listing details above to activate the map and performance analysis.")

show_disclaimer()
