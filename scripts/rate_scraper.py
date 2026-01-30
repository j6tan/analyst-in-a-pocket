import requests
import json
import os
from datetime import datetime

def fetch_boc_observation(series_id):
    """Fetches the most recent observation from the BoC Valet API with robust error handling."""
    try:
        url = f"https://www.bankofcanada.ca/valet/observations/{series_id}/json?recent=1"
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        if 'observations' in data and len(data['observations']) > 0:
            val = data['observations'][0].get(series_id, {}).get('v')
            return float(val) if val else None
        return None
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch {series_id}. Error: {e}")
        return None

def fetch_provincial_yields():
    return {
        "Ontario": 4.5, "BC": 3.8, "Alberta": 6.8, "Quebec": 5.2,
        "Manitoba": 7.0, "Saskatchewan": 7.4, "Nova Scotia": 5.5,
        "NB": 6.5, "PEI": 6.1, "NL": 6.2
    }

def update_market_intel():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    file_path = os.path.join(data_dir, "market_intel.json")
    history_path = os.path.join(data_dir, "market_history.json")

    print("📡 Connecting to Market Data Sources...")
    
    prime = fetch_boc_observation("V121758") or 5.95
    overnight = fetch_boc_observation("V39079") or 3.75
    fixed_5 = fetch_boc_observation("V122667786") or 4.49
    
    yields = fetch_provincial_yields()
    current_time = datetime.now()

    # --- 1. PREPARE CURRENT INTEL WITH DYNAMIC TAX RULES ---
    intel_data = {
        "last_updated": current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "rates": {
            "boc_overnight": overnight,
            "bank_prime": prime,
            "five_year_fixed_uninsured": fixed_5
        },
        "provincial_yields": yields,
        "tax_rules": {
            "Ontario": [
                {"threshold": 55000, "rate": 0.005},
                {"threshold": 250000, "rate": 0.01},
                {"threshold": 400000, "rate": 0.015},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 999999999, "rate": 0.025} # Catch-all high threshold
            ],
            "Toronto_Municipal": [
                {"threshold": 55000, "rate": 0.005},
                {"threshold": 250000, "rate": 0.01},
                {"threshold": 400000, "rate": 0.015},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 3000000, "rate": 0.025},
                {"threshold": 999999999, "rate": 0.03} # Toronto has higher luxury brackets
            ],
            "BC": [
                {"threshold": 200000, "rate": 0.01},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 3000000, "rate": 0.03},
                {"threshold": 999999999, "rate": 0.05} # BC Additional Tax on $3M+
            ],
            "rebates": {
                "ON_FTHB_Max": 4000,
                "Toronto_FTHB_Max": 4475,
                "BC_FTHB_Threshold": 500000, # Full exemption limit
                "BC_FTHB_Partial_Limit": 525000 # Partial exemption limit
            }
        }
    }

    # --- 2. PREPARE HISTORICAL ENTRY ---
    new_history_entry = {
        "date": current_time.strftime("%Y-%m-%d"),
        "prime": prime,
        "overnight": overnight,
        "fixed_5": fixed_5
    }

    # --- 3. UPDATE HISTORY FILE ---
    history = []
    if os.path.exists(history_path):
        try:
            with open(history_path, "r") as f:
                history = json.load(f)
        except Exception:
            history = []

    if not history or history[-1].get("date") != new_history_entry["date"]:
        history.append(new_history_entry)
        if len(history) > 24:
            history = history[-24:]

    # --- 4. SAVE FILES ---
    with open(file_path, "w") as f:
        json.dump(intel_data, f, indent=4)
        
    with open(history_path, "w") as f:
        json.dump(history, f, indent=4)
    
    print(f"✅ Market Intel & Tax Brackets Saved: {file_path}")
    print(f"📈 History Updated: {history_path}")

if __name__ == "__main__":
    update_market_intel()
