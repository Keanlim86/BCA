"""
CONQUAS Score Scraper - BCA Quality Housing Portal
===================================================
Setup (one-time):
    pip install playwright beautifulsoup4 pandas
    playwright install chromium

Run:
    python conquas_scraper.py

Output: conquas_scores.csv in the same folder
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import time

BASE_URL = "https://www.bca.gov.sg/quality-housing-portal/ConquasScore.aspx?cat=1"


def chosen_select(page, select_id, value):
    """
    Bypass Chosen.js hidden select by setting value directly via JS
    and firing the change event to trigger ASP.NET postback.
    """
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


def parse_results(html):
    """Parse the CONQUAS results table from page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="ctl00_MainContent_gvAdmin")
    if not table:
        return []

    results = []
    for row in table.find_all("tr")[2:]:  # skip 2 header rows
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        name_tag = cols[0].find("a")
        name = name_tag.get_text(strip=True) if name_tag else cols[0].get_text(strip=True)

        band_tag = cols[1].find("span")
        band = band_tag.get_text(strip=True) if band_tag else cols[1].get_text(strip=True)

        proj_tag = cols[2].find("a")
        projects = proj_tag.get_text(strip=True) if proj_tag else cols[2].get_text(strip=True)

        if name:
            results.append({
                "Developer": name,
                "CONQUAS Band": band,
                "Projects & Bands": projects
            })
    return results


def scrape_all():
    all_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("=" * 60)
        print("CONQUAS Scraper - BCA Quality Housing Portal")
        print("=" * 60)
        print("Loading page...")

        # Step 1: Load the initial page
        page.goto(BASE_URL, wait_until="networkidle", timeout=60000)

        # Step 2: Read all developer names BEFORE triggering any postback
        # Use JS to extract values from the hidden native <select>
        developers = page.evaluate("""
            () => {
                var sel = document.getElementById('ctl00_MainContent_txtNameOne');
                return Array.from(sel.options)
                    .map(o => o.value.trim())
                    .filter(v => v !== '');
            }
        """)
        total = len(developers)
        print(f"Found {total} developers.\n")

        # Step 3: Now switch to Developer category (triggers postback)
        page.select_option("#ctl00_MainContent_ddlCategory", "Developer")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # Step 4: Loop through each developer
        for i, dev in enumerate(developers):
            try:
                print(f"[{i+1}/{total}] {dev}")

                # Set value via JS to bypass Chosen.js visibility restriction
                chosen_select(page, "ctl00_MainContent_txtNameOne", dev)
                time.sleep(0.3)

                # Click Search and wait for postback to complete
                page.click("#ctl00_MainContent_btnCompare")
                page.wait_for_load_state("networkidle")
                time.sleep(0.5)

                # Parse table from resulting page
                rows = parse_results(page.content())

                if rows:
                    all_data.extend(rows)
                    for r in rows:
                        print(f"   Band: {r['CONQUAS Band']} | {r['Projects & Bands']}")
                else:
                    print("   - No data found")
                    all_data.append({
                        "Developer": dev,
                        "CONQUAS Band": "No Data",
                        "Projects & Bands": ""
                    })

            except Exception as e:
                print(f"   ERROR: {e}")
                all_data.append({
                    "Developer": dev,
                    "CONQUAS Band": "Error",
                    "Projects & Bands": str(e)
                })

        browser.close()

    # Save results
    df = pd.DataFrame(all_data)
    df.drop_duplicates(inplace=True)
    df.to_csv("conquas_scores.csv", index=False, encoding="utf-8-sig")

    print("\n" + "=" * 60)
    print(f"Done! {len(df)} records saved to conquas_scores.csv")
    print("=" * 60)
    print("\nBand Distribution:")
    print(df["CONQUAS Band"].value_counts().to_string())

    return df


if __name__ == "__main__":
    scrape_all()