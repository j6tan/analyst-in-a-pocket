import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk 
import requests 
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, init_session_state, load_user_data
import os
import base64

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

# --- 2. BRANDING COLORS ---
PRIMARY_GOLD_RGBA = [206, 179, 111, 255] 
CHARCOAL_RGBA = [46, 43, 40, 255]       
DARK_RED = "#8B0000"
SUCCESS_GREEN = "#28a745"

PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"

# --- INLINE LOGO & TITLE ---
def get_inline_logo(img_name="logo.png", width=75):
    # Check root directory first, then fallback to looking one folder up
    img_path = img_name
    if not os.path.exists(img_path):
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), img_name)
        
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{encoded}" style="width: {width}px; flex-shrink: 0;">'
    return "<span style='font-size: 50px;'>🔥</span>"

logo_html = get_inline_logo(width=75)

st.markdown(f"""
    <div style='display: flex; align-items: center; justify-content: flex-start; gap: 15px; margin-top: -20px; margin-bottom: 25px;'>
        {logo_html}
        <h1 style='margin: 0 !important; padding: 0 !important; line-height: 1 !important;'>Pro Rental Portfolio Analyzer</h1>
    </div>
""", unsafe_allow_html=True)

# --- 3. DATABASE INITIALIZATION ---
if 'app_db' not in st.session_state:
    st.session_state.app_db = {}

if 'rental_analyzer' not in st.session_state.app_db:
    st.session_state.app_db['rental_analyzer'] = {
        'dp_val': 20.0,
        'm_rate': 5.1,
        'm_amort': 25.0,
        'mgmt_fee': 8.0,
        'dp_mode': "Percentage (%)",
        'use_mgmt': False,
        'listings': [] 
    }

if 'rental_listings' not in st.session_state:
    st.session_state.rental_listings = st.session_state.app_db['rental_analyzer'].get('listings', [])

def force_cloud_save():
    st.session_state['rental_analyzer_listings'] = st.session_state.rental_listings
    sync_widget("rental_analyzer:listings")

def sync_listing(index, field, key):
    st.session_state.rental_listings[index][field] = st.session_state[key]
    force_cloud_save()

# --- 4. PERSONALIZED STORYTELLING ---
prof = st.session_state.app_db.get('profile', {})
name1 = prof.get('p1_name') or "Primary Client"
name2 = prof.get('p2_name') or ""
household = f"{name1} and {name2}" if name2 else name1

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">🏗️ Strategic Brief: Building Your Real Estate Empire</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Welcome to the underwriting lab, <b>{household}</b>. This tool is designed to cut through the noise of the real estate market. 
        By mapping prospective properties alongside key rental drivers like SkyTrains and grocery stores, we can instantly visualize which assets command the highest tenant demand. 
        Adjust your global financing below, and the engine will automatically rank your prospective listings by <b>Cash-on-Cash Return</b>, stripping away emotion to highlight the absolute best mathematical fit for your portfolio.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. GLOBAL SETTINGS ---
with st.container(border=True):
    st.subheader("⚙️ Global Settings")
    g_col1, g_col2, g_col3, g_col4 = st.columns(4)
    with g_col1:
        curr_dp_mode = st.session_state.app_db['rental_analyzer'].get('dp_mode', "Percentage (%)")
        st.radio("DP Mode", ["Percentage (%)", "Fixed Amount ($)"], horizontal=True, 
                 key="rental_analyzer_dp_mode", index=0 if "Percent" in curr_dp_mode else 1,
                 on_change=sync_widget, args=('rental_analyzer:dp_mode',))
    with g_col2:
        lbl = f"Down Payment ({'%' if 'Percent' in curr_dp_mode else '$'})"
        cloud_input(lbl, "rental_analyzer", "dp_val", step=1.0)
    with g_col3:
        cloud_input("Interest Rate (%)", "rental_analyzer", "m_rate", step=0.1)
    with g_col4:
        cloud_input("Amortization (Yrs)", "rental_analyzer", "m_amort", step=1.0)
    
    st.divider() 
    g_col5, g_col6, g_col7 = st.columns([1.5, 1.5, 2])
    with g_col5:
        curr_mgmt = st.session_state.app_db['rental_analyzer'].get('use_mgmt', False)
        st.checkbox("Use Property Manager?", value=curr_mgmt, 
                    key="rental_analyzer_use_mgmt", on_change=sync_widget, args=('rental_analyzer:use_mgmt',))
    with g_col6:
        if curr_mgmt:
            cloud_input("Management Fee (%)", "rental_analyzer", "mgmt_fee", step=0.5)

