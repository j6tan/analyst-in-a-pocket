import requests
import json
import os
from datetime import datetime

def fetch_boc_observation(series_id):
    """Fetches the most recent observation from the BoC Valet API with robust error handling."""
    try:
        # The BoC API is case-sensitive and sometimes requires specific headers
        url = f"https://www.bankofcanada.ca/valet/observations/{series_id}/json?recent=1"
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        # Verify the path exists in the JSON before accessing
        if 'observations' in data and len(data['observations']) > 0:
            val = data['observations'][0].get(series_id, {}).get('v')
            return float(val) if val else None
        return None
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch {series_id}. Error: {e}")
        return None

def fetch_provincial_yields():
    """
    Benchmarks for Provincial Cap Rates (Annual Rent / Purchase Price).
    In a professional tool, these are updated based on the latest quarterly 
    CMHC or Rentals.ca reports.
    """
    return {
        "Ontario": 4.5,
        "BC": 3.8, # Lower yields in BC due to higher property values
        "Alberta": 6.8, # Higher yields in Alberta
        "Quebec": 5.2,
        "Manitoba": 7.0,
        "Saskatchewan": 7.4,
        "Nova Scotia": 5.5,
        "NB": 6.5,
        "PEI": 6.1,
        "NL": 6.2
    }

def update_market_intel():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Ensure it points to your data folder correctly
    data_dir = os.path.join(script_dir, "..", "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    file_path = os.path.join(data_dir, "market_intel.json")

    print("📡 Connecting to Market Data Sources...")
    
    # Try fetching but provide smart defaults (current 2024/2025 levels)
    # V121758 = Prime | V39079 (Case sensitive) = Overnight | V122667786 = 5yr Fixed
    prime = fetch_boc_observation("V121758") or 5.95
    overnight = fetch_boc_observation("V39079") or 3.75
    fixed_5 = fetch_boc_observation("V122667786") or 4.49
    
    yields = fetch_provincial_yields()

    intel_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rates": {
            "boc_overnight": overnight,
            "bank_prime": prime,
            "five_year_fixed_uninsured": fixed_5
        },
        "provincial_yields": yields,
        "tax_thresholds": {
            "on_ltt_rebate_max": 4000,
            "bc_fthb_exemption": 835000
        }
    }

    with open(file_path, "w") as f:
        json.dump(intel_data, f, indent=4)
    
    print(f"✅ Market Intel Saved Successfully to: {file_path}")

if __name__ == "__main__":
    update_market_intel()
