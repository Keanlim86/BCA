"""
CONQUAS Scraper - DEBUG VERSION
================================
Run this once to print all label IDs found in the first result row.
Paste the output back to Claude so the real scraper can be fixed.

Run:
    python QHP_Scrapper.py
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

BASE_URL = "https://www.bca.gov.sg/quality-housing-portal/ConquasScore.aspx"


def chosen_select(page, select_id, value):
    page.evaluate("""
        ([id, val]) => {
            var sel = document.getElementById(id);
            sel.value = val;
            if (window.jQuery) {
                jQuery(sel).trigger('change');
            } else {
                sel.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
    """, [select_id, value])


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("Loading page...")
    page.goto(BASE_URL, wait_until="networkidle", timeout=60000)

    # Select Property Name category
    page.select_option("#ctl00_MainContent_ddlCategory", "Property Name")
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    # Get first property
    properties = page.evaluate("""
        () => {
            var sel = document.getElementById('ctl00_MainContent_txtNameOne');
            return Array.from(sel.options)
                .map(o => o.value.trim())
                .filter(v => v !== '');
        }
    """)
    #first_prop = properties[0]
    first_prop = "10 Evelyn Road"
    print(f"Searching for: {first_prop}\n")

    # Search for first property
    chosen_select(page, "ctl00_MainContent_txtNameOne", first_prop)
    time.sleep(0.3)
    page.click("#ctl00_MainContent_btnCompare")
    page.wait_for_load_state("networkidle")
    time.sleep(0.5)

    # Parse the HTML
    soup = BeautifulSoup(page.content(), "html.parser")
    table = soup.find("table", id="ctl00_MainContent_gvProject")

    if not table:
        print("ERROR: Could not find table with id='ctl00_MainContent_gvProject'")
        print("\nAll table IDs on page:")
        for t in soup.find_all("table"):
            print(f"  id='{t.get('id', 'NO ID')}'")
    else:
        print("Found table! Printing all IDs in first data row:\n")
        rows = table.find_all("tr")
        # Find first data row (skip headers)
        for row in rows:
            all_ids = [(tag.name, tag.get("id"), tag.get_text(strip=True)[:50])
                       for tag in row.find_all(True) if tag.get("id")]
            if all_ids:
                print(f"Row with {len(all_ids)} IDs:")
                for tag_name, tag_id, tag_text in all_ids:
                    print(f"  <{tag_name}> id='{tag_id}' text='{tag_text}'")
                print()
                break  # only show first data row

    browser.close()