import requests
import yfinance as yf
import re
from bs4 import BeautifulSoup
import time

# SEC requires valid headers or it blocks you
HEADERS = {
    "User-Agent": "Ahmed Yar ahmed@limeox.com",   # <-- use your real email here
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov"
}

def safe_get_json(url):
    """Fetch JSON with retry & SEC bypass handling"""
    for attempt in range(5):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"HTTP {resp.status_code}, retrying...")
        except Exception as e:
            print(f"Error: {e}, retrying...")

        time.sleep(2)

    print("❌ SEC blocked all attempts.")
    return None


def get_company_cik(ticker):
    url = "https://www.sec.gov/files/company_tickers.json"
    data = safe_get_json(url)

    if data:
        for _, v in data.items():
            if v["ticker"].lower() == ticker.lower():
                return str(v["cik_str"]).zfill(10)

    print("⚠️ JSON file failed. Using fallback lookup...")

    return get_cik_fallback(ticker)


def get_cik_fallback(ticker):
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={ticker}&owner=exclude&action=getcompany"
    resp = requests.get(url, headers=HEADERS).text
    match = re.search(r"CIK=(\d+)", resp)
    if match:
        cik = match.group(1).zfill(10)
        print(f"✔ Fallback CIK found: {cik}")
        return cik
    return None


def get_latest_10k(cik):
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = safe_get_json(url)

    if not data:
        return None

    forms = data["filings"]["recent"]["form"]
    acc = data["filings"]["recent"]["accessionNumber"]

    for i, f in enumerate(forms):
        if f == "10-K":
            accession = acc[i].replace("-", "")
            return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/index.json"

    return None


def extract_text_from_10k(index_url):
    data = safe_get_json(index_url)
    if not data:
        return ""

    for f in data["directory"]["item"]:
        if f["name"].endswith(".htm"):
            file_url = index_url.replace("index.json", f["name"])
            html = requests.get(file_url, headers=HEADERS).text
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text(separator=" ")

    return ""


def extract_matches(text):
    patterns = {
        "customers": r"customer.{0,300}",
        "suppliers": r"supplier.{0,300}",
        "investments": r"investment.{0,300}",
        "concentration": r"concentration.{0,300}",
        "risks": r"risk.{0,300}"
    }

    results = {}
    for key, pattern in patterns.items():
        found = re.findall(pattern, text, flags=re.IGNORECASE)
        results[key] = list(set(found))[:8]

    return results


def get_basic_financials(ticker):
    stock = yf.Ticker(ticker)
    return {
        "name": stock.info.get("longName"),
        "sector": stock.info.get("sector"),
        "industry": stock.info.get("industry"),
        "website": stock.info.get("website"),
        "marketCap": stock.info.get("marketCap"),
        "revenue": stock.info.get("totalRevenue"),
        "grossProfits": stock.info.get("grossProfits")
    }


def run(ticker):
    print(f"\n🔍 Fetching data for: {ticker}\n")

    cik = get_company_cik(ticker)
    if not cik:
        print("❌ Could not find CIK.")
        return

    print(f"✔ CIK: {cik}")

    print("\n=== 📊 BASIC FINANCIALS ===")
    print(get_basic_financials(ticker))

    print("\n=== 📄 SEC 10-K Extraction ===")
    index_url = get_latest_10k(cik)

    if not index_url:
        print("❌ No 10-K found.")
        return

    print(f"✔ 10-K index file: {index_url}")

    text = extract_text_from_10k(index_url)
    extracted = extract_matches(text)

    print("\n=== 🧩 CUSTOMERS ===")
    print(extracted["customers"])

    print("\n=== 🔧 SUPPLIERS ===")
    print(extracted["suppliers"])

    print("\n=== 💸 INVESTMENTS ===")
    print(extracted["investments"])

    print("\n=== 🎯 REVENUE CONCENTRATION ===")
    print(extracted["concentration"])

    print("\n=== ⚠️ RISK FACTORS ===")
    print(extracted["risks"])


ticker = input("Enter stock ticker (e.g., NVDA): ")
run(ticker)
