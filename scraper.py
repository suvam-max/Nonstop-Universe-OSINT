import requests
import re
import pandas as pd
import json
import time
import os

# Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "8656ae64aca28fe2c7eeec1401eddb887fb0d7dd")
SERPER_URL = "https://google.serper.dev/search"
TARGET_UNIQUE_NUMBERS = 200
OUTPUT_FILE = "Strict_200_B2B_Pipeline.csv"

# Step 2: The Product Matrix
PRODUCTS = [
    'Continuous Glucose Monitors', 'Metabolic Breath Analyzers', 'Wearable Sleep Trackers',
    'Red Light Therapy Panels', 'HBOT Chambers', 'PEMF Mats', 'Brain-Sensing Headbands',
    'Smart Mattresses', 'Pneumatic Compression Boots', 'Targeted Shockwave Therapy',
    'TENS Machines', 'CPM Machines', 'Percussive Massage Guns', 'Orthopedic Heating Pads',
    'Clinical K-Tape', 'Carbon Fiber Wheelchairs', 'Electric Wheelchairs', 'Smart Walking Canes',
    'Patient Transfer Hoists', 'Smart Insoles', 'Motorized ICU Beds',
    'Dynamic Alternating Pressure Mattresses', 'Premium Commode Chairs', 'Orthopedic Seat Cushions',
    'Automated Medication Dispensers', 'White Noise Sleep Devices', 'Smart ECG Monitors',
    'Multiparameter Patient Monitors', 'Smart BP Monitors', 'Oxygen Concentrators',
    'Compressor Nebulizers', 'Adult Diapers Wholesale', 'Washable Silicone Bedpans',
    'Medical Nitrile Gloves', 'Orthopedic Bracing'
]

def clean_title(title):
    """
    Step 4: Clean the 'Supplier Title'. Strip out generic platform text.
    """
    if not title:
        return ""
    # Remove common platform suffixes and generic ID strings
    title = re.split(r' - IndiaMART| - TradeIndia| \| ID:| - Indiamart| \| IndiaMART', title, flags=re.IGNORECASE)[0]
    title = re.sub(r' \| .*$', '', title)
    title = re.sub(r' ID: .*$', '', title)
    return title.strip()

def clean_phone_number(phone):
    """
    Step 4: Clean the extracted number to remove spaces/dashes so it formats cleanly.
    """
    digits = re.sub(r'[^\d]', '', phone)
    # The regex already matched +91 or 91 or a number starting with 6-9
    # We want +919876543210 format
    if len(digits) >= 10:
        return '+91' + digits[-10:]
    return '+91' + digits

def extract_numbers(text):
    """
    Step 4: Use this strict Indian mobile regex on the snippet.
    """
    # Regex provided by user: r'\+91[-.\s]?[6789]\d{4}[-.\s]?\d{5}'
    # Note: IndiaMART snippets often format numbers as +91 804... or 0804...
    # but the user specifically wants mobile numbers starting with 6, 7, 8, or 9.
    pattern = r'\+91[-.\s]?[6789]\d{4}[-.\s]?\d{5}'
    matches = re.findall(pattern, text)

    return [clean_phone_number(m) for m in matches]

def search_serper(product, num_results=10, page=1):
    """
    Step 3: Strict Verified Search (Mobile Focus)
    """
    # Query provided by user
    query = f'site:indiamart.com OR site:tradeindia.com "{product}" "India" "Verified Supplier" OR "Authorized Distributor" "+91" -"1800" -"toll-free" -"customer care"'

    payload = json.dumps({
        "q": query,
        "num": num_results,
        "page": page
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(SERPER_URL, headers=headers, data=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # If strict query fails, try a slightly broader one to ensure volume as discussed in turns
        fallback_query = f'site:indiamart.com "{product}" IndiaMART contact number'
        payload = json.dumps({"q": fallback_query, "num": num_results, "page": page})
        try:
            response = requests.post(SERPER_URL, headers=headers, data=payload)
            return response.json()
        except:
            return {}

def main():
    unique_numbers = set()
    results_list = []

    # Load existing to deduplicate if script is resumed
    if os.path.exists(OUTPUT_FILE):
        try:
            existing_df = pd.read_csv(OUTPUT_FILE)
            for num in existing_df['Direct B2B Number'].tolist():
                unique_numbers.add(str(num))
            results_list = existing_df.to_dict('records')
        except:
            pass

    print(f"Starting extraction. Current Unique: {len(unique_numbers)}")

    current_page = 1
    while len(unique_numbers) < TARGET_UNIQUE_NUMBERS and current_page <= 5:
        print(f"--- Processing Page {current_page} ---")
        found_this_page = 0

        for product in PRODUCTS:
            if len(unique_numbers) >= TARGET_UNIQUE_NUMBERS:
                break

            search_data = search_serper(product, num_results=20, page=current_page)

            organic_results = search_data.get('organic', [])
            for result in organic_results:
                title = result.get('title', '')
                link = result.get('link', '')
                snippet = result.get('snippet', '')

                extracted = extract_numbers(snippet)
                for num in extracted:
                    if num not in unique_numbers:
                        unique_numbers.add(num)
                        results_list.append({
                            "Product Category": product,
                            "Supplier Title": clean_title(title),
                            "Direct B2B Number": num,
                            "Verified Directory Link": link
                        })
                        found_this_page += 1
                        if len(unique_numbers) >= TARGET_UNIQUE_NUMBERS:
                            break

            # Small delay to respect API
            time.sleep(0.2)

        if found_this_page == 0:
            break
        current_page += 1

    # Step 5: Save to CSV
    df = pd.DataFrame(results_list)
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"Extraction finished. Total Unique: {len(unique_numbers)}")

if __name__ == "__main__":
    main()
