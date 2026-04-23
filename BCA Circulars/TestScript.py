from playwright.sync_api import sync_playwright

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

    # Dump everything near the bottom of the page (pagination area)
    info = page.evaluate("""
        () => {
            const results = [];
            
            // All buttons
            document.querySelectorAll('button').forEach(el => {
                results.push('BUTTON: ' + el.outerHTML.slice(0, 200));
            });
            
            // All links with short text (pagination links are short)
            document.querySelectorAll('a').forEach(el => {
                const txt = el.innerText.trim();
                if (txt.length < 20) {
                    results.push('LINK: text=' + txt + ' | class=' + el.className.slice(0,80) + ' | href=' + el.href.slice(0,80));
                }
            });
            
            // Any element with aria-label containing next/prev
            document.querySelectorAll('[aria-label]').forEach(el => {
                const lbl = el.getAttribute('aria-label').toLowerCase();
                if (lbl.includes('next') || lbl.includes('prev') || lbl.includes('page')) {
                    results.push('ARIA: ' + el.outerHTML.slice(0, 200));
                }
            });
            
            return results;
        }
    """)
    
    for line in info:
        print(line)
    
    browser.close()