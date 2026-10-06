import csv
import build_surgical_leads

def generate_csv():
    leads = build_surgical_leads.main()

    fieldnames = [
        'Date',
        'City',
        'Store Name',
        'Exact Location / Address',
        'Phone Number',
        'Other Phone Number',
        'Email Address',
        'Google Map Link',
        'Estimated Store Size (Sq Ft)',
        'Store Manager / POC',
        'Trustiva Placement Suitability',
        'Collaboration Terms Remarks',
        'Follow-up Status'
    ]

    filename = "Surgical_Stores_Trustiva_Collaboration_Leads.csv"

    with open(filename, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in leads:
            writer.writerow(row)

    print(f"Successfully generated {filename} with {len(leads)} records.")

if __name__ == "__main__":
    generate_csv()
