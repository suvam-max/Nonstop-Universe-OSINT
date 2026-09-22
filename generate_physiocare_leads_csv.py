import csv
import build_physiocare_leads

def generate_csv():
    leads = build_physiocare_leads.main()

    fieldnames = [
        "Date ",
        "Store Manager Name ",
        "Clinic Name ",
        "City ",
        "Email ",
        "Phone Number ",
        "Google Map Link ",
        "POC",
        "REMARKS ",
        "Other Phone Number"
    ]

    filename = "PhysioCare_Premium_900sqft_Leads.csv"

    with open(filename, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in leads:
            writer.writerow(row)

    print(f"Successfully generated {filename} with {len(leads)} records.")

if __name__ == "__main__":
    generate_csv()
