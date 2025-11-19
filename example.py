import re
import yfinance as yf
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ------------------------------- #
#  GET CIK USING PLAYWRIGHT
# ------------------------------- #
def get_cik(play, ticker):
    browser = play.chromium.launch(headless=True)
    page = browser.new_page()

    url = f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={ticker}&owner=exclude&action=getcompany"
    page.goto(url, timeout=60000)

    text = page.locator("span.companyName").inner_text()

    browser.close()

    match = re.search(r"CIK\s*([0-9]+)", text)
    if match:
        return match.group(1).zfill(10)
    return None


# ------------------------------- #
#  FIND LATEST 10-K DOCUMENT
# ------------------------------- #
def get_latest_10k_url(play, cik):
    browser = play.chromium.launch(headless=True)
    page = browser.new_page()

    url = f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={cik}&type=10-K&owner=exclude&count=100"
    page.goto(url, timeout=60000)

    link = page.locator("a[href*='Archives'][href$='.htm']").first
    filing_url = link.get_attribute("href")

    browser.close()

    if filing_url:
        return "https://www.sec.gov" + filing_url
    return None


# ------------------------------- #
#  DOWNLOAD THE 10-K HTML PAGE
# ------------------------------- #
def extract_10k_html(play, filing_url):
    browser = play.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(filing_url, timeout=120000)
    html = page.content()

    browser.close()
    return html


# ------------------------------- #
#  EXTRACT SECTIONS
# ------------------------------- #
def extract_sections(text):
    patterns = {
        "customers": r"customer.{0,350}",
        "suppliers": r"supplier.{0,350}",
        "investments": r"investment.{0,350}",
        "concentration": r"concentration.{0,350}",
        "risks": r"risk.{0,350}",
    }

    results = {}
    for key, patt in patterns.items():
        found = re.findall(patt, text, flags=re.IGNORECASE)
        results[key] = list(set(found))[:10]

    return results


# ------------------------------- #
#  BASIC FINANCIALS
# ------------------------------- #
def get_basic_financials(ticker):
    stock = yf.Ticker(ticker)
    return {
        "name": stock.info.get("longName"),
        "sector": stock.info.get("sector"),
        "industry": stock.info.get("industry"),
        "website": stock.info.get("website"),
        "marketCap": stock.info.get("marketCap"),
        "revenue": stock.info.get("totalRevenue"),
        "grossProfits": stock.info.get("grossProfits"),
    }


# ------------------------------- #
#  RUN EVERYTHING
# ------------------------------- #
def run(ticker):
    print(f"\n🔍 Fetching data for: {ticker}\n")

    with sync_playwright() as play:

        print("⏳ Getting CIK...")
        cik = get_cik(play, ticker)
        if not cik:
            print("❌ Could not find CIK")
            return

        print(f"✔ CIK: {cik}")

        print("\n=== 📊 BASIC FINANCIALS ===")
        print(get_basic_financials(ticker))

        print("\n⏳ Finding latest 10-K filing...")
        filing_url = get_latest_10k_url(play, cik)
        if not filing_url:
            print("❌ No 10-K found")
            return

        print(f"✔ 10-K URL: {filing_url}")

        print("\n⏳ Downloading 10-K HTML...")
        html = extract_10k_html(play, filing_url)

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    print("\n⏳ Extracting sections...")
    extracted = extract_sections(text)

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


# Run script
ticker = input("Enter stock ticker (e.g. NVDA): ")
run(ticker)
