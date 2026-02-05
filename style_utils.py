import streamlit as st

def inject_global_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Inter', sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }

        /* 1. DYNAMIC CONTAINER PADDING */
        .block-container {
            padding-top: clamp(2rem, 5vh, 5rem) !important;
            padding-bottom: 5rem !important;
            padding-left: clamp(1rem, 5vw, 8rem) !important;
            padding-right: clamp(1rem, 5vw, 8rem) !important;
            max-width: 1400px !important;
        }

        /* 2. DYNAMIC EDITORIAL TITLES */
        /* clamp(min, preferred, max) ensures it never gets too small or too huge */
        h1 {
            font-weight: 800 !important;
            letter-spacing: -0.045em !important;
            line-height: 1.05 !important;
            font-size: clamp(2rem, 4.5vw, 3.8rem) !important; 
            color: #000000 !important;
            margin-bottom: 1rem !important;
        }

        h2 {
            font-size: clamp(1.5rem, 2.5vw, 2.2rem) !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }

        /* 3. DARK GREY PILL BUTTONS (Dynamic Width) */
        div.stButton > button {
            background-color: #222222 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 50px !important;
            padding: 0.7rem clamp(1.5rem, 3vw, 3rem) !important;
            font-weight: 600 !important;
            font-size: clamp(0.85rem, 1vw, 1rem) !important;
            transition: all 0.2s ease-in-out !important;
            width: auto; /* Buttons grow with text but stay as pills */
        }

        div.stButton > button:hover {
            background-color: #000000 !important;
            transform: translateY(-1px);
        }

        /* 4. RESPONSIVE CARDS */
        [data-testid="stVerticalBlock"] > div[style*="border: 1px solid"] {
            border-radius: 20px !important;
            padding: clamp(1.5rem, 3vw, 2.5rem) !important;
            background-color: #ffffff !important;
            border: 1px solid #f0f0f0 !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.03) !important;
        }

        /* 5. METRICS AUTO-SCALE */
        [data-testid="stMetricValue"] {
            font-weight: 800 !important;
            font-size: clamp(1.5rem, 3vw, 2.5rem) !important;
            letter-spacing: -0.03em !important;
        }
        
        /* 6. HIDE CLUTTER */
        header, footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)