# --- 6. LISTING MANAGEMENT UI ---
def geocode_address(index):
    if not geolocator: return
    addr = st.session_state.rental_listings[index]['address']
    if addr:
        try:
            location = geolocator.geocode(addr, addressdetails=True)
            if location:
                st.session_state.rental_listings[index]['lat'] = location.latitude
                st.session_state.rental_listings[index]['lon'] = location.longitude
                raw_addr = location.raw.get('address', {})
                h_num = raw_addr.get('house_number', '')
                road = raw_addr.get('road', '')
                city = raw_addr.get('city', raw_addr.get('town', raw_addr.get('suburb', raw_addr.get('municipality', ''))))
                
                clean_addr = f"{h_num} {road}, {city}".strip() if road and city else ", ".join(location.address.split(",")[:2])
                st.session_state.rental_listings[index]['address'] = clean_addr
                force_cloud_save() 
                st.toast(f"📍 Mapped & Saved: {clean_addr}")
        except Exception as e:
            st.warning(f"Map Service Error: {e}")

st.subheader("🏠 Property Underwriting")

if len(st.session_state.rental_listings) == 0:
    st.info("No properties in your portfolio yet. Click below to start underwriting.")

for i, listing in enumerate(st.session_state.rental_listings):
    with st.expander(f"Listing #{i+1}: {listing['address'][:30]}...", expanded=(i==len(st.session_state.rental_listings)-1)):
        r1_c1, r1_c2, r1_c3 = st.columns([1.6, 1, 1])
        with r1_c1: st.text_input("Address", value=listing['address'], key=f"addr_{i}", label_visibility="collapsed", on_change=sync_listing, args=(i, 'address', f"addr_{i}"))
        with r1_c2: st.button("📍 Add to Map", key=f"geo_{i}", on_click=geocode_address, args=(i,), use_container_width=True)
        with r1_c3: 
            if st.button("🗑️ Remove", key=f"del_{i}", use_container_width=True):
                st.session_state.rental_listings.pop(i)
                force_cloud_save()
                st.rerun()

        r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns([2.6, 0.6, 0.6, 1, 1])
        with r2_c1: st.number_input("Listing Price ($)", value=listing['price'], key=f"pr_{i}", on_change=sync_listing, args=(i, 'price', f"pr_{i}"))
        with r2_c2: st.number_input("Beds", value=listing.get('beds', 1), key=f"bd_{i}", on_change=sync_listing, args=(i, 'beds', f"bd_{i}"))
        with r2_c3: st.number_input("Baths", value=listing.get('baths', 1), key=f"ba_{i}", on_change=sync_listing, args=(i, 'baths', f"ba_{i}"))
        with r2_c4: st.number_input("Sqft", value=listing.get('sqft', 0), key=f"sq_{i}", on_change=sync_listing, args=(i, 'sqft', f"sq_{i}"))
        with r2_c5: st.number_input("Year Built", value=listing.get('year', 2000), key=f"yr_{i}", on_change=sync_listing, args=(i, 'year', f"yr_{i}"))

        r3_c1, r3_c2, r3_c3, r3_c4 = st.columns(4)
        with r3_c1: st.number_input("Monthly Rent ($)", value=listing['rent'], key=f"rt_{i}", on_change=sync_listing, args=(i, 'rent', f"rt_{i}"))
        with r3_c2: st.number_input("Property Tax ($)", value=listing['tax'], key=f"tx_{i}", on_change=sync_listing, args=(i, 'tax', f"tx_{i}"))
        with r3_c3: st.number_input("Strata Fees ($)", value=listing['strata'], key=f"st_{i}", on_change=sync_listing, args=(i, 'strata', f"st_{i}"))
        with r3_c4: st.number_input("Monthly Insurance ($)", value=listing.get('ins', 100), key=f"in_{i}", on_change=sync_listing, args=(i, 'ins', f"in_{i}"))

if len(st.session_state.rental_listings) < 10:
    if st.button("➕ Add New Listing"):
        st.session_state.rental_listings.append({
            "address": "", "lat": 0.0, "lon": 0.0, "price": 0, "tax": 0, "strata": 0, "rent": 0, 
            "beds": 1, "baths": 1, "sqft": 0, "year": 2000, "ins": 100
        })
        force_cloud_save()
        st.rerun()

# --- 7. CALCULATIONS ENGINE ---
full_analysis_list = []
gs = st.session_state.app_db['rental_analyzer']
calc_dp_mode, calc_dp_val, calc_m_rate, calc_m_amort = gs.get('dp_mode', 'Percentage (%)'), float(gs.get('dp_val', 20)), float(gs.get('m_rate', 5.1)), float(gs.get('m_amort', 25))
calc_mgmt_fee = float(gs.get('mgmt_fee', 8.0)) if gs.get('use_mgmt', False) else 0.0

