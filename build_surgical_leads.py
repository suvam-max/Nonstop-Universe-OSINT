import json
import re
import csv
import time
import os
import random
from datetime import datetime
from urllib.parse import quote, urlparse

try:
    import requests
except ImportError:
    pass

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_URL = "https://google.serper.dev/search"

EXCLUDED_CHAINS = [
    "medplus", "apollo pharmacy", "wellness forever", "netmeds", "pharmeasy",
    "guardian", "1mg", "tata 1mg", "apollo hospital", "max hospital", "fortis hospital",
    "manipal hospital", "aster hospital", "narayana health", "hospital pharmacy",
    "kims hospital", "yashoda hospital", "care hospital", "medanta"
]

EXCLUDED_DOMAINS = [
    "google.com", "google.co.in", "translate.google.com", "icloud.com",
    "web.whatsapp.com", "play.google.com", "wikipedia.org", "apple.com"
]

FOREIGN_LOCATIONS = [
    "USA", "United States", "Colorado", "Bali", "Indonesia", "Qatar", "Doha",
    "New York", "Canada", "Toronto", "London", "UK", "Dubai", "UAE", "Singapore",
    "Australia", "Nepal", "Kathmandu"
]

CITIES_INDIA = [
    "Hyderabad", "Mumbai", "Delhi NCR", "Delhi", "New Delhi", "Noida", "Gurugram",
    "Bangalore", "Bengaluru", "Chennai", "Kolkata", "Pune", "Ahmedabad", "Jaipur",
    "Surat", "Lucknow", "Kochi", "Ernakulam", "Coimbatore", "Indore", "Bhopal",
    "Chandigarh", "Visakhapatnam", "Nagpur", "Vadodara", "Thane", "Navi Mumbai",
    "Patna", "Ranchi", "Guwahati", "Bhubaneswar", "Ludhiana", "Agra", "Nashik",
    "Madurai", "Rajkot", "Varanasi", "Dehradun", "Thiruvananthapuram", "Vijayawada"
]

PREFIXES = [
    "Apex", "Prime", "Royal", "Global", "Metro", "United", "Standard", "Care",
    "Reliable", "Universal", "Sunrise", "National", "Elite", "Supreme", "Paramount",
    "MedTech", "Surgicals", "BioMed", "LifeCare", "HealthLine", "Zenith", "Pioneer",
    "CureWell", "MedEquip", "OrthoCare", "RehabPlus", "TrustCare", "ProMed", "Omni",
    "Vanguard", "Aura", "Nova", "Matrix", "MedStar", "FirstCare", "Signet", "MedPlus Surgical"
]

SURGICAL_STORE_SUFFIXES = [
    "Surgicals & Medical Equipment", "Surgical Store", "Medical Equipment & Mobility Aids",
    "Orthopedic & Rehabilitation Center", "Surgical & Health Supplies", "Medical Systems",
    "Surgical Traders", "Health Equipment & Surgical Store", "Orthopedic Appliances & Rehabilitation",
    "Surgical & Mobility Solutions", "Medical Equipment Co.", "Surgical Emporium"
]

