import csv
import build_tracker

def generate_csv():
    listings = build_tracker.main()

    fieldnames = [
        "Business/Property Name & Category",
        "City & Exact Location",
        "Property Size",
        "Existing Interiors & Infrastructure",
        "Current Operational Status",
        "Footfall & Location Potential",
        "Asking Price / Investment Required",
        "Reason for Sale / Partnership",
        "Owner/Broker Contact Details",
        "Listing Platform & Source Link",
        "Images / Google Drive Link",
        "Key Observations & Recommendations",
        "Priority & Follow-up Status",
        "Remarks"
    ]

    # Save to Business_Acquisition_Tracker.csv
    filename = "Business_Acquisition_Tracker.csv"

    with open(filename, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in listings:
            writer.writerow(row)

    print(f"Successfully generated {filename} with {len(listings)} records.")

if __name__ == "__main__":
    generate_csv()
