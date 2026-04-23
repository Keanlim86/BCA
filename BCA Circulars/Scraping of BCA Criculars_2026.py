from playwright.sync_api import sync_playwright
import csv, time

def scrape_bca_circulars():
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www1.bca.gov.sg/resources/circulars/")
        page.wait_for_load_state("networkidle")

        while True:
            # Extract all circular cards on current page
            cards = page.query_selector_all("article, .article-card, a[href*='isomer-user-content']")
            
            # More robust: grab date + title + link together
            items = page.evaluate("""
                () => {
                    const results = [];
                    const links = document.querySelectorAll('a[href*="isomer-user-content"]');
                    links.forEach(link => {
                        const container = link.closest('div') || link.parentElement;
                        const dateEl = container?.querySelector('p, span, time');
                        results.push({
                            title: link.innerText.trim(),
                            url: link.href,
                            date: dateEl?.innerText.trim() || ''
                        });
                    });
                    return results;
                }
            """)
            results.extend(items)
            print(f"Scraped {len(results)} so far...")

            # Try clicking "Next"
            next_btn = page.query_selector("a[aria-label='Next page'], button:has-text('Next'), a:has-text('Next')")
            if not next_btn or not next_btn.is_enabled():
                break
            next_btn.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)  # be polite

        browser.close()

    # Save to CSV
    with open("bca_circulars.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "title", "url"])
        writer.writeheader()
        writer.writerows(results)

    print(f"Done! {len(results)} circulars saved to bca_circulars.csv")

scrape_bca_circulars()