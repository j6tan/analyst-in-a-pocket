import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk 
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

# --- 2. BRANDING COLORS (RGBA for Pydeck) ---
PRIMARY_GOLD = [206, 179, 111, 255] # #CEB36F
CHARCOAL = [46, 43, 40, 255]       # #2E2B28
WHITE = [255, 255, 255, 255]

st.title("Pro Rental Portfolio Analyzer")

# --- 3. GLOBAL SETTINGS PANEL ---
with st.container(border=True):
    st.subheader("⚙️ Global Settings")
    g_col1, g_col2, g_col3, g_col4 = st.columns([1.5, 1.5, 1, 1])
    with g_col1:
        dp_mode = st.radio("Down Payment Mode", ["Percentage (%)", "Fixed Amount ($)"], horizontal=True)
    with g_col2:
        dp_global_val = st.number_input(f"Down Payment ({'%' if 'Percent' in dp_mode else '$'})", 
                                        value=20.0 if "Percent" in dp_mode else 100000.0)
    with g_col3:
        m_rate = st.number_input("Mortgage Interest Rate (%)", value=5.1, step=0.1)
    with g_col4:
        m_amort = st.number_input("Amortization (Years)", value=25, step=1)
    
    g_col5, g_col6 = st.columns([2, 1])
    with g_col5:
        use_mgmt = st.checkbox("Will you use a Property Manager?")
    with g_col6:
        mgmt_fee = st.number_input("Property Management Fee (%)", value=8.0, step=0.5) if use_mgmt else 0.0

