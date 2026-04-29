import pandas as pd
import re
import requests
import json
import os

API_KEY = "4a65202efca81fc02eb466030c40f499725d2568"
URL = "https://google.serper.dev/search"
PHONE_REGEX = r'(?:\+91[-.\s]?)?[6789]\d{4}[-.\s]?\d{5}'

def clean_brand_name(name):
    return re.sub(r'\(.*?\)', '', name).strip()

def get_serper_results(query, num=1):
    payload = json.dumps({
        "q": query,
        "num": num
    })
    headers = {
        'X-API-KEY': API_KEY,
        'Content-Type': 'application/json'
    }
    try:
        response = requests.request("POST", URL, headers=headers, data=payload)
        response.raise_for_status()
        return response.json().get('organic', [])
    except Exception as e:
        print(f"Error searching for {query}: {e}")
    return []

def extract_phone_number(snippets):
    for snippet in snippets:
        match = re.search(PHONE_REGEX, snippet)
        if match:
            return match.group(0)
    return ""

def main():
    input_file = 'Antigl.csv'
    output_file = 'Final_Mobile_Numbers.csv'

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    try:
        df = pd.read_csv(input_file, encoding='latin1')
    except Exception as e:
        df = pd.read_csv(input_file)

    results_data = []

    print(f"Processing {len(df)} brands with Serper API and Phone Extraction...")

    for index, row in df.iterrows():
        original_brand = row.get('Brand / Company Name')
        if pd.isna(original_brand) or str(original_brand).strip() == "":
            continue

        search_term = clean_brand_name(str(original_brand))
        print(f"--- Processing {index+1}/{len(df)}: {search_term} ---")

        # Query 1: LinkedIn SPOC (Top 1)
        query1 = f'site:linkedin.com/in "{search_term}" "India" ("Head of Sales" OR "Director" OR "Partnerships")'
        results1 = get_serper_results(query1, 1)
        link1 = results1[0].get('link', '') if results1 else ''

        # Query 2: B2B Mobile (Top 3 for snippet extraction)
        query2 = f'"{search_term}" "India" "+91" "B2B" -support'
        results2 = get_serper_results(query2, 3)
        snippets = [r.get('snippet', '') for r in results2]
        phone = extract_phone_number(snippets)

        results_data.append({
            'Brand Name': original_brand,
            'SPOC LinkedIn URL': link1,
            'Extracted Phone Number': phone
        })

        # Save progress
        if (index + 1) % 10 == 0:
            pd.DataFrame(results_data).to_csv(output_file, index=False)

    final_df = pd.DataFrame(results_data)
    final_df.to_csv(output_file, index=False)
    print(f"Finished. Saved to {output_file}")

if __name__ == "__main__":
    main()
