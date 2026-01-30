import requests
import json
import os
from datetime import datetime

def fetch_boc_observation(series_id):
    """Fetches the most recent observation from the BoC Valet API with robust error handling."""
    try:
        url = f"https://www.bankofcanada.ca/valet/observations/{series_id}/json?recent=1"
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code != 200: return None
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

    # --- 1. PREPARE CURRENT INTEL WITH DYNAMIC TAX RULES & WIDE CITY RANGE ---
    intel_data = {
        "last_updated": current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "rates": {
            "boc_overnight": overnight,
            "bank_prime": prime,
            "five_year_fixed_uninsured": fixed_5
        },
        "provincial_yields": yields,
        "city_tax_data": {
            "Ontario": {
                "Toronto": 0.00754, "Ottawa": 0.01227, "Mississauga": 0.00860, "Brampton": 0.01015,
                "Hamilton": 0.01497, "London": 0.01573, "Markham": 0.00650, "Vaughan": 0.00695,
                "Kitchener": 0.01356, "Windsor": 0.01850, "Oakville": 0.00760, "Burlington": 0.00860,
                "Oshawa": 0.01376, "Barrie": 0.01291, "Guelph": 0.01229, "Kingston": 0.01445,
                "Thunder Bay": 0.01709, "Sudbury": 0.01650, "Outside Toronto": 0.0075
            },
            "BC": {
                "Vancouver": 0.00311, "Surrey": 0.00340, "Burnaby": 0.00480, "Richmond": 0.00320,
                "Coquitlam": 0.00380, "Langley": 0.00390, "Kelowna": 0.00444, "Victoria": 0.00520,
                "Abbotsford": 0.00412, "Nanaimo": 0.00720, "Kamloops": 0.00680, "Prince George": 0.00890,
                "West Vancouver": 0.00243, "Other BC": 0.0040
            },
            "Alberta": {
                "Calgary": 0.00618, "Edmonton": 0.00816, "Red Deer": 0.00940, "Lethbridge": 0.01059,
                "St. Albert": 0.01020, "Medicine Hat": 0.01120, "Other Alberta": 0.0065
            },
            "Quebec": {
                "Montreal": 0.00767, "Quebec City": 0.00880, "Laval": 0.00910, "Gatineau": 0.01050,
                "Longueuil": 0.01020, "Sherbrooke": 0.01180, "Other Quebec": 0.0085
            },
            "Manitoba": {
                "Winnipeg": 0.01242, "Brandon": 0.02100, "Steinbach": 0.01150, "Other Manitoba": 0.0120
            },
            "Saskatchewan": {
                "Saskatoon": 0.01339, "Regina": 0.01364, "Moose Jaw": 0.01420, "Other Saskatchewan": 0.0135
            },
            "Atlantic": {
                "Halifax": 0.01110, "Moncton": 0.01600, "Saint John": 0.01790, "Fredericton": 0.01550,
                "St. John's": 0.00910, "Charlottetown": 0.01670, "Other Atlantic": 0.0120
            }
        },
        "tax_rules": {
            "Ontario": [
                {"threshold": 55000, "rate": 0.005},
                {"threshold": 250000, "rate": 0.01},
                {"threshold": 400000, "rate": 0.015},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 999999999, "rate": 0.025}
            ],
            "Toronto_Municipal": [
                {"threshold": 55000, "rate": 0.005},
                {"threshold": 250000, "rate": 0.01},
                {"threshold": 400000, "rate": 0.015},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 3000000, "rate": 0.025},
                {"threshold": 999999999, "rate": 0.03}
            ],
            "BC": [
                {"threshold": 200000, "rate": 0.01},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 3000000, "rate": 0.03},
                {"threshold": 999999999, "rate": 0.05}
            ],
            "rebates": {
                "ON_FTHB_Max": 4000,
                "Toronto_FTHB_Max": 4475,
                "BC_FTHB_Threshold": 500000,
                "BC_FTHB_Partial_Limit": 525000
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
    
    print(f"✅ Market Intel, Tax Brackets & Wide-Range City Rates Saved: {file_path}")
    print(f"📈 History Updated: {history_path}")

if __name__ == "__main__":
    update_market_intel()