# --- 4. LISTING MANAGEMENT ---
if 'rental_listings' not in st.session_state:
    st.session_state.rental_listings = [
        {"address": "3399 Noel Drive, Burnaby, BC", "lat": 49.2667, "lon": -122.9000, "price": 800000, "tax": 3000, "strata": 400, "rent": 3500, "beds": 2, "baths": 2, "year": 2010, "ins": 100, "sqft": 850},
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
                st.rerun()
        except: pass

st.subheader("🏠 Property Underwriting")

for i, listing in enumerate(st.session_state.rental_listings):
    with st.expander(f"Listing #{i+1}: {listing['address'][:30]}...", expanded=(i==len(st.session_state.rental_listings)-1)):
        r1_c1, r1_c2, r1_c3 = st.columns([1.6, 1, 1])
        with r1_c1: listing['address'] = st.text_input("Address", value=listing['address'], key=f"addr_{i}", label_visibility="collapsed")
        with r1_c2: st.button("📍 Add to Map", key=f"geo_{i}", on_click=geocode_address, args=(i,), use_container_width=True)
        with r1_c3: 
            if st.button("🗑️ Remove", key=f"del_{i}", use_container_width=True):
                st.session_state.rental_listings.pop(i); st.rerun()

        r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns([2.6, 0.6, 0.6, 1, 1])
        with r2_c1: listing['price'] = st.number_input("Listing Price ($)", value=listing['price'], key=f"pr_{i}")
        with r2_c2: listing['beds'] = st.number_input("Beds", value=listing.get('beds', 1), key=f"bd_{i}")
        with r2_c3: listing['baths'] = st.number_input("Baths", value=listing.get('baths', 1), key=f"ba_{i}")
        with r2_c4: listing['sqft'] = st.number_input("Sqft", value=listing.get('sqft', 0), key=f"sq_{i}")
        with r2_c5: listing['year'] = st.number_input("Year Built", value=listing.get('year', 2000), key=f"yr_{i}")

        r3_c1, r3_c2, r3_c3, r3_c4 = st.columns(4)
        with r3_c1: listing['rent'] = st.number_input("Monthly Rent ($)", value=listing['rent'], key=f"rt_{i}")
        with r3_c2: listing['tax'] = st.number_input("Property Tax ($)", value=listing['tax'], key=f"tx_{i}")
        with r3_c3: listing['strata'] = st.number_input("Strata Fees ($)", value=listing['strata'], key=f"st_{i}")
        with r3_c4: listing['ins'] = st.number_input("Monthly Insurance ($)", value=listing.get('ins', 100), key=f"in_{i}")

if len(st.session_state.rental_listings) < 10:
    st.button("➕ Add Another Listing", on_click=lambda: st.session_state.rental_listings.append({"address": "", "lat": 0.0, "lon": 0.0, "price": 0, "tax": 0, "strata": 0, "rent": 0}))

# --- 5. CALCULATIONS ENGINE ---
full_analysis_list = []
for idx, l in enumerate(st.session_state.rental_listings):
    if l.get('lat') and l.get('lon'):
        # Financial defaults if price is 0
        noi, dp_amt, ann_mtg, net_cf, coc_ret = 0, 0, 0, 0, 0
        if l['price'] > 0:
            mgmt_cost = (l['rent'] * 12 * (mgmt_fee / 100))
            reserves = (l['rent'] * 12 * 0.05) 
            gross_inc = l['rent'] * 12
            op_ex = l['tax'] + (l['strata'] * 12) + (l['ins'] * 12) + mgmt_cost + reserves
            noi = gross_inc - op_ex
            dp_amt = (l['price'] * (dp_global_val / 100)) if "Percent" in dp_mode else dp_global_val
            loan = l['price'] - dp_amt
            r = (m_rate / 100) / 12
            pmt = loan * (r * (1 + r)**(m_amort*12)) / ((1 + r)**(m_amort*12) - 1) if r > 0 else loan / (m_amort*12)
            ann_mtg = pmt * 12
            net_cf = noi - ann_mtg
            coc_ret = (net_cf / dp_amt) * 100 if dp_amt > 0 else 0

        full_analysis_list.append({
            "Address": l['address'], "Price": l['price'], "DP": dp_amt, 
            "Gross": l['rent']*12, "OpEx": l['tax']+(l['strata']*12)+(l['ins']*12)+mgmt_cost+reserves if l['price']>0 else 0, 
            "Mtg": ann_mtg, "Cap Rate %": (noi / l['price']) * 100 if l['price']>0 else 0, 
            "CoC %": coc_ret, "Net $": net_cf, "lat": l['lat'], "lon": l['lon']
        })

# --- 6. VISUALS, RANKING & LEGEND ---
if full_analysis_list:
    df_results = pd.DataFrame(full_analysis_list)
    df_ranked = df_results[df_results['Price'] > 0].sort_values(by="CoC %", ascending=False).reset_index(drop=True)
    
    # 1. Prepare Legend Data
    st.divider()
    l_col1, l_col2 = st.columns([3, 1])
    with l_col1:
        st.subheader("🗺️ Geographic Portfolio Distribution")
    with l_col2:
        # Visual Legend using HTML/CSS
        st.markdown(f"""
        <div style="display: flex; gap: 15px; font-size: 0.85em; margin-top: 10px; justify-content: flex-end;">
            <div style="display: flex; align-items: center; gap: 5px;">
                <span style="height: 12px; width: 12px; background-color: #CEB36F; border-radius: 50%; display: inline-block;"></span> Top Rank
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <span style="height: 12px; width: 12px; background-color: #2E2B28; border-radius: 50%; display: inline-block;"></span> Others
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 2. Advanced Mapping with Text Layer
    df_results['Rank'] = df_results['Address'].map(lambda x: df_ranked[df_ranked['Address'] == x].index[0] + 1 if x in df_ranked['Address'].values else "-")
    df_results['color'] = df_results['Rank'].map(lambda x: PRIMARY_GOLD if x == 1 else CHARCOAL)
    df_results['radius'] = df_results['Rank'].map(lambda x: 250 if x == 1 else 150)

    view_state = pdk.ViewState(latitude=df_results['lat'].mean(), longitude=df_results['lon'].mean(), zoom=10)
    
    # Scatter Layer for Color
    scatter_layer = pdk.Layer("ScatterplotLayer", df_results, get_position='[lon, lat]', get_color='color', get_radius='radius', pickable=True)
    
    # Text Layer for Numbers/Labels
    text_layer = pdk.Layer(
        "TextLayer",
        df_results,
        get_position='[lon, lat]',
        get_text="Rank",
        get_color=WHITE,
        get_size=16,
        get_alignment_baseline="'center'",
    )
    
    st.pydeck_chart(pdk.Deck(
        map_style=None, initial_view_state=view_state, 
        layers=[scatter_layer, text_layer],
        tooltip={"text": "{Address}\nPrice: ${Price}\nRank: #{Rank}"}
    ))

    # 3. Tables & Verdict
    if not df_ranked.empty:
        st.subheader("📊 Comparative Ranking")
        st.dataframe(df_ranked.drop(columns=['lat', 'lon', 'DP', 'Gross', 'OpEx', 'Mtg']), use_container_width=True, hide_index=True,
                     column_config={"Price": st.column_config.NumberColumn(format="$%d"), "Net $": st.column_config.NumberColumn(format="$%d"),
                                    "Cap Rate %": st.column_config.NumberColumn(format="%.2f%%"), "CoC %": st.column_config.ProgressColumn(min_value=0, max_value=15, format="%.2f%%")})

        top = df_ranked.iloc[0]
        st.success(f"🏆 **Top Choice (Ranked by CoC %):** {top['Address']}")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Down Payment Req", f"${top['DP']:,.0f}"); r2.metric("Gross Annual Income", f"${top['Gross']:,.0f}"); r3.metric("Annual Operating Ex", f"${top['OpEx']:,.0f}"); r4.metric("Annual Mortgage", f"${top['Mtg']:,.0f}")

show_disclaimer()
