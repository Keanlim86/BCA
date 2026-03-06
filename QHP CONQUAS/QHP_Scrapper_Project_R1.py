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
    """
    Parse the CONQUAS results table (gvProject) from page HTML.

    Confirmed label IDs (pattern: ctl00_MainContent_gvProject_ctlXX_<field>):
      lblSN, lblProjectShortName, lblConquasBand, lblProjectDeveloper,
      lnkParentDeveloper1/2/3, lnkBuilder1/2/3, lblArchitect1/2/3, lblFY
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="ctl00_MainContent_gvProject")
    if not table:
        return []

    results = []
    for row in table.find_all("tr"):
        # Identify data rows by presence of lblSN
        sn_tag = row.find(id=lambda x: x and "lblSN" in x)
        if not sn_tag:
            continue

        def find_tag(field):
            """Find a single field by its exact field name anywhere in the id."""
            tag = row.find(id=lambda x: x and x.endswith(field))
            return tag.get_text(strip=True) if tag else ""

        def find_multi(field, count=3):
            """Find up to `count` numbered fields e.g. lnkBuilder1, lnkBuilder2..."""
            values = []
            for n in range(1, count + 1):
                tag = row.find(id=lambda x: x and x.endswith(f"{field}{n}"))
                if tag:
                    text = tag.get_text(strip=True)
                    if text:
                        values.append(text)
            return " / ".join(values)

        sn          = find_tag("lblSN")
        project     = find_tag("lblProjectShortName")
        band        = find_tag("lblConquasBand")
        project_dev = find_tag("lblProjectDeveloper")
        developer   = find_multi("lnkParentDeveloper")   # lnkParentDeveloper1/2/3
        builder     = find_multi("lnkBuilder")           # lnkBuilder1/2/3
        architect   = find_multi("lblArchitect")         # lblArchitect1/2/3
        year        = find_tag("lblFY")

        if project:
            results.append({
                "S/N":               sn,
                "Project":           project,
                "CONQUAS Band":      band,
                "Project Developer": project_dev,
                "Developer":         developer,
                "Builder":           builder,
                "Architect":         architect,
                "Year":              year,
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

        # Step 2: Select "Property Name" category
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

                chosen_select(page, "ctl00_MainContent_txtNameOne", prop)
                time.sleep(0.3)

                page.click("#ctl00_MainContent_btnCompare")
                page.wait_for_load_state("networkidle")
                time.sleep(0.5)

                rows = parse_results(page.content())

                if rows:
                    all_data.extend(rows)
                    for r in rows:
                        print(f"   Band: {r['CONQUAS Band']} | Dev: {r['Project Developer']} | Parent: {r['Developer']} | Builder: {r['Builder']} | Arch: {r['Architect']} | Year: {r['Year']}")
                else:
                    print("   - No data found")
                    all_data.append({
                        "S/N": "", "Project": prop, "CONQUAS Band": "No Data",
                        "Project Developer": "", "Developer": "",
                        "Builder": "", "Architect": "", "Year": "",
                    })

            except Exception as e:
                print(f"   ERROR: {e}")
                all_data.append({
                    "S/N": "", "Project": prop, "CONQUAS Band": "Error",
                    "Project Developer": "", "Developer": "",
                    "Builder": "", "Architect": "", "Year": str(e),
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