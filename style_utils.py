import streamlit as st

def inject_global_css():
    st.markdown("""
        <style>
        /* 1. WEALTHSIMPLE TYPEFACE (Inter) */
        @import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap');
        
        html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, span {
            font-family: 'Inter', sans-serif !important;
            color: #1a1a1a !important;
            -webkit-font-smoothing: antialiased;
        }

        /* 2. UNIVERSAL DE-SQUISHING & PADDING */
        .block-container {
            padding-top: 4rem !important; 
            padding-bottom: 5rem !important;
            padding-left: 6% !important;
            padding-right: 6% !important;
            max-width: 1300px !important;
        }

        /* 3. EDITORIAL HEADERS (Bold & Tight) */
        h1 {
            font-weight: 800 !important;
            letter-spacing: -0.045em !important; /* The tighter the better for this look */
            line-height: 1.05 !important;
            font-size: 3.5rem !important;
            color: #000000 !important;
            margin-bottom: 1.5rem !important;
        }

        h2, h3 {
            font-weight: 700 !important;
            letter-spacing: -0.025em !important;
            color: #1a1a1a !important;
        }

        /* 4. DARK GREY PILL BUTTONS */
        div.stButton > button {
            background-color: #222222 !important; /* Dark Grey / Ink */
            color: #ffffff !important;
            border: none !important;
            border-radius: 50px !important; /* Rounded Pill */
            padding: 0.7rem 2.2rem !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            letter-spacing: -0.01em !important;
            transition: all 0.2s ease-in-out !important;
        }

        div.stButton > button:hover {
            background-color: #000000 !important; /* Pure black on hover */
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        /* 5. SECONDARY BUTTONS (For 'Back' or 'Cancel') */
        div.stButton > button[kind="secondary"] {
            background-color: #f2f2f2 !important;
            color: #1a1a1a !important;
        }

        /* 6. CLEAN CARDS (The Paper Look) */
        [data-testid="stVerticalBlock"] > div[style*="border: 1px solid"] {
            background-color: #ffffff !important;
            border: 1px solid #f0f0f0 !important;
            border-radius: 20px !important;
            padding: 2.5rem !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.03) !important;
        }

        /* 7. METRIC STYLING */
        [data-testid="stMetricValue"] {
            font-weight: 800 !important;
            letter-spacing: -0.03em !important;
            font-size: 2.2rem !important;
        }
        
        /* Hide default Streamlit clutter */
        header {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)