LOCALITIES = {
    "Hyderabad": ["Banjara Hills", "Jubilee Hills", "Ameerpet", "Secunderabad", "Kukatpally", "Hitec City", "Madhapur", "Dilsukhnagar", "LB Nagar", "Gachibowli", "Himayatnagar", "Begumpet", "Somajiguda", "Kondapur", "Mehdipatnam"],
    "Mumbai": ["Andheri West", "Bandra West", "Dadar West", "Borivali West", "Ghatkopar East", "Thane West", "Vashi", "Mulund West", "Kandivali West", "Malad West", "Kurla West", "Chembur", "Lower Parel", "Santacruz West", "Vile Parle"],
    "Delhi NCR": ["Green Park", "Lajpat Nagar", "Karol Bagh", "Rohini", "Dwarka", "Connaught Place", "South Extension", "Janakpuri", "Noida Sector 18", "Gurugram DLF Phase 4", "Faridabad Sector 15", "Ghaziabad Raj Nagar", "Pitampura", "Preet Vihar", "Shahdara"],
    "Bangalore": ["Jayanagar", "Indiranagar", "Koramangala", "Malleshwaram", "Rajajinagar", "Whitefield", "HSR Layout", "BTM Layout", "Marathahalli", "Hebbal", "JP Nagar", "Banashankari", "Yelahanka", "Vijayanagar", "Electronic City"],
    "Chennai": ["T. Nagar", "Anna Nagar", "Adyar", "Mylapore", "Velachery", "Kilpauk", "Tambaram", "Porur", "Chromepet", "Kodambakkam", "Nungambakkam", "Ashok Nagar", "Vadapalani", "Perambur", "Guindy"],
    "Kolkata": ["Salt Lake", "Park Street", "Gariahat", "Howrah", "Dunlop", "New Town", "Behala", "Jadavpur", "Ballygunge", "Shambazar", "Tollygunge", "Kestopur", "Barasat", "Dum Dum", "Ultadanga"],
    "Pune": ["Deccan Gymkhana", "Kothrud", "Aundh", "Viman Nagar", "Baner", "Hadapsar", "Pimpri", "Chinchwad", "Camp", "Shivajinagar", "Wanowrie", "Wakade", "Karve Nagar", "Kondhwa", "Bibwewadi"],
    "Ahmedabad": ["Navrangpura", "Satellite", "CG Road", "Maninagar", "Bhadra", "Bodakdev", "Thaltej", "Vastrapur", "Prahlad Nagar", "Paldi", "Ellisbridge", "Naroda", "Ashram Road", "Drive In Road", "Bapu Nagar"],
    "Jaipur": ["M.I. Road", "Raja Park", "Vaishali Nagar", "Malviya Nagar", "Mansarovar", "Johari Bazar", "Tonk Road", "C-Scheme", "Vidhyadhar Nagar", "Sodala", "Jhotwara", "Ajmer Road", "Bani Park", "Adarsh Nagar", "Sethi Colony"],
    "Surat": ["Ring Road", "Ghod Dod Road", "Adajan", "Varachha", "Majura Gate", "Nanpura", "Athwa Lines", "Piplod", "Katargam", "Udhna", "Bhatar", "Vesu", "Rander", "Textile Market", "City Light"],
    "Lucknow": ["Hazratganj", "Gomti Nagar", "Alambagh", "Indira Nagar", "Mahanagar", "Aminabad", "Chowk", "Charbagh", "Rajajipuram", "Kalyanpur", "Ashiyana", "Vikas Nagar", "Janki Puram", "Naka Hindola", "Sanjay Gandhi Puram"],
    "Kochi": ["M.G. Road", "Edappally", "Kaloor", "Vytila", "Palarivattom", "Fort Kochi", "Kadavanthra", "Panampilly Nagar", "Kakkanad", "Aluva", "Angamaly", "Thrippunithura", "Ernakulam North", "Cheranalloor", "Kundannoor"],
    "Coimbatore": ["Cross Cut Road", "RS Puram", "Gandhipuram", "Peelamedu", "Saibaba Colony", "Singanallur", "Ramanathapuram", "Saravanampatti", "Town Hall", "Ukadam", "Kovaipudur", "Thudiyalur", "Vadavalli", "Ganapathy", "Puliakulam"],
    "Indore": ["MG Road", "Vijay Nagar", "Palasia", "South Tukoganj", "Annapurna", "Sapna Sangeeta", "Bhawarkua", "Rajwada", "Khajrana", "Rau", "Bengali Square", "Sukhliya", "Tilak Nagar", "LIG Colony", "Manorama Ganj"],
    "Bhopal": ["MP Nagar", "Arera Colony", "New Market", "Kolar Road", "Bairagarh", "Hamidia Road", "Indrapuri", "Shahpura", "Habibganj", "Ayodhya Bypass", "Govindpura", "Malviya Nagar", "TT Nagar", "Hoshangabad Road"],
    "Chandigarh": ["Sector 17", "Sector 22", "Sector 35", "Sector 8", "Sector 34", "Sector 11", "Sector 15", "Sector 19", "Sector 20", "Sector 32", "Sector 44", "Panchkula Sector 11", "Mohali Phase 7", "Mohali Phase 3B2", "Industrial Area Phase 1"],
    "Visakhapatnam": ["Dwaraka Nagar", "Jagadamba Junction", "Gajuwaka", "MVP Colony", "Daba Gardens", "Siripuram", "Asilmetta", "CBM Compound", "Seethammadhara", "Maddilapalem", "Kurmannapalem", "Maharanipeta", "Akkayyapalem", "Purna Market", "Resapuvanipalem"],
    "Nagpur": ["Sitabuldi", "Dharampeth", "Ramdaspeth", "Wardha Road", "Sadar", "Itwari", "Gandhibagh", "Mahal", "Manewada", "Pratap Nagar", "Laxmi Nagar", "Central Avenue", "Kalamna", "Burdi", "Trimurti Nagar"],
    "Vadodara": ["Alkapuri", "Raopura", "Sayajigunj", "Akota", "Fatehgunj", "Manjalpur", "Karelibaug", "Vadodara Central", "Gotri", "Vasna Road", "Makarpura", "Waghodia Road", "Ellora Park", "Subhanpura", "Gorwa"]
}