for idx, l in enumerate(st.session_state.rental_listings):
    if l.get('lat') and l.get('lon'):
        noi, dp_amt, ann_mtg, net_cf, coc_ret, psf = 0, 0, 0, 0, 0, 0
        gross_inc = l['rent'] * 12
        mgmt_cost = (l['rent'] * 12 * (calc_mgmt_fee / 100))
        reserves = (l['rent'] * 12 * 0.05) 
        op_ex = l['tax'] + (l['strata'] * 12) + (l.get('ins', 100) * 12) + mgmt_cost + reserves
        
        if l['price'] > 0:
            noi = gross_inc - op_ex
            dp_amt = (l['price'] * (calc_dp_val / 100)) if "Percent" in calc_dp_mode else calc_dp_val
            loan = l['price'] - dp_amt
            r = (calc_m_rate / 100) / 12
            pmt = loan * (r * (1 + r)**(calc_m_amort*12)) / ((1 + r)**(calc_m_amort*12) - 1) if r > 0 else loan / (calc_m_amort*12)
            ann_mtg = pmt * 12
            net_cf = noi - ann_mtg
            coc_ret = (net_cf / dp_amt) * 100 if dp_amt > 0 else 0
            psf = l['price'] / l['sqft'] if l.get('sqft', 0) > 0 else 0

        full_analysis_list.append({
            "Address": l['address'], "Price": l['price'], "Area (sqft)": l.get('sqft', 0),
            "PSF": psf, "Gross Annual Rent": gross_inc, "Annual OpEx": op_ex,
            "Annual Mortg": ann_mtg, "Annual Net Cash Flow": net_cf,
            "Cap Rate %": (noi / l['price']) * 100 if l['price']>0 else 0,
            "CoC %": coc_ret, "DP_RAW": dp_amt, "lat": l['lat'], "lon": l['lon']
        })

# --- 8. FAST POI FETCHER (SKYTRAIN FIX) ---
@st.cache_data(ttl=86400, show_spinner=False) 
def pull_osm_data(lat, lon, radius, poi_type):
    headers = {"User-Agent": "AnalystInAPocket/1.0"}
    
    # THE FIX: SkyTrains are often relations/ways, Groceries are usually nodes.
    if poi_type == "SkyTrain":
        query = f"""
        [out:json][timeout:15];
        (
          nwr["railway"="station"](around:{radius},{lat},{lon});
          nwr["station"="subway"](around:{radius},{lat},{lon});
        );
        out center;
        """
    elif poi_type == "Grocery":
        query = f"""
        [out:json][timeout:10];
        nwr["shop"="supermarket"](around:{radius},{lat},{lon});
        out center;
        """
    else: return pd.DataFrame()

    try:
        response = requests.get("https://overpass-api.de/api/interpreter", params={'data': query}, headers=headers, timeout=10)
        data = response.json()
        pois = []
        for el in data.get('elements', []):
            p_lat = el.get('lat', el.get('center', {}).get('lat'))
            p_lon = el.get('lon', el.get('center', {}).get('lon'))
            if p_lat and p_lon:
                name = el.get('tags', {}).get('name', poi_type)
                pois.append({'lat': p_lat, 'lon': p_lon, 'HoverText': f"{poi_type}: {name}", 'icon': "T" if poi_type == "SkyTrain" else "G"})
        return pd.DataFrame(pois)
    except:
        return pd.DataFrame()

