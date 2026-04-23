from playwright.sync_api import sync_playwright
import csv, time, os, requests
from scraped_filenames import already_scraped_filenames

SCRAPED_LOG = "scraped_filenames.py"

def save_scraped_filename(filename):
    """Append a newly downloaded filename to the log file."""
    with open(SCRAPED_LOG, "r", encoding="utf-8") as f:
        content = f.read()

    new_entry = f'    "{filename}",\n'
    updated = content.replace("]\n", new_entry + "]\n", 1)

    with open(SCRAPED_LOG, "w", encoding="utf-8") as f:
        f.write(updated)

def scrape_bca_circulars():
    results = []

    # ── User prompts ──────────────────────────────────────────────
    download_pdfs = input("Do you want to download the PDF files? (y/n): ").strip().lower() == 'y'

    year_filter = None
    if download_pdfs:
        year_input = input("Which year to download PDFs for? (e.g. 2025, or press Enter for ALL): ").strip()
        year_filter = year_input if year_input.isdigit() and len(year_input) == 4 else None
        if year_filter:
            print(f"Will download PDFs for year: {year_filter}")
        else:
            print("Will download PDFs for ALL years.")

        pdf_folder = f"BCA_Circulars_PDFs_{year_filter or 'ALL'}"
        os.makedirs(pdf_folder, exist_ok=True)

        already_scraped = set(already_scraped_filenames)
        print(f"Found {len(already_scraped)} already-scraped filenames in {SCRAPED_LOG}.")
    # ─────────────────────────────────────────────────────────────

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-SG",
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        page = context.new_page()
        page.goto("https://www1.bca.gov.sg/resources/circulars/")
        page.wait_for_selector("a[href*='isomer-user-content']", timeout=20000)

        page_num = 1

        while True:
            print(f"Scraping page {page_num}...")
            page.wait_for_selector("a[href*='isomer-user-content']", timeout=10000)

            first_link = page.locator("a[href*='isomer-user-content']").first.get_attribute("href")

            items = page.evaluate("""
                () => {
                    const results = [];
                    document.querySelectorAll("a[href*='isomer-user-content']").forEach(link => {
                        let container = link;
                        for (let i = 0; i < 6; i++) {
                            if (container.innerText && /\\d{1,2}\\s+\\w+\\s+20\\d{2}/.test(container.innerText)) break;
                            container = container.parentElement || container;
                        }

                        const fullText = container.innerText || '';
                        const dateMatch = fullText.match(/\\d{1,2}\\s+\\w+\\s+20\\d{2}/);
                        const date = dateMatch ? dateMatch[0] : '';
                        const yearMatch = date.match(/20\\d{2}/);
                        const year = yearMatch ? yearMatch[0] : '';

                        const titleEl = link.querySelector('h3, h2, h4');
                        const title = (titleEl?.innerText || link.innerText).trim();

                        const url = link.href;
                        const urlPath = new URL(url).pathname;
                        const filename = decodeURIComponent(urlPath.split('/').pop() || '');

                        results.push({ year, date, title, filename, url });
                    });
                    return results;
                }
            """)

            results.extend(items)
            print(f"  Got {len(items)} items. Total: {len(results)}")

            next_btn = page.locator("button[aria-label='Go to next page']")
            if next_btn.count() == 0 or next_btn.get_attribute("disabled") is not None:
                print("Reached last page. Done.")
                break

            next_btn.click()
            page_num += 1

            page.wait_for_function(
                f"""() => {{
                    const links = document.querySelectorAll("a[href*='isomer-user-content']");
                    return links.length > 0 && links[0].href !== "{first_link}";
                }}""",
                timeout=10000
            )
            time.sleep(0.5)

        browser.close()

    # Deduplicate by URL
    seen, unique = set(), []
    for r in results:
        if r['url'] not in seen:
            seen.add(r['url'])
            unique.append(r)

    print(f"\nDone scraping! {len(unique)} unique circulars found.")

    # ── Save CSV (always, all records) ────────────────────────────
    with open("bca_circulars.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "date", "title", "filename", "url"])
        writer.writeheader()
        writer.writerows(unique)
    print("Saved full list to bca_circulars.csv")

    # ── Download PDFs ─────────────────────────────────────────────
    if download_pdfs:
        to_download = [
            r for r in unique
            if (year_filter is None or r['year'] == year_filter)
            and r['filename'] not in already_scraped
        ]

        skipped = len([
            r for r in unique
            if (year_filter is None or r['year'] == year_filter)
            and r['filename'] in already_scraped
        ])

        print(f"\nPDFs to download : {len(to_download)}")
        print(f"Skipped (already in {SCRAPED_LOG}): {skipped}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        for i, item in enumerate(to_download, 1):
            filename = item['filename']
            filepath = os.path.join(pdf_folder, filename)

            try:
                r = requests.get(item['url'], headers=headers, timeout=30)
                if r.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(r.content)
                    save_scraped_filename(filename)
                    print(f"  [{i}/{len(to_download)}] Downloaded: {filename}")
                else:
                    print(f"  [{i}/{len(to_download)}] Failed ({r.status_code}): {filename}")
            except Exception as e:
                print(f"  [{i}/{len(to_download)}] Error: {filename} — {e}")

            time.sleep(0.3)

        print(f"\nPDF download complete. Files saved to '{pdf_folder}/'")
        print(f"Filenames logged to '{SCRAPED_LOG}'")

scrape_bca_circulars()