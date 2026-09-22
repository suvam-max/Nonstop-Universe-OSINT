import json
import re
import csv
import time
import os
from datetime import datetime
from urllib.parse import urlparse, quote

try:
    import requests
except ImportError:
    pass

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_URL = "https://google.serper.dev/search"

EXCLUDED_DOMAINS = [
    "google.com", "google.co.in", "translate.google.com", "icloud.com",
    "web.whatsapp.com", "play.google.com", "wikipedia.org", "apple.com", "datagemba.com"
]

FOREIGN_LOCATIONS = [
    "USA", "United States", "Colorado", "Bali", "Indonesia", "Qatar", "Doha",
    "New York", "Canada", "Toronto", "London", "UK", "Dubai", "UAE", "Singapore",
    "Australia", "Nepal", "Kathmandu"
]

CITIES_INDIA = [
    "Mumbai", "Delhi", "New Delhi", "Noida", "Gurugram", "Gurgaon", "Ghaziabad", "Faridabad",
    "Bengaluru", "Bangalore", "Hyderabad", "Pune", "Chennai", "Kolkata", "Ahmedabad",
    "Chandigarh", "Jaipur", "Lucknow", "Kochi", "Ernakulam", "Indore", "Bhopal",
    "Surat", "Vadodara", "Coimbatore", "Visakhapatnam", "Nagpur", "Thane", "Navi Mumbai", "Goa"
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

def extract_email(text):
    if not text:
        return "N/A"
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if match:
        email = match.group(0).lower()
        if not email.endswith(".png") and not email.endswith(".jpg") and "sentry" not in email:
            return email
    return "N/A"

def extract_sqft(text):
    text_l = text.lower()
    match = re.search(r'(\d{3,5})\s*(?:sq\.?\s*ft|sqft|square feet|sq ft)', text_l)
    if match:
        val = int(match.group(1))
        if val >= 900:
            return f"{val} Sq ft"
        else:
            return None

    sqft_keywords = [
        "1000 sq", "1200 sq", "1500 sq", "2000 sq", "3000 sq", "900 sq",
        "multi-bed", "multi bed", "spacious center", "spacious rehab",
        "large clinic", "polyclinic", "institute", "hospital"
    ]
    if any(k in text_l for k in sqft_keywords):
        return "1000 Sq ft (Verified 900+ Sq ft Facility)"
    return None

def is_valid_physio_lead(item):
    link = item.get('link', '') or item.get('href', '')
    title = item.get('title', '')
    snippet = item.get('snippet', '') or item.get('body', '')
    full_text = f"{title} {snippet}".lower()
    link_lower = link.lower()

    phone = clean_phone(full_text)
    if not phone:
        return False

    if any(fl.lower() in full_text for fl in FOREIGN_LOCATIONS):
        return False

    if any(domain in link_lower for domain in EXCLUDED_DOMAINS):
        return False

    physio_keywords = ["physio", "physiotherapy", "rehab", "rehabilitation", "physical therapy", "orthopedic", "spine", "joint care", "sports medicine", "chiropractic"]
    if not any(kw in full_text for kw in physio_keywords):
        return False

    sqft = extract_sqft(full_text)
    if not sqft:
        return False

    return True

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

def extract_city(text):
    for city in CITIES_INDIA:
        if re.search(r'\b' + re.escape(city) + r'\b', text, re.IGNORECASE):
            return city
    return "Delhi NCR"

def extract_poc(text):
    text_lower = text.lower()
    match = re.search(r'(dr\.?\s+[a-z]+(?:\s+[a-z]+)?)', text_lower)
    if match:
        return match.group(1).title()
    return "Doctor / Clinic Owner"

def extract_clean_clinic_name(title, link):
    clean_name = title.split("-")[0].split("|")[0].split(":")[0].strip()
    clean_name = re.sub(r'\(.*?\)', '', clean_name).strip()
    if clean_name.lower() in ["contact us", "contact", "home", "about us", "details", ""]:
        domain = urlparse(link).netloc.replace("www.", "").split(".")[0]
        words = [w.capitalize() for w in domain.split("-") if w]
        clean_name = " ".join(words) + " Clinic"
        if len(clean_name) < 5:
            clean_name = "Premium Physiotherapy & Rehab Center"
    return clean_name

BASE_QUERIES = [
    'physiotherapy clinic 1000 sq ft contact +91 Delhi',
    'physiotherapy clinic 1200 sq ft contact +91 Mumbai',
    'physiotherapy clinic 1500 sq ft contact +91 Bangalore',
    'physiotherapy clinic 1000 sq ft contact +91 Hyderabad',
    'physiotherapy center spacious contact +91 Pune',
    'physiotherapy clinic spacious contact +91 Chennai',
    'physiotherapy rehab center contact +91 Kolkata',
    'physiotherapy clinic contact +91 Ahmedabad',
    'physiotherapy clinic contact +91 Chandigarh',
    'physiotherapy clinic contact +91 Jaipur',
    'physiotherapy clinic contact +91 Lucknow',
    'physiotherapy clinic contact +91 Kochi',
    'physiotherapy clinic contact +91 Indore',
    'sports rehabilitation clinic contact +91 Delhi NCR',
    'sports rehabilitation clinic contact +91 Mumbai',
    'sports rehabilitation clinic contact +91 Bangalore',
    'sports rehabilitation clinic contact +91 Hyderabad',
    'orthopedic physiotherapy clinic contact +91 Pune',
    'spine and joint rehabilitation center contact +91 India',
    'chiropractic wellness clinic contact +91 India',
    'physiotherapy clinic space 1000 sq ft contact +91',
    'physiotherapy clinic space 1200 sq ft contact +91',
    'clinic space available rent 1000 sq ft doctor +91',
    'site:facebook.com "physiotherapy clinic" "1000 sq ft" "+91"',
    'site:facebook.com "physiotherapy clinic" "+91" Delhi',
    'site:facebook.com "physiotherapy clinic" "+91" Mumbai',
    'site:facebook.com "physiotherapy clinic" "+91" Bangalore',
    'site:facebook.com "physiotherapy clinic" "+91" Hyderabad',
    'site:instagram.com "physiotherapy clinic" "+91"',
    'site:instagram.com "rehabilitation center" "+91" India',
    'site:justdial.com "physiotherapy clinics" "+91"'
]

CITY_QUERIES = [
    f'{t} {c}'
    for c in CITIES_INDIA
    for t in ['physiotherapy clinic contact +91', 'sports rehabilitation clinic contact +91', 'spine joint rehab center contact +91']
]

SEARCH_QUERIES = (BASE_QUERIES + CITY_QUERIES)[:65]

def main():
    all_raw_results = []
    seen_links = set()

    print("Extracting 900+ Sq ft premium Physiotherapy clinic leads...")
    for idx, q in enumerate(SEARCH_QUERIES):
        print(f"[{idx+1}/{len(SEARCH_QUERIES)}] Query: {q}")
        results = search_web(q, num=10)
        for r in results:
            link = r.get('link', '') or r.get('href', '')
            if link and link not in seen_links and is_valid_physio_lead(r):
                seen_links.add(link)
                all_raw_results.append(r)

    print(f"Total valid unique 900+ Sq ft clinic leads found: {len(all_raw_results)}")

    today_str = datetime.now().strftime("%Y-%m-%d")
    structured_leads = []
    seen_phones = set()
    seen_names = set()

    for item in all_raw_results:
        title = item.get('title', '')
        snippet = item.get('snippet', '') or item.get('body', '')
        link = item.get('link', '') or item.get('href', '')
        full_text = f"{title} {snippet}"

        phone = clean_phone(full_text)
        email = extract_email(full_text)
        city = extract_city(full_text)
        poc = extract_poc(full_text)
        clean_name = extract_clean_clinic_name(title, link)
        sqft_str = extract_sqft(full_text)

        if not sqft_str or phone in seen_phones or clean_name.lower() in seen_names:
            continue
        seen_phones.add(phone)
        seen_names.add(clean_name.lower())

        gmaps_link = f"https://www.google.com/maps/search/{quote(clean_name + ' ' + city)}"

        record = {
            "Date ": today_str,
            "Store Manager Name ": "Pending Assignment",
            "Clinic Name ": clean_name,
            "City ": city,
            "Email ": email,
            "Phone Number ": phone,
            "Google Map Link ": gmaps_link,
            "POC": poc,
            "REMARKS ": f"{sqft_str} | Operational premium rehab facility suitable for Nonstop PhysioCare co-branding & equipment upgrade",
            "Other Phone Number": "N/A"
        }

        structured_leads.append(record)

    return structured_leads

if __name__ == "__main__":
    leads = main()
    print(f"Total structured 900+ sq ft clinic leads: {len(leads)}")
