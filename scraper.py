import pandas as pd
import re
import time
from duckduckgo_search import DDGS
import os

def clean_brand_name(name):
    # Strip out any text inside parentheses
    return re.sub(r'\(.*?\)', '', name).strip()

def get_ddg_results(query, num_results=2):
    results = []
    print(f"Searching DuckDuckGo: {query}")
    try:
        with DDGS() as ddgs:
            ddgs_gen = ddgs.text(query, max_results=num_results)
            for r in ddgs_gen:
                results.append(r['href'])
                print(f"  Found: {r['href']}")
                if len(results) >= num_results:
                    break
    except Exception as e:
        print(f"Error searching for {query}: {e}")
    return results

def main():
    # The user provided Antigl.csv in the repo
    input_file = 'Antigl.csv'
    output_file = 'OSINT_Exact_SPOC_Leads.csv'

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    try:
        df = pd.read_csv(input_file, encoding='latin1')
    except Exception as e:
        df = pd.read_csv(input_file)

    # Check if output already exists to resume
    if os.path.exists(output_file):
        processed_df = pd.read_csv(output_file)
        processed_brands = processed_df['Brand Name'].tolist()
        results_data = processed_df.to_dict('records')
        print(f"Resuming from brand {len(processed_brands)}")
    else:
        processed_brands = []
        results_data = []

    print(f"Processing {len(df)} brands...")

    for index, row in df.iterrows():
        original_brand = row.get('Brand / Company Name')
        if pd.isna(original_brand) or str(original_brand).strip() == "":
            continue

        if original_brand in processed_brands:
            continue

        search_term = clean_brand_name(str(original_brand))
        print(f"--- Processing {index+1}/{len(df)}: {search_term} ---")

        # Query 1 (SPOC LinkedIn Hunter)
        query1 = f'site:linkedin.com/in "{search_term}" "India" ("Head of Sales" OR "Director" OR "Partnerships" OR "B2B")'
        urls1 = get_ddg_results(query1, 2)
        time.sleep(4)

        # Query 2 (Direct Mobile Hunter)
        query2 = f'"{search_term}" "India" ("+91" OR "91-") ("Director" OR "Sales" OR "B2B" OR "Wholesale") -support -"customer care" -toll-free'
        urls2 = get_ddg_results(query2, 2)
        time.sleep(4)

        # Padding
        while len(urls1) < 2:
            urls1.append("")
        while len(urls2) < 2:
            urls2.append("")

        results_data.append({
            'Brand Name': original_brand,
            'SPOC LinkedIn URL 1': urls1[0],
            'SPOC LinkedIn URL 2': urls1[1],
            'B2B Mobile Source 1': urls2[0],
            'B2B Mobile Source 2': urls2[1]
        })

        # Save after every brand to be safe
        pd.DataFrame(results_data).to_csv(output_file, index=False)

    print(f"Finished. Saved to {output_file}")

if __name__ == "__main__":
    main()