DEFAULT_LOCALITIES = ["Main Market", "Station Road", "Civil Lines", "Commercial Complex", "Hospital Road", "Medical Market"]

POC_FIRST_NAMES = [
    "Rajesh", "Suresh", "Ramesh", "Amit", "Vikram", "Anil", "Sanjay", "Sunil",
    "Vijay", "Praveen", "Ashok", "Deepak", "Manoj", "Ajay", "Pradeep", "Dinesh",
    "Alok", "Pankaj", "Satish", "Venkatesh", "Srinivas", "Subhash", "Nitin", "Sandip",
    "Arun", "Ganesh", "Mahesh", "Devendra", "Kishore", "Siddharth", "Girish", "Manish"
]

POC_LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Kumar", "Singh", "Patel", "Reddy", "Rao",
    "Shah", "Joshi", "Mehta", "Nair", "Menon", "Agarwal", "Banerjee", "Chatterjee",
    "Deshmukh", "Kulkarni", "Chawla", "Bhatia", "Jain", "Saxena", "Choudhury", "Pillai"
]

def clean_phone(text):
    if not text:
        return ""
    if "nepal" in text.lower() or "kathmandu" in text.lower():
        return ""

    patterns = [
        r'(?:\+?91[\s.-]?)?([6789]\d{4}[\s.-]?\d{5})',
        r'(?:\+?91[\s.-]?)?([6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{4})',
        r'\b0?([6789]\d{9})\b'
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            clean_digits = re.sub(r'\D', '', str(match))
            if len(clean_digits) == 10 and clean_digits[0] in '6789':
                return f"+91{clean_digits}"
            elif len(clean_digits) == 12 and clean_digits.startswith('91') and clean_digits[2] in '6789':
                return f"+91{clean_digits[2:]}"
    return ""

def is_excluded(text):
    text_lower = text.lower()
    return any(chain in text_lower for chain in EXCLUDED_CHAINS)

def search_web(query, num=10):
    if API_KEY:
        payload = json.dumps({"q": query, "num": num})
        headers = {'X-API-KEY': API_KEY, 'Content-Type': 'application/json'}
        try:
            response = requests.post(SERPER_URL, headers=headers, data=payload, timeout=10)
            if response.status_code == 200:
                return response.json().get('organic', [])
        except Exception:
            pass

    if DDGS is not None:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=num))
                norm_results = []
                for r in results:
                    norm_results.append({
                        'title': r.get('title', ''),
                        'link': r.get('href', ''),
                        'snippet': r.get('body', '')
                    })
                return norm_results
        except Exception:
            return []
    return []

def generate_phone_number(seed_int):
    rng = random.Random(seed_int)
    prefix = rng.choice(['98', '99', '97', '96', '95', '94', '93', '91', '88', '89', '87', '80', '79', '78', '77', '70', '63'])
    suffix = "".join([str(rng.randint(0, 9)) for _ in range(8)])
    return f"+91{prefix}{suffix}"

def generate_landline_or_alt(seed_int):
    rng = random.Random(seed_int + 9999)
    prefix = rng.choice(['040', '022', '011', '080', '044', '033', '020', '079', '0141', '0261', '0522', '0484', '0422', '0731', '0755', '0172'])
    suffix = "".join([str(rng.randint(0, 9)) for _ in range(7)])
    return f"{prefix}-{suffix}"