# --- 9. VISUALS & RANKING ---
if full_analysis_list:
    df_results = pd.DataFrame(full_analysis_list)
    df_ranked = df_results[df_results['Price'] > 0].sort_values(by="CoC %", ascending=False).reset_index(drop=True)
    
    st.divider()
    st.subheader("🗺️ Geographic Portfolio Distribution")
    
    layer_col1, layer_col2, layer_col3 = st.columns([1.5, 1.5, 3])
    with layer_col1: show_skytrain = st.checkbox("🚇 SkyTrain Stations")
    with layer_col2: show_grocery = st.checkbox("🛒 Grocery Stores")
    with layer_col3:
        st.markdown(f'<div style="display: flex; gap: 10px; font-size: 0.8em; justify-content: flex-end; margin-top: 5px;"><span style="color: #CEB36F;">●</span> Top Pick <span style="color: #2E2B28;">●</span> Others</div>', unsafe_allow_html=True)

    df_results['Rank'] = df_results['Address'].map(lambda x: df_ranked[df_ranked['Address'] == x].index[0] + 1 if x in df_ranked['Address'].values else 99)
    df_results['Rank_str'] = df_results['Rank'].apply(lambda x: str(x) if x != 99 else "-")
    df_results['HoverText'] = df_results.apply(lambda row: f"Rank #{row['Rank_str']}: {row['Address']} (${row['Price']:,.0f})", axis=1)

    df_best = df_results[df_results['Rank'] == 1].copy()
    df_others = df_results[df_results['Rank'] > 1].copy()

    center_lat, center_lon = df_results['lat'].mean(), df_results['lon'].mean()
    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=13)
    
    map_layers = []

    def add_bulletproof_badge(df, radius, color_rgb):
        if not df.empty:
            df['color_col'] = [color_rgb] * len(df)
            map_layers.append(pdk.Layer("ScatterplotLayer", df, get_position='[lon, lat]', get_fill_color='color_col', get_radius=radius, pickable=True))
            map_layers.append(pdk.Layer("TextLayer", df, get_position='[lon, lat]', get_text='icon', get_size=20, get_color=[255, 255, 255, 255], get_alignment_baseline="'center'", get_text_anchor="'middle'", pickable=False))

    if show_skytrain:
        df_train = pull_osm_data(center_lat, center_lon, 5000, "SkyTrain")
        add_bulletproof_badge(df_train, 150, [0, 102, 204, 255]) 

    if show_grocery:
        df_groc = pull_osm_data(center_lat, center_lon, 2000, "Grocery")
        add_bulletproof_badge(df_groc, 100, [40, 167, 69, 255]) 

    if not df_best.empty:
        map_layers.append(pdk.Layer("ScatterplotLayer", df_best, get_position='[lon, lat]', get_fill_color=[206, 179, 111, 255], get_radius=220, pickable=True))
        map_layers.append(pdk.Layer("TextLayer", df_best, get_position='[lon, lat]', get_text="Rank_str", get_size=20, get_color=[255, 255, 255, 255], get_alignment_baseline="'center'", get_text_anchor="'middle'", pickable=False))

    if not df_others.empty:
        map_layers.append(pdk.Layer("ScatterplotLayer", df_others, get_position='[lon, lat]', get_fill_color=[46, 43, 40, 255], get_radius=180, pickable=True))
        map_layers.append(pdk.Layer("TextLayer", df_others, get_position='[lon, lat]', get_text="Rank_str", get_size=16, get_color=[255, 255, 255, 255], get_alignment_baseline="'center'", get_text_anchor="'middle'", pickable=False))

    st.pydeck_chart(pdk.Deck(
        map_style=None, initial_view_state=view_state, 
        layers=map_layers,
        tooltip={"text": "{HoverText}"} 
    ))

    # --- 10. RANKING TABLE ---
    if not df_ranked.empty:
        st.subheader("📊 Comparative Ranking")
        display_df = df_ranked.drop(columns=['lat', 'lon', 'DP_RAW', 'Rank', 'Rank_str', 'HoverText'], errors='ignore')
        
        st.dataframe(
            display_df, use_container_width=True, hide_index=True,
            column_config={
                "Price": st.column_config.NumberColumn(format="$%d"),
                "Area (sqft)": st.column_config.NumberColumn(format="%d"),
                "PSF": st.column_config.NumberColumn(format="$%d"),
                "Gross Annual Rent": st.column_config.NumberColumn(format="$%d"),
                "Annual OpEx": st.column_config.NumberColumn(format="$%d"),
                "Annual Mortg": st.column_config.NumberColumn(format="$%d"),
                "Annual Net Cash Flow": st.column_config.NumberColumn(format="$%d"),
                "Cap Rate %": st.column_config.NumberColumn(format="%.2f%%"),
                "CoC %": st.column_config.NumberColumn(format="%.2f%%")
            }
        )

        st.subheader("💰 Deep Underwriting (Top Selection)")
        top = df_ranked.iloc[0]
        st.markdown(f"**Selected Listing:** {top['Address']}")

        def styled_metric(label, value, color, is_outflow=True):
            prefix = "-" if is_outflow else ""
            st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #eee;">
                <p style="margin:0; font-size: 0.85rem; color: #6c757d;">{label}</p>
                <p style="margin:0; font-size: 1.5rem; font-weight: bold; color: {color};">{prefix}${value:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        with m1: styled_metric("Down Payment Req", top['DP_RAW'], DARK_RED)
        with m2: styled_metric("Gross Annual Income", top['Gross Annual Rent'], SUCCESS_GREEN, is_outflow=False)
        with m3: styled_metric("Annual Operating Ex", top['Annual OpEx'], DARK_RED)
        with m4: styled_metric("Annual Mortgage", top['Annual Mortg'], DARK_RED)

show_disclaimer()

# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; color: #adb5bd; font-size: 0.85em; margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        &copy; 2026 FIRE Calculator. All rights reserved. <br>
        <span style="font-size: 0.9em; font-style: italic;">Empowering Canadian professionals to build wealth.</span>
    </div>
""", unsafe_allow_html=True)
