from playwright.sync_api import sync_playwright
import csv, time

def scrape_bca_circulars():
    results = []

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
                        const dateMatch = container.innerText?.match(/\\d{1,2}\\s+\\w+\\s+20\\d{2}/);
                        const titleEl = link.querySelector('h3, h2, h4');
                        results.push({
                            title: (titleEl?.innerText || link.innerText).trim(),
                            url: link.href,
                            date: dateMatch ? dateMatch[0] : ''
                        });
                    });
                    return results;
                }
            """)

            results.extend(items)
            print(f"  Got {len(items)} items. Total: {len(results)}")

            # ✅ Correct selector: it's a <button>, not an <a>
            next_btn = page.locator("button[aria-label='Go to next page']")

            # Stop if button is disabled (last page)
            if next_btn.count() == 0 or next_btn.get_attribute("disabled") is not None:
                print("Reached last page. Done.")
                break

            next_btn.click()
            page_num += 1

            # Wait until content changes
            page.wait_for_function(
                f"""() => {{
                    const links = document.querySelectorAll("a[href*='isomer-user-content']");
                    return links.length > 0 && links[0].href !== "{first_link}";
                }}""",
                timeout=10000
            )
            time.sleep(0.5)

        browser.close()

    seen, unique = set(), []
    for r in results:
        if r['url'] not in seen:
            seen.add(r['url'])
            unique.append(r)

    print(f"\nDone! {len(unique)} unique circulars.")
    with open("bca_circulars.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "title", "url"])
        writer.writeheader()
        writer.writerows(unique)
    print("Saved to bca_circulars.csv")

scrape_bca_circulars()