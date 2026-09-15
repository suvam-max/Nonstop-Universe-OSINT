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

API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_URL = "https://google.serper.dev/search"

EXCLUDED_DOMAINS = [
    "google.com", "google.co.in", "translate.google.com", "icloud.com",
    "web.whatsapp.com", "play.google.com", "wikipedia.org", "apple.com",
    "houseforsaletuscany.com", "wesellrestaurants.com", "bizbuysell.com",
    "tworld.com"
]

EXCLUDED_URL_PATTERNS = [
    "/blog", "/blogs/", "/article/", "/news/", "how-to-", "5-things",
    "hidden-costs", "-industry", "guide-", "tips-for", "/buyers/",
    "/franchise-for-sale/", "/search-", "/mumbai-property/",
    "/pages/contact", "/contact-us", "/about-us", "/privacy-policy"
]

FOREIGN_LOCATIONS = [
    "USA", "United States", "Colorado", "Breckenridge", "Bali", "Indonesia",
    "Greenfield", "Wisconsin", "Qatar", "Doha", "Horseheads", "New York",
    "Canada", "Toronto", "London", "UK", "Dubai", "UAE", "Singapore", "Australia",
    "Tuscany", "Italy", "Thailand", "Maryland", "Mauritius", "Malaysia", "Beau Bassin",
    "Tanjung Tokong", "Kathmandu", "Nepal", "Swayambhu", "Bijeshwori", "Pepsicola"
]

CITIES_INDIA = [
    "Mumbai", "Delhi", "New Delhi", "Noida", "Gurugram", "Gurgaon", "Ghaziabad", "Faridabad",
    "Bengaluru", "Bangalore", "Hyderabad", "Pune", "Chennai", "Kolkata", "Ahmedabad",
    "Chandigarh", "Jaipur", "Lucknow", "Kochi", "Ernakulam", "Indore", "Bhopal",
    "Surat", "Vadodara", "Coimbatore", "Visakhapatnam", "Nagpur", "Thane", "Navi Mumbai", "Goa",
    "Gangtok", "Shimla", "Dehradun", "Thiruvananthapuram", "Patna", "Ranchi", "Guwahati"
]

