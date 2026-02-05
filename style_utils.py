import streamlit as st

def inject_global_css():
    st.markdown("""
        <style>
        /* 1. WEALTHSIMPLE TYPEFACE */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Inter', sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }

        /* 2. LAYOUT */
        .block-container {
            padding-top: clamp(3rem, 7vh, 5rem) !important;
            padding-bottom: 5rem !important;
            max-width: 1400px !important;
        }

        /* 3. HEADERS */
        h1 { font-weight: 800 !important; letter-spacing: -0.04em !important; font-size: 3rem !important; }
        h2, h3 { font-weight: 700 !important; }

        /* 4. BUTTONS (Charcoal) */
        div.stButton > button {
            background-color: #4D4D4D !important;
            color: white !important;
            border-radius: 50px !important;
            padding: 0.6rem 2rem !important;
            border: none !important;
        }
        div.stButton > button:hover { background-color: #333 !important; }
        
        /* Secondary Buttons */
        div.stButton > button[kind="secondary"] {
            background-color: #EDEDED !important;
            color: #444 !important;
        }

        /* 5. CARDS & METRICS */
        [data-testid="stVerticalBlock"] > div[style*="border: 1px solid"] {
            border-radius: 20px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.03) !important;
        }
        [data-testid="stMetricValue"] { font-weight: 800 !important; }

        /* --- 6. THE SIDEBAR FIX (NUCLEAR EDITION) --- */
        
        /* Force the container to make space */
        [data-testid="stSidebarNavItems"] {
            padding-top: 10px !important;
        }

        /* Target EVERY text element inside the Nav Items container */
        /* This catches spans, divs, smalls, strongs - anything with text */
        [data-testid="stSidebarNavItems"] * {
            color: #4D4D4D !important; /* Force Dark Grey */
            visibility: visible !important;
            opacity: 1 !important;
            display: block !important;
        }

        /* Fix the actual links so they don't look broken (overridden by above) */
        [data-testid="stSidebarNavItems"] a {
            display: flex !important; /* Keep links flexible */
            align-items: center !important;
            font-weight: 500 !important;
            margin-bottom: 5px !important;
        }

        /* Target the Header specifically if possible to make it bold */
        /* We guess it is the element WITHOUT an href link */
        [data-testid="stSidebarNavItems"] div:not(:has(a)) {
            font-weight: 800 !important;
            text-transform: uppercase !important;
            font-size: 0.75rem !important;
            letter-spacing: 0.1em !important;
            margin-top: 20px !important;
            margin-bottom: 5px !important;
        }

        /* HIDE CLUTTER */
        header, footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)
