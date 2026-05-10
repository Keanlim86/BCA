"""Diagnostic: check pages 35-40 for OTHER-tagged links that might be valid circulars."""
from playwright.sync_api import sync_playwright
import time

TARGET_PAGES = list(range(35, 41))

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        page.goto("https://www1.bca.gov.sg/resources/circulars/")
        page.wait_for_selector("a[href*='isomer-user-content']", timeout=20000)

        page_num = 1

        while True:
            page.wait_for_load_state('networkidle', timeout=10000)

            if page_num in TARGET_PAGES:
                debug = page.evaluate("""
                    () => {
                        const KNOWN = [
                            'isomer-user-content', 'www1.bca.gov.sg/resources/circulars/',
                            'go.gov.sg/bca',
                        ];
                        const SKIP = [
                            'facebook', 'youtube', 'instagram', 'linkedin', 'tiktok',
                            'telegram', 'scamshield', 'reach.gov', 'isomer.gov',
                            'open.gov', 'trusted-sites', 'bca.gov.sg/contact',
                            'bca.gov.sg/feedback', 'privacy', 'terms-of-use',
                            'about-us', '/e-services', '/safety-and', '/sustainability',
                            '/growth', '/home-and-building', 'www1.bca.gov.sg/resources/',
                            'go.gov.sg/report',
                        ];

                        const out = [];
                        for (const link of document.querySelectorAll('a[href]')) {
                            const href = link.href || '';
                            if (!href) continue;
                            if (/\\/resources\\/circulars\\/?([\\?#]|$)/.test(href)) continue;
                            if (SKIP.some(s => href.includes(s))) continue;

                            let container = link;
                            let found = false;
                            for (let i = 0; i < 5; i++) {
                                if (container.innerText && /\\d{1,2}\\s+\\w+\\s+20\\d{2}/.test(container.innerText)) {
                                    found = true; break;
                                }
                                if (!container.parentElement) break;
                                container = container.parentElement;
                            }
                            if (!found) continue;

                            const dateMatch = container.innerText.match(/\\d{1,2}\\s+\\w+\\s+20\\d{2}/);
                            const isKnown = KNOWN.some(p => href.includes(p));
                            out.push({
                                href, isKnown,
                                date: dateMatch ? dateMatch[0] : '',
                                text: (link.innerText || '').trim().slice(0, 60),
                            });
                        }
                        return out;
                    }
                """)

                other = [d for d in debug if not d['isKnown']]
                known_count = sum(1 for d in debug if d['isKnown'])
                print(f"\nPage {page_num}: {known_count} known + {len(other)} OTHER links")
                for d in other:
                    print(f"  [{d['date']}] {d['text'][:55]}")
                    print(f"    => {d['href'][:110]}")

            first_link = None
            links = page.locator("a[href*='isomer-user-content']")
            if links.count() > 0:
                first_link = links.first.get_attribute("href")

            next_btn = page.locator("button[aria-label='Go to next page']")
            if next_btn.count() == 0 or next_btn.is_disabled():
                print(f"\nStopped at page {page_num} (last page).")
                break
            if page_num >= max(TARGET_PAGES):
                break

            next_btn.click()
            page_num += 1

            if first_link:
                try:
                    page.wait_for_function(
                        f"""() => {{
                            const links = document.querySelectorAll("a[href*='isomer-user-content']");
                            return links.length > 0 && links[0].href !== "{first_link}";
                        }}""",
                        timeout=15000
                    )
                except Exception:
                    time.sleep(2)

        browser.close()

run()
