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

        /* --- 6. THE "UNBREAKABLE" SIDEBAR FIX --- */
        
        /* A. Container Spacing */
        [data-testid="stSidebarNavItems"] {
            padding-top: 1rem !important;
        }

        /* B. THE GROUP TITLES (Targeting Structure, Not Tags) */
        /* We select the FIRST child element of every group container. */
        /* It doesn't matter if Streamlit makes it a div, span, strong, or p. */
        [data-testid="stSidebarNavItems"] > div > :first-child {
            visibility: visible !important;
            display: block !important;
            color: #999999 !important;      /* Light Grey Label */
            font-size: 0.75rem !important;  /* Small */
            font-weight: 700 !important;    /* Bold */
            text-transform: uppercase !important; /* All Caps */
            letter-spacing: 0.1em !important;
            margin-top: 1.5rem !important;
            margin-bottom: 0.5rem !important;
            background-color: transparent !important;
        }

        /* C. THE TOOLS (The Links) */
        /* We target the 'a' tag (Anchor). This is standard HTML and will never change. */
        [data-testid="stSidebarNavItems"] a {
            color: #4D4D4D !important;      /* Dark Charcoal */
            font-size: 0.95rem !important;  /* Normal Size */
            font-weight: 500 !important;    /* Normal Weight */
            text-transform: none !important; /* Normal Case */
        }
        
        /* Active Tool Highlight */
        [data-testid="stSidebarNavItems"] a[aria-current="page"] {
            background-color: #EDEDED !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }

        /* HIDE CLUTTER */
        header, footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)
