"""
SCAL Members Directory Scraper
================================
Scrapes all members from https://www.scal.com.sg/memberlistings
by calling the underlying AJAX API endpoint directly.

Requirements:
    pip install requests pandas openpyxl

Usage:
    python scal_members_scraper.py
"""

import requests
import pandas as pd
import time
import json

BASE_URL = "https://www.scal.com.sg"
API_URL = f"{BASE_URL}/helper/searchmembers"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Referer": f"{BASE_URL}/memberlistings",
    "X-Requested-With": "XMLHttpRequest",
}

PAGE_SIZE = 10  # The site loads 10 members per page


def fetch_page(page: int, company_name="", member_type="", regnhead="", workhead=""):
    """Fetch a single page of members from the API."""
    params = {
        "index": page,
        "companyName": company_name,
        "memberType": member_type,
        "regnhead": regnhead,
        "workhead": workhead,
    }
    response = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return response.json()


def scrape_all_members(delay: float = 0.5):
    """
    Scrape all members across all pages.
    
    Args:
        delay: Seconds to wait between requests (be polite to the server)
    
    Returns:
        List of member dicts with keys: id, name, slug, url
    """
    print("Fetching first page to get total count...")
    first = fetch_page(1)

    if not first.get("success"):
        raise RuntimeError(f"API returned failure: {first}")

    total = first["count"]
    total_pages = -(-total // PAGE_SIZE)  # Ceiling division
    print(f"Total members: {total} | Total pages: {total_pages}")

    all_members = []

    # Add members from first page
    for item in first["data"]:
        all_members.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "slug": item.get("slug"),
            "url": f"{BASE_URL}/memberlisting-details/{item.get('id')}-{item.get('slug')}",
        })

    # Fetch remaining pages
    for page in range(2, total_pages + 1):
        print(f"  Fetching page {page}/{total_pages}...", end="\r")
        time.sleep(delay)

        data = fetch_page(page)
        if not data.get("success"):
            print(f"\nWarning: page {page} returned failure, skipping.")
            continue

        for item in data["data"]:
            all_members.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "slug": item.get("slug"),
                "url": f"{BASE_URL}/memberlisting-details/{item.get('id')}-{item.get('slug')}",
            })

    print(f"\nDone! Collected {len(all_members)} members.")
    return all_members


def save_results(members: list):
    """Save results to both CSV and Excel."""
    df = pd.DataFrame(members)

    csv_path = "scal_members.csv"
    xlsx_path = "scal_members.xlsx"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False)

    print(f"Saved {len(df)} members to:")
    print(f"  CSV  → {csv_path}")
    print(f"  XLSX → {xlsx_path}")

    return df


if __name__ == "__main__":
    members = scrape_all_members(delay=0.5)
    df = save_results(members)

    # Preview
    print("\nFirst 10 members:")
    print(df.head(10).to_string(index=False))
