import streamlit as st

def inject_global_css():
    st.markdown("""
        <style>
        /* 1. WEALTHSIMPLE TYPEFACE (Inter) */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, span {
            font-family: 'Inter', sans-serif !important;
            color: #1a1a1a !important;
            -webkit-font-smoothing: antialiased;
        }

        /* 2. DYNAMIC LAYOUT (Expansive & Responsive) */
        .block-container {
            padding-top: clamp(2.5rem, 6vh, 6rem) !important;
            padding-bottom: 5rem !important;
            padding-left: clamp(1rem, 7vw, 12rem) !important;
            padding-right: clamp(1rem, 7vw, 12rem) !important;
            max-width: 1450px !important;
        }

        /* 3. DYNAMIC EDITORIAL TITLES (800 Weight) */
        h1 {
            font-weight: 800 !important;
            letter-spacing: -0.05em !important; /* Extra tight for editorial feel */
            line-height: 1.05 !important;
            font-size: clamp(2.4rem, 5vw, 4rem) !important; 
            color: #000000 !important;
            margin-bottom: 1.5rem !important;
        }

        h2 {
            font-size: clamp(1.6rem, 3vw, 2.5rem) !important;
            font-weight: 700 !important;
            letter-spacing: -0.03em !important;
        }

        /* 4. DEEP CHARCOAL GREY BUTTONS (25% Darker) */
        div.stButton > button {
            background-color: #4D4D4D !important; /* Deep Charcoal Grey */
            color: #ffffff !important;
            border: none !important;
            border-radius: 50px !important; /* Pill Shape */
            padding: 0.75rem clamp(2rem, 4vw, 3.5rem) !important;
            font-weight: 600 !important;
            font-size: clamp(0.9rem, 1.1vw, 1.15rem) !important;
            letter-spacing: -0.01em !important;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
        }

        div.stButton > button:hover {
            background-color: #333333 !important; /* Darkens on hover */
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(0,0,0,0.15) !important;
        }

        /* 5. SECONDARY BUTTONS (Muted) */
        div.stButton > button[kind="secondary"] {
            background-color: #F2F2F2 !important;
            color: #4D4D4D !important;
        }

        /* 6. DYNAMIC CARDS (The Paper Look) */
        [data-testid="stVerticalBlock"] > div[style*="border: 1px solid"] {
            border-radius: 28px !important;
            padding: clamp(1.5rem, 5vw, 3.5rem) !important;
            background-color: #ffffff !important;
            border: 1px solid #EDEDED !important;
            box-shadow: 0 15px 45px rgba(0,0,0,0.03) !important;
        }

        /* 7. DYNAMIC METRICS */
        [data-testid="stMetricValue"] {
            font-weight: 800 !important;
            font-size: clamp(2rem, 4.5vw, 3.2rem) !important;
            letter-spacing: -0.05em !important;
        }
        
        /* Hide Default Clutter */
        header, footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)