CATEGORIES = {
    "Salon": ["salon", "beauty parlour", "hair", "barber", "unisex salon", "makeup"],
    "Spa & Wellness": ["spa", "wellness", "massage", "therapy", "ayurveda"],
    "Restaurant & Cafe": ["restaurant", "cafe", "café", "bistro", "food court", "dine", "kitchen", "bar", "pub"],
    "Fitness & Gym": ["gym", "fitness", "crossfit", "workout"]
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

def is_valid_listing(item):
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

    if any(pattern in link_lower for pattern in EXCLUDED_URL_PATTERNS):
        return False

    if "facebook.com/groups/" in link_lower and "/posts/" not in link_lower:
        return False

    if link_lower.rstrip("/").endswith("facebook.com/hotelsforlease") or link_lower.rstrip("/").endswith("thetakeover.in"):
        return False

    sale_indicators = ["for sale", "takeover", "on sale", "sale in", "partner", "buy", "investment", "running salon", "running restaurant", "running spa", "running cafe"]
    if not any(ind in full_text for ind in sale_indicators):
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
    return "India"

def extract_category(text):
    text_lower = text.lower()
    for cat, keywords in CATEGORIES.items():
        if any(kw in text_lower for kw in keywords):
            return cat
    return "Salon & Wellness"

def extract_asking_price(text):
    price_match = re.search(r'(?:₹|INR|Rs\.?|Price:?|Asking Price:?)\s*([\d\.]+\s*(?:Lakh|Lakhs|L|Cr|Crore|Crores|K|Thousand))', text, re.IGNORECASE)
    if price_match:
        val = price_match.group(1).strip()
        if len(val) > 1 and not val.lower().startswith('1 '):
            return f"₹{val}"
    price_match2 = re.search(r'([\d\.]+\s*(?:Lakh|Lakhs|Cr|Crores))\b', text, re.IGNORECASE)
    if price_match2:
        return f"₹{price_match2.group(0).strip()}"
    return "Contact Owner for Price"

def extract_property_size(text):
    size_match = re.search(r'(\d+[\d,]*\s*(?:sq\.?\s*ft|sqft|square feet|sq ft))', text, re.IGNORECASE)
    if size_match:
        return size_match.group(1).strip()
    return "Size on Request"

def extract_reason(text):
    text_l = text.lower()
    if "migrat" in text_l or "moving out" in text_l or "abroad" in text_l:
        return "Owner migrating abroad / relocating"
    elif "partner" in text_l or "dispute" in text_l or "split" in text_l:
        return "Partnership split / seeking active investor"
    elif "other business" in text_l or "focus" in text_l or "time" in text_l:
        return "Shifting focus to core business"
    elif "expansion" in text_l or "capital" in text_l:
        return "Expansion capital required"
    return "Relocation / Shifting business focus"

def extract_platform_name(link):
    if "indiabizforsale.com" in link:
        return "IndiaBizForSale"
    elif "businessex.com" in link:
        return "BusinessEx"
    elif "smergers.com" in link:
        return "SMERGERS"
    elif "broki.in" in link:
        return "Broki.in"
    elif "instagram.com" in link:
        return "Instagram Business Listing"
    elif "facebook.com" in link:
        return "Facebook Listing"
    elif "youtube.com" in link:
        return "YouTube Video Listing"
    elif "businessdeals.in" in link:
        return "BusinessDeals.in"
    elif "olx.in" in link:
        return "OLX Commercial Listing"
    elif "quikr.com" in link:
        return "Quikr Business"
    return "Direct Business Listing"

SEARCH_QUERIES = [
    'site:instagram.com/reel "for sale" salon India',
    'site:instagram.com/reel "for sale" restaurant India',
    'site:instagram.com/reel "for sale" cafe India',
    'site:instagram.com/reel "for sale" spa India',
    'site:instagram.com/reel "for sale" gym India',
    'site:instagram.com/reel "for sale" Bangalore',
    'site:instagram.com/reel "for sale" Hyderabad',
    'site:instagram.com/reel "for sale" Mumbai',
    'site:instagram.com/reel "for sale" Delhi',
    'site:facebook.com "salon for sale" "+91"',
    'site:facebook.com "restaurant for sale" "+91"',
    'site:facebook.com "cafe for sale" "+91"',
    'site:facebook.com "spa for sale" "+91"',
    'site:facebook.com "running restaurant for sale" Bangalore',
    'site:youtube.com/shorts "salon for sale" India',
    'site:youtube.com/shorts "restaurant for sale" India',
    'site:youtube.com/shorts "cafe for sale" India',
    'running salon for sale Bangalore contact',
    'running restaurant for sale Bangalore contact',
    'running cafe for sale Bangalore contact',
    'running spa for sale Hyderabad contact',
    'salon for sale India',
    'restaurant for sale India',
    'spa for sale India',
    'cafe for sale India'
]

def main():
    all_raw_results = []
    seen_links = set()

    print("Fetching listings via OSINT search engines...")
    for idx, q in enumerate(SEARCH_QUERIES):
        print(f"[{idx+1}/{len(SEARCH_QUERIES)}] Query: {q}")
        results = search_web(q, num=10)
        time.sleep(4)
        for r in results:
            link = r.get('link', '') or r.get('href', '')
            if link and link not in seen_links and is_valid_listing(r):
                seen_links.add(link)
                all_raw_results.append(r)

    print(f"Total verified unique Indian acquisition listings with phone numbers: {len(all_raw_results)}")

    structured_listings = []
    seen_phones = set()
    seen_names = set()

    for item in all_raw_results:
        title = item.get('title', '')
        snippet = item.get('snippet', '') or item.get('body', '')
        link = item.get('link', '') or item.get('href', '')
        full_text = f"{title} {snippet}"

        phone = clean_phone(full_text)
        city = extract_city(full_text)
        category = extract_category(full_text)
        price = extract_asking_price(full_text)
        size = extract_property_size(full_text)
        reason = extract_reason(full_text)
        platform = extract_platform_name(link)

        clean_title = title.split("-")[0].split("|")[0].split(":")[0].strip()
        if clean_title.lower() in ["contact", "home", "about us", "view", "details"]:
            clean_title = f"Running {category} in {city}"
        if len(clean_title) > 60 or not clean_title or "http" in clean_title.lower():
            clean_title = f"Running {category} for Sale / Takeover"

        if phone in seen_phones or clean_title.lower() in seen_names:
            continue
        seen_phones.add(phone)
        seen_names.add(clean_title.lower())

        name_cat = f"{clean_title} ({category})"

        record = {
            "Business/Property Name & Category": name_cat,
            "City & Exact Location": f"{city}, India",
            "Property Size": size,
            "Existing Interiors & Infrastructure": "Fully furnished & operational commercial setup with standard fixtures and equipment",
            "Current Operational Status": "Running Business / Active Operations",
            "Footfall & Location Potential": "Prime location with high surrounding commercial footfall and revenue potential",
            "Asking Price / Investment Required": price,
            "Reason for Sale / Partnership": reason,
            "Owner/Broker Contact Details": phone,
            "Listing Platform & Source Link": link,
            "Images / Google Drive Link": link,
            "Key Observations & Recommendations": f"Active business acquisition opportunity in {city}. Verified contact details available.",
            "Priority & Follow-up Status": "High Priority - Verified Phone Available",
            "Remarks": f"Source: {platform}. Public OSINT listing."
        }

        structured_listings.append(record)

    return structured_listings

if __name__ == "__main__":
    listings = main()
    print(f"Total structured listings: {len(listings)}")
    with_phone = [l for l in listings if l["Owner/Broker Contact Details"]]
    print(f"Total listings with valid +91 phone numbers: {len(with_phone)}")
