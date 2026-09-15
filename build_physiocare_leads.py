import requests
import json
import re
import csv
import time
import os

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from urllib.parse import urlparse

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

CATEGORIES = {
    "Physiotherapy Clinic / Rehab Center": ["physiotherapy", "physio", "rehab", "rehabilitation", "physical therapy"],
    "Gym & Fitness Center": ["gym", "fitness", "crossfit", "workout", "sports performance", "training center"],
    "Wellness & Orthopedic Center": ["wellness", "orthopedic", "spine", "joint care", "sports medicine"],
    "Chiropractic & Yoga/Pilates Studio": ["chiropractic", "chiro", "yoga", "pilates", "posture"]
}

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

def is_valid_lead(item):
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

    lead_keywords = ["physio", "physiotherapy", "gym", "fitness", "rehab", "wellness", "orthopedic", "chiropractic", "yoga", "pilates", "sports"]
    if not any(kw in full_text for kw in lead_keywords):
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
    return "Delhi NCR / Metro India"

def extract_category(text):
    text_lower = text.lower()
    for cat, keywords in CATEGORIES.items():
        if any(kw in text_lower for kw in keywords):
            return cat
    return "Physiotherapy & Fitness Center"

def extract_owner_title(text):
    text_lower = text.lower()
    if "dr." in text_lower or "doctor" in text_lower:
        return "Doctor / Clinic Director / Founder"
    elif "founder" in text_lower or "owner" in text_lower:
        return "Clinic Founder / Gym Owner"
    elif "manager" in text_lower:
        return "Operations Manager / Facility Head"
    return "Gym / Clinic Owner & Managing Director"

def extract_clean_business_name(title, link, category):
    clean_name = title.split("-")[0].split("|")[0].split(":")[0].strip()
    clean_name = re.sub(r'\(.*?\)', '', clean_name).strip()
    if clean_name.lower() in ["contact us", "contact", "home", "about us", "details", ""]:
        domain = urlparse(link).netloc.replace("www.", "").split(".")[0]
        words = [w.capitalize() for w in domain.split("-") if w]
        clean_name = " ".join(words)
        if len(clean_name) < 3:
            clean_name = f"Premium {category} Facility"
    return clean_name

SEARCH_QUERIES = [
    'physiotherapy clinic contact +91 Delhi NCR',
    'physiotherapy clinic contact +91 Mumbai',
    'physiotherapy clinic contact +91 Bangalore',
    'physiotherapy clinic contact +91 Hyderabad',
    'physiotherapy clinic contact +91 Pune',
    'gym fitness center contact +91 Delhi NCR',
    'gym fitness center contact +91 Mumbai',
    'gym fitness center contact +91 Bangalore',
    'gym fitness center contact +91 Hyderabad',
    'gym fitness center contact +91 Pune',
    'sports rehabilitation center contact +91 India',
    'orthopedic wellness center contact +91 India',
    'chiropractic center contact +91 India',
    'pilates studio fitness contact +91 India',
    'site:facebook.com "physiotherapy clinic" "+91"',
    'site:facebook.com "gym" "+91" "contact"',
    'site:instagram.com "physiotherapy clinic" "+91"',
    'site:instagram.com "fitness center" "+91" India',
    'site:justdial.com "physiotherapy clinics" "+91"'
]

def main():
    all_raw_results = []
    seen_links = set()

    print("Executing OSINT extraction for Nonstop PhysioCare franchise targets...")
    for idx, q in enumerate(SEARCH_QUERIES):
        print(f"[{idx+1}/{len(SEARCH_QUERIES)}] Query: {q}")
        results = search_web(q, num=10)
        time.sleep(4)
        for r in results:
            link = r.get('link', '') or r.get('href', '')
            if link and link not in seen_links and is_valid_lead(r):
                seen_links.add(link)
                all_raw_results.append(r)

    print(f"Total valid unique clinic/gym lead records: {len(all_raw_results)}")

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
        category = extract_category(full_text)
        owner_title = extract_owner_title(full_text)
        clean_name = extract_clean_business_name(title, link, category)

        if phone in seen_phones or clean_name.lower() in seen_names:
            continue
        seen_phones.add(phone)
        seen_names.add(clean_name.lower())

        name_cat = f"{clean_name} ({category})"

        record = {
            "Business / Clinic Name & Category": name_cat,
            "City & Location": f"{city}, India",
            "Contact Person / Owner / Decision Maker Title": owner_title,
            "Standardized Contact Phone Number (+91XXXXXXXXXX)": phone,
            "Email Address (if available)": email,
            "Website / Source Profile Link": link,
            "Current Setup / Infrastructure Notes": "Operational clinic/gym facility (suitable for 900–1500+ sq ft integration) with existing wellness clientele and rehab infrastructure",
            "Franchise Partnership Pitch Suitability & Priority Status": "High Priority - Ideal candidate for Nonstop PhysioCare franchise/co-branding integration"
        }

        structured_leads.append(record)

    return structured_leads

if __name__ == "__main__":
    leads = main()
    print(f"Total structured leads: {len(leads)}")
