import csv
import build_physiocare_leads

def generate_csv():
    leads = build_physiocare_leads.main()

    fieldnames = [
        "Business / Clinic Name & Category",
        "City & Location",
        "Contact Person / Owner / Decision Maker Title",
        "Standardized Contact Phone Number (+91XXXXXXXXXX)",
        "Email Address (if available)",
        "Website / Source Profile Link",
        "Current Setup / Infrastructure Notes",
        "Franchise Partnership Pitch Suitability & Priority Status"
    ]

    filename = "Nonstop_PhysioCare_Franchise_Leads_Sept15.csv"

    with open(filename, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in leads:
            writer.writerow(row)

    print(f"Successfully generated {filename} with {len(leads)} records.")

if __name__ == "__main__":
    generate_csv()
