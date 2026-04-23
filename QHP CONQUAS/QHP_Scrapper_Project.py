"""
CONQUAS Score Scraper - BCA Quality Housing Portal
===================================================
Scrapes by Property Name category, extracting all 8 columns:
S/N, Project, CONQUAS Band, Project Developer, Developer,
Builder, Architect, Year

Setup (one-time):
    pip install playwright beautifulsoup4 pandas
    playwright install chromium

Run:
    python QHP_Scrapper.py

Output: conquas_scores.csv in the same folder
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import time

BASE_URL = "https://www.bca.gov.sg/quality-housing-portal/ConquasScore.aspx"


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
    """Parse the CONQUAS results table (gvProject) from page HTML.

    Extracts all 8 columns:
    S/N, Project, CONQUAS Band, Project Developer, Developer,
    Builder, Architect, Year
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="ctl00_MainContent_gvProject")
    if not table:
        return []

    results = []
    for row in table.find_all("tr")[2:]:  # skip 2 header rows
        cols = row.find_all("td")
        if len(cols) < 8:
            continue

        sn               = cols[0].get_text(strip=True)
        project          = cols[1].get_text(strip=True)
        band             = cols[2].get_text(strip=True)
        project_developer = cols[3].get_text(separator=" / ", strip=True)
        developer        = cols[4].get_text(separator=" / ", strip=True)
        builder          = cols[5].get_text(separator=" / ", strip=True)
        architect        = cols[6].get_text(separator=" / ", strip=True)
        year             = cols[7].get_text(strip=True)

        if project:
            results.append({
                "S/N": sn,
                "Project": project,
                "CONQUAS Band": band,
                "Project Developer": project_developer,
                "Developer": developer,
                "Builder": builder,
                "Architect": architect,
                "Year": year,
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

        # Step 1: Load the page
        page.goto(BASE_URL, wait_until="networkidle", timeout=60000)

        # Step 2: Select "Property Name" category (triggers postback to load property list)
        page.select_option("#ctl00_MainContent_ddlCategory", "Property Name")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # Step 3: Read all property names from the dropdown
        properties = page.evaluate("""
            () => {
                var sel = document.getElementById('ctl00_MainContent_txtNameOne');
                return Array.from(sel.options)
                    .map(o => o.value.trim())
                    .filter(v => v !== '');
            }
        """)
        total = len(properties)
        print(f"Found {total} properties.\n")

        # Step 4: Loop through each property
        for i, prop in enumerate(properties):
            try:
                print(f"[{i+1}/{total}] {prop}")

                # Set value via JS to bypass Chosen.js visibility restriction
                chosen_select(page, "ctl00_MainContent_txtNameOne", prop)
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
                        print(f"   Band: {r['CONQUAS Band']} | Builder: {r['Builder']}")
                else:
                    print("   - No data found")
                    all_data.append({
                        "S/N": "",
                        "Project": prop,
                        "CONQUAS Band": "No Data",
                        "Project Developer": "",
                        "Developer": "",
                        "Builder": "",
                        "Architect": "",
                        "Year": "",
                    })

            except Exception as e:
                print(f"   ERROR: {e}")
                all_data.append({
                    "S/N": "",
                    "Project": prop,
                    "CONQUAS Band": "Error",
                    "Project Developer": "",
                    "Developer": "",
                    "Builder": "",
                    "Architect": "",
                    "Year": str(e),
                })

        browser.close()

    # Save results
    df = pd.DataFrame(all_data)
    df.to_csv("conquas_scores_full.csv", index=False, encoding="utf-8-sig")

    print("\n" + "=" * 60)
    print(f"Done! {len(df)} records saved to conquas_scores.csv")
    print("=" * 60)
    print("\nBand Distribution:")
    print(df["CONQUAS Band"].value_counts().to_string())

    return df


if __name__ == "__main__":
    scrape_all()