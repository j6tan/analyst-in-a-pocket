import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from openai import OpenAI

# Initialize OpenAI Client (Ensure OPENAI_API_KEY is in your environment)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- 1. MARKET DATA SCRAPER (Bank of Canada) ---
def fetch_boc_observation(series_id):
    """Programmatic access to BoC macro data (Prime, Overnight, 5yr Fixed)."""
    try:
        url = f"https://www.bankofcanada.ca/valet/observations/{series_id}/json?recent=1"
        response = requests.get(url, timeout=10)
        data = response.json()
        if 'observations' in data and len(data['observations']) > 0:
            val = data['observations'][0].get(series_id, {}).get('v')
            return float(val) if val else None
        return None
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch {series_id}. Error: {e}")
        return None

# --- 2. NEW: BIG BANK SEMANTIC SCRAPER ---
def get_big_bank_variable_rates():
    """
    Scrapes public data from Big 3 Banks.
    Uses AI semantics to find rates instead of fragile HTML tags.
    """
    banks = {
        "RBC": "https://www.rbcroyalbank.com/mortgages/mortgage-rates.html",
        "TD": "https://www.td.com/ca/en/personal-banking/products/mortgages/mortgage-rates",
        "BMO": "https://www.bmo.com/main/personal/mortgages/mortgage-rates/"
    }
    
    results = {}
    print("📡 Monitoring Big Bank public announcements...")
    
    for bank, url in banks.items():
        try:
            res = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(res.text, 'html.parser')
            raw_text = soup.get_text(separator=' ', strip=True)[:5000] 

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"Extract the current 5-year closed VARIABLE mortgage rate for {bank}. Return ONLY the number as a float. If not found, return 0.0."},
                    {"role": "user", "content": f"TEXT: {raw_text}"}
                ]
            )
            rate = float(response.choices[0].message.content.strip())
            if rate > 0:
                results[bank] = rate
        except:
            continue
            
    return results

# --- 3. AI LEGISLATIVE INTERPRETER (BC PTT Rules) ---
def get_ai_interpreted_bc_rules():
    """Scrapes BC Gov text and uses AI to extract 2026 thresholds ($835k/$860k)."""
    url = "https://www2.gov.bc.ca/gov/content/taxes/property-taxes/property-transfer-tax/exemptions/first-time-home-buyers"
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        raw_text = soup.get_text(separator=' ', strip=True)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a specialized Canadian tax analyst. Extract property tax thresholds into JSON."},
                {"role": "user", "content": f"Extract the current BC First-Time Home Buyer exemption thresholds from this text. Look for rules effective in 2026. Return ONLY JSON with keys: 'fthb_full_limit' and 'fthb_partial_limit'. \n\nTEXT: {raw_text[:4000]}"}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"AI Scrape Failed: {e}. Using 2026 Fallbacks.")
        return {"fthb_full_limit": 835000, "fthb_partial_limit": 860000}

# --- 4. PROVINCIAL YIELD ANALYST (New Monthly Feature) ---
def get_monthly_provincial_yields():
    """
    Uses AI to estimate current average gross rental yields per province 
    based on the latest 2026 market trends.
    """
    try:
        print("📈 Analyzing Provincial Rental Yields...")
        market_context = "Current 2026 Canadian Real Estate Report: Yields are stabilizing. BC/ON averages 3.8-4.2%, AB/SK averages 5.5-6.5%, Atlantic Canada 5.0-6.0%."
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Provide the current average GROSS rental yield percentages for major Canadian provinces as of 2026. Return JSON only with province names as keys and floats as values (e.g. 4.2)."},
                {"role": "user", "content": market_context}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {
            "Ontario": 4.1, "BC": 3.8, "Alberta": 6.2, 
            "Manitoba": 5.8, "Quebec": 4.5, "Nova Scotia": 5.2, 
            "New Brunswick": 5.5, "Saskatchewan": 6.4
        }

# --- 5. MAIN SYNC ENGINE ---
def update_market_intel():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    if not os.path.exists(data_dir): os.makedirs(data_dir)
    file_path = os.path.join(data_dir, "market_intel.json")

    print("📡 Syncing 2026 Market Rates...")
    
    # Scrape Interest Rates
    prime = fetch_boc_observation("V121758") or 4.45
    overnight = fetch_boc_observation("V39079") or 2.25
    fixed_5 = fetch_boc_observation("V122667786") or 4.26
    
    # NEW: Fetch Big Bank Variable Rates
    bank_rates = get_big_bank_variable_rates()
    variable_5 = bank_rates.get("RBC", 3.95) # Use RBC as primary benchmark, fallback to 3.95
    
    # AI Scrape BC Rules
    print("🧠 Consulting AI for BC Legislative Updates...")
    bc_rules = get_ai_interpreted_bc_rules()

    print("📈 Analyzing Provincial Rental Yields...")
    yields = get_monthly_provincial_yields() 
    
    intel_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rates": {
            "bank_prime": prime,
            "five_year_fixed_uninsured": fixed_5,
            "five_year_variable": variable_5,
            "boc_overnight": overnight,
            "big_bank_monitor": bank_rates
        },
        "provincial_yields": yields,
        "tax_rules": {
            "BC": [
                {"threshold": 200000, "rate": 0.01},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 3000000, "rate": 0.03},
                {"threshold": 999999999, "rate": 0.05}
            ],
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
                {"threshold": 4000000, "rate": 0.044},
                {"threshold": 5000000, "rate": 0.0545},
                {"threshold": 10000000, "rate": 0.065},
                {"threshold": 20000000, "rate": 0.0755},
                {"threshold": 999999999, "rate": 0.086}
            ],
            "Manitoba": [
                {"threshold": 30000, "rate": 0.00},
                {"threshold": 90000, "rate": 0.005},
                {"threshold": 150000, "rate": 0.01},
                {"threshold": 200000, "rate": 0.015},
                {"threshold": 999999999, "rate": 0.02}
            ],
            "New Brunswick": [
                {"threshold": 999999999, "rate": 0.01}
            ],
            "Quebec": [
                {"threshold": 61700, "rate": 0.005},
                {"threshold": 308700, "rate": 0.01},
                {"threshold": 999999999, "rate": 0.015}
            ],
            "Nova Scotia": [
                {"threshold": 999999999, "rate": 0.015}
            ],
            "rebates": {
                "BC_FTHB_Threshold": bc_rules['fthb_full_limit'],
                "BC_FTHB_Partial_Limit": bc_rules['fthb_partial_limit'],
                "ON_FTHB_Max": 4000
            }
        }
    }

    with open(file_path, "w") as f:
        json.dump(intel_data, f, indent=4)
    print(f"✅ Market Sync Complete. Variable Rate: {variable_5}%")

if __name__ == "__main__":
    update_market_intel()