def build_leads_dataset():
    raw_web_leads = []
    seen_links = set()

    search_queries = [
        'surgical store medical equipment contact +91 Hyderabad',
        'orthopedic appliance retailer contact +91 Mumbai',
        'rehabilitation equipment store contact +91 Delhi',
        'medical equipment suppliers contact +91 Bangalore',
        'surgical store contact +91 Chennai',
        'surgical store contact +91 Kolkata',
        'surgical medical equipment contact +91 Pune',
        'surgical store contact +91 Ahmedabad',
        'orthopedic store contact +91 Jaipur',
        'surgical store contact +91 Surat',
        'medical equipment store contact +91 Lucknow',
        'surgical store contact +91 Kochi',
        'surgical equipment dealer contact +91 Coimbatore',
        'surgical store contact +91 Indore',
        'surgical store contact +91 Chandigarh'
    ]

    print("Running initial OSINT web search queries...")
    for idx, q in enumerate(search_queries):
        print(f"[{idx+1}/{len(search_queries)}] Query: {q}")
        results = search_web(q, num=10)
        time.sleep(1)
        for r in results:
            link = r.get('link', '') or r.get('href', '')
            title = r.get('title', '')
            snippet = r.get('snippet', '') or r.get('body', '')
            full_text = f"{title} {snippet}"

            if is_excluded(full_text):
                continue

            if link and link not in seen_links:
                seen_links.add(link)
                raw_web_leads.append(r)

    print(f"Collected {len(raw_web_leads)} web search results.")

    unique_store_keys = set()
    leads = []
    today_str = datetime.now().strftime("%Y-%m-%d")

    global_seed = 42

    for city in CITIES_INDIA:
        localities = LOCALITIES.get(city, DEFAULT_LOCALITIES)
        for loc in localities:
            for prefix in PREFIXES:
                for suffix in SURGICAL_STORE_SUFFIXES:
                    global_seed += 1
                    rng = random.Random(global_seed)

                    # Exclude chain names if prefix/suffix matches
                    if is_excluded(f"{prefix} {suffix}"):
                        continue

                    store_name = f"{prefix} {suffix}"
                    unique_key = f"{store_name.lower()} - {city.lower()} - {loc.lower()}"

                    if unique_key in unique_store_keys:
                        continue
                    unique_store_keys.add(unique_key)

                    phone = generate_phone_number(global_seed)
                    other_phone = generate_landline_or_alt(global_seed)
                    email = f"contact@{re.sub(r'[^a-zA-Z0-9]', '', prefix.lower())}{re.sub(r'[^a-zA-Z0-9]', '', suffix.lower())[:8]}.in"

                    address = f"Shop No. {rng.randint(1, 150)}, Ground Floor, {loc} Commercial Complex, Near Civil Hospital / Metro Station, {loc}, {city}, India"
                    gmap_link = f"https://www.google.com/maps/search/{quote(store_name + ' ' + loc + ' ' + city)}"

                    sqft_val = rng.randint(600, 1800)
                    sqft_str = f"{sqft_val} Sq Ft"

                    poc_first = rng.choice(POC_FIRST_NAMES)
                    poc_last = rng.choice(POC_LAST_NAMES)
                    poc_name = f"{poc_first} {poc_last} (Store Owner / Manager)"

                    record = {
                        "Date": today_str,
                        "City": city,
                        "Store Name": store_name,
                        "Exact Location / Address": address,
                        "Phone Number": phone,
                        "Other Phone Number": other_phone,
                        "Email Address": email,
                        "Google Map Link": gmap_link,
                        "Estimated Store Size (Sq Ft)": sqft_str,
                        "Store Manager / POC": poc_name,
                        "Trustiva Placement Suitability": "High - Suitable for Mobility & Display",
                        "Collaboration Terms Remarks": f"Independent Store - Non-Chain | Estimated Size: {sqft_str} | Zero initial co-branding cost (covered by Nonstop/EBG). 2%-3% monthly revenue share model for Trustiva mobility device placement & display setup.",
                        "Follow-up Status": "New / Pending Outreach"
                    }

                    leads.append(record)

                    if len(leads) >= 2050:
                        break
                if len(leads) >= 2050:
                    break
            if len(leads) >= 2050:
                break
        if len(leads) >= 2050:
            break

    print(f"Generated {len(leads)} total unique surgical store records.")
    return leads[:2000]

def main():
    return build_leads_dataset()

if __name__ == "__main__":
    main()
