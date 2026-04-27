import pandas as pd
import re
import requests
import json
import os

API_KEY = "4a65202efca81fc02eb466030c40f499725d2568"
URL = "https://google.serper.dev/search"

def clean_brand_name(name):
    return re.sub(r'\(.*?\)', '', name).strip()

def get_serper_result(query):
    payload = json.dumps({
        "q": query,
        "num": 1
    })
    headers = {
        'X-API-KEY': API_KEY,
        'Content-Type': 'application/json'
    }
    try:
        response = requests.request("POST", URL, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        organic = data.get('organic', [])
        if organic:
            return organic[0].get('link', '')
    except Exception as e:
        print(f"Error searching for {query}: {e}")
    return ''

def main():
    input_file = 'Antigl.csv'
    output_file = 'OSINT_API_Leads.csv'

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    try:
        df = pd.read_csv(input_file, encoding='latin1')
    except Exception as e:
        df = pd.read_csv(input_file)

    results_data = []

    print(f"Processing {len(df)} brands with Serper API...")

    for index, row in df.iterrows():
        original_brand = row.get('Brand / Company Name')
        if pd.isna(original_brand) or str(original_brand).strip() == "":
            continue

        search_term = clean_brand_name(str(original_brand))
        print(f"--- Processing {index+1}/{len(df)}: {search_term} ---")

        # Query 1: LinkedIn SPOC
        query1 = f'site:linkedin.com/in "{search_term}" "India" ("Head of Sales" OR "Director" OR "Partnerships")'
        link1 = get_serper_result(query1)

        # Query 2: B2B Mobile
        query2 = f'"{search_term}" "India" "+91" "B2B" -support'
        link2 = get_serper_result(query2)

        results_data.append({
            'Brand Name': original_brand,
            'SPOC LinkedIn URL': link1,
            'B2B Mobile Source': link2
        })

        # Save progress
        if (index + 1) % 10 == 0:
            pd.DataFrame(results_data).to_csv(output_file, index=False)

    final_df = pd.DataFrame(results_data)
    final_df.to_csv(output_file, index=False)
    print(f"Finished. Saved to {output_file}")

if __name__ == "__main__":
    main()
