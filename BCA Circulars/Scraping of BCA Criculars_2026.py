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

        # ── Discover total page count ─────────────────────────────
        page.goto("https://www1.bca.gov.sg/resources/circulars/")
        page.wait_for_selector("a[href*='isomer-user-content']", timeout=20000)
        page.wait_for_load_state('networkidle', timeout=15000)

        total_pages = page.evaluate("""
            () => {
                let maxPage = 1;
                document.querySelectorAll('button').forEach(btn => {
                    const n = parseInt((btn.textContent || '').trim());
                    if (!isNaN(n) && n > maxPage) maxPage = n;
                });
                return maxPage;
            }
        """)
        print(f"Total pages detected: {total_pages}")
        # ─────────────────────────────────────────────────────────

        JS_EXTRACT = """
            () => {
                const results = [];

                // Older circulars link to BCA webpage slugs or go.gov.sg short links
                // instead of isomer-user-content PDFs — capture all five patterns.
                // go.gov.sg is restricted to bca-* paths to exclude footer links
                // like go.gov.sg/report-vulnerability.
                for (const link of document.querySelectorAll('a[href]')) {
                    const href = link.href || '';

                    const isIsomer  = href.includes('isomer-user-content');
                    const isBcaPage = href.includes('www1.bca.gov.sg/resources/circulars/');
                    const isGoGovSg = /go\\.gov\\.sg\\/bca/i.test(href);
                    const isCorenet = href.includes('corenet.gov.sg');
                    const isMOM     = href.includes('www.mom.gov.sg/newsroom');

                    if (!isIsomer && !isBcaPage && !isGoGovSg && !isCorenet && !isMOM) continue;

                    // Skip the base circulars listing page and pagination anchors
                    if (/\\/resources\\/circulars\\/?([\\?#]|$)/.test(href)) continue;

                    // Walk up at most 3 levels to find the item container with a date.
                    // Keeping this shallow prevents accidentally inheriting a date from
                    // a distant shared ancestor (e.g. footer links picking up page dates).
                    let container = link;
                    let found = false;
                    for (let i = 0; i < 3; i++) {
                        if (container.innerText && /\\d{1,2}\\s+\\w+\\s+20\\d{2}/.test(container.innerText)) {
                            found = true;
                            break;
                        }
                        if (!container.parentElement) break;
                        container = container.parentElement;
                    }
                    if (!found) continue;

                    const fullText = container.innerText || '';
                    const dateMatch = fullText.match(/\\d{1,2}\\s+\\w+\\s+20\\d{2}/);
                    if (!dateMatch) continue;

                    const date = dateMatch[0];
                    const yearMatch = date.match(/20\\d{2}/);
                    const year = yearMatch ? yearMatch[0] : '';

                    const titleEl = link.querySelector('h3, h2, h4');
                    const title = (titleEl?.innerText || link.innerText).trim();

                    const url = href;
                    const urlPath = new URL(url).pathname;
                    const filename = decodeURIComponent(
                        urlPath.split('/').filter(Boolean).pop() || ''
                    );

                    results.push({ year, date, title, filename, url });
                }

                return results;
            }
        """

        for page_num in range(1, total_pages + 1):
            print(f"Scraping page {page_num}...")

            # Navigate directly to each page by URL — avoids SPA transition bleed
            # that occurs when clicking Next (old page items linger in DOM briefly).
            if page_num > 1:
                page.goto(f"https://www1.bca.gov.sg/resources/circulars/?page={page_num}")

            try:
                page.wait_for_selector("a[href*='isomer-user-content']", timeout=15000)
            except Exception:
                print(f"  No isomer links on page {page_num} — may be corenet-only, continuing.")

            try:
                page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                pass

            items = page.evaluate(JS_EXTRACT)
            results.extend(items)
            print(f"  Got {len(items)} items. Total so far: {len(results)}")

        browser.close()

    print(f"\nRaw items collected : {len(results)}")

    # Pass 1: deduplicate by URL
    seen_url, unique = set(), []
    for r in results:
        if r['url'] not in seen_url:
            seen_url.add(r['url'])
            unique.append(r)
        else:
            print(f"  Duplicate URL: [{r['date']}] {r['title'][:55]}  =>  {r['url'][:90]}")
    print(f"After URL dedup     : {len(unique)}")

    # Pass 2: deduplicate by (date, title) — catches circulars that appear under
    # both an isomer-user-content PDF URL and a go.gov.sg / BCA page URL.
    # Prefer the isomer-user-content entry (actual PDF) where both exist.
    unique.sort(key=lambda r: (0 if 'isomer-user-content' in r['url'] else 1))
    seen_dt, unique2 = set(), []
    removed_dt = []
    for r in unique:
        key = (r['date'], r['title'][:80])
        if key not in seen_dt:
            seen_dt.add(key)
            unique2.append(r)
        else:
            removed_dt.append(r)
    unique = unique2

    if removed_dt:
        print(f"Date+title dedup removed {len(removed_dt)} entries:")
        for r in removed_dt:
            print(f"  [{r['date']}] {r['title'][:60]}  =>  {r['url'][:80]}")

    print(f"Final unique count  : {len(unique)}")

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
            and 'isomer-user-content' in r['url']   # only download actual PDFs
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