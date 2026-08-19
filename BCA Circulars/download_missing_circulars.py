"""
Downloads the 55 circulars listed in circulars_missing_as_of_2026-04-17.xlsx into
Missing_Circulars_2026-04-17/<year>/, resolving page/short-links to their actual PDF
where possible.
"""
from playwright.sync_api import sync_playwright
import openpyxl, os, re, requests, time
from urllib.parse import urlparse, unquote

SRC_XLSX = "circulars_missing_as_of_2026-04-17.xlsx"
OUT_ROOT = "Missing_Circulars_2026-04-17"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def safe_filename(name, fallback):
    name = name or fallback
    name = re.sub(r'[<>:"/\\|?*]', '_', name).strip()
    return name[:150] if name else fallback

def filename_from_url(url):
    path = urlparse(url).path
    return unquote(path.split('/')[-1]) or None

def download_direct(url, dest_path):
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code == 200 and r.content:
        with open(dest_path, "wb") as f:
            f.write(r.content)
        return True, r.headers.get("Content-Type", "")
    return False, f"HTTP {r.status_code}"

def main():
    wb = openpyxl.load_workbook(SRC_XLSX, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    print(f"Loaded {len(rows)} missing circulars.")

    os.makedirs(OUT_ROOT, exist_ok=True)

    results = []  # (year, date, title, status, detail, saved_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            user_agent=HEADERS["User-Agent"], locale="en-SG"
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()

        for idx, row in enumerate(rows, 1):
            year, date, filename, title, url = row[0], row[1], row[2], row[3], row[4]
            year = str(int(year))
            year_dir = os.path.join(OUT_ROOT, year)
            os.makedirs(year_dir, exist_ok=True)
            date_str = date.strftime("%Y-%m-%d") if date else "unknown-date"

            print(f"[{idx}/{len(rows)}] {date_str} | {(title or '')[:60]}")

            if url and "isomer-user-content" in url:
                fn = filename_from_url(url) or safe_filename(title, f"circular_{idx}") + ".pdf"
                fn = f"{date_str}_{safe_filename(fn, f'circular_{idx}.pdf')}"
                dest = os.path.join(year_dir, fn)
                ok, detail = download_direct(url, dest)
                results.append((year, date_str, title, "OK-direct" if ok else "FAIL-direct", detail, dest if ok else ""))
                time.sleep(0.3)
                continue

            # Page/short-link: visit and look for an isomer-user-content PDF link
            try:
                page.goto(url, timeout=25000, wait_until="domcontentloaded")
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass

                pdf_href = page.evaluate("""
                    () => {
                        const links = Array.from(document.querySelectorAll('a[href]'));
                        const hit = links.find(a => a.href.includes('isomer-user-content'));
                        return hit ? hit.href : null;
                    }
                """)

                if pdf_href:
                    fn = filename_from_url(pdf_href) or safe_filename(title, f"circular_{idx}") + ".pdf"
                    fn = f"{date_str}_{safe_filename(fn, f'circular_{idx}.pdf')}"
                    dest = os.path.join(year_dir, fn)
                    ok, detail = download_direct(pdf_href, dest)
                    results.append((year, date_str, title, "OK-resolved" if ok else "FAIL-resolved", pdf_href, dest if ok else ""))
                else:
                    # No PDF found on the page — save the rendered page as HTML fallback
                    html = page.content()
                    fn = f"{date_str}_{safe_filename(title, f'circular_{idx}')}.html"
                    dest = os.path.join(year_dir, fn)
                    with open(dest, "w", encoding="utf-8") as f:
                        f.write(html)
                    results.append((year, date_str, title, "NO-PDF-saved-html", url, dest))
            except Exception as e:
                results.append((year, date_str, title, "ERROR", str(e), ""))

            time.sleep(0.3)

        browser.close()

    # Summary
    ok_count = sum(1 for r in results if r[3].startswith("OK"))
    print(f"\n{ok_count}/{len(results)} PDFs downloaded successfully.")
    fails = [r for r in results if not r[3].startswith("OK")]
    if fails:
        print(f"{len(fails)} not downloaded as PDF:")
        for r in fails:
            print(f"  [{r[3]}] {r[1]} | {(r[2] or '')[:60]} | {r[4][:90]}")

    # Write a log CSV
    import csv
    with open(os.path.join(OUT_ROOT, "_download_log.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "date", "title", "status", "detail", "saved_path"])
        w.writerows(results)
    print(f"\nLog written to {os.path.join(OUT_ROOT, '_download_log.csv')}")

if __name__ == "__main__":
    main()
