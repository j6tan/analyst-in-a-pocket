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

        /* 3. MAIN PAGE HEADERS */
        h1 { font-weight: 800 !important; letter-spacing: -0.04em !important; font-size: 3rem !important; }
        h2, h3 { font-weight: 700 !important; }

        /* 4. BUTTONS */
        div.stButton > button {
            background-color: #4D4D4D !important;
            color: white !important;
            border-radius: 50px !important;
            padding: 0.6rem 2rem !important;
            border: none !important;
        }
        div.stButton > button:hover { background-color: #333 !important; }
        div.stButton > button[kind="secondary"] {
            background-color: #EDEDED !important;
            color: #444 !important;
        }

        /* 5. CARDS */
        [data-testid="stVerticalBlock"] > div[style*="border: 1px solid"] {
            border-radius: 20px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.03) !important;
        }

        /* --- 6. SIDEBAR REFINEMENT (The Fix) --- */

        /* A. The Container Spacing */
        [data-testid="stSidebarNavItems"] {
            padding-top: 1rem !important;
        }

        /* B. GROUP HEADERS (The Labels) */
        /* We force these to be Light Grey, All Caps, and Small */
        div[data-testid="stSidebarNavItems"] > div > div > span,
        div[data-testid="stSidebarNavItems"] > div > small {
            visibility: visible !important;
            display: block !important;
            color: #999999 !important; /* Light Grey to push them to background */
            font-size: 0.75rem !important; /* Smaller than tools */
            font-weight: 700 !important;
            text-transform: uppercase !important; /* Force capitalization */
            letter-spacing: 0.1em !important;
            margin-top: 2rem !important;
            margin-bottom: 0.5rem !important;
        }

        /* C. THE TOOLS (The Links) */
        /* We force these to be Dark Charcoal and Normal Case */
        [data-testid="stSidebarNavItems"] ul li a {
            color: #4D4D4D !important; /* Dark Grey */
            font-size: 0.95rem !important;
            font-weight: 500 !important;
            text-transform: none !important; /* Ensure they don't get capitalized */
        }
        
        /* Active/Selected Tool */
        [data-testid="stSidebarNavItems"] ul li a[aria-current="page"] {
            background-color: #EDEDED !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }

        /* HIDE CLUTTER */
        header, footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)
