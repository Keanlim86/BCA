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

    # Navigate to last few pages where older circulars are
    for target_page in range(2, 40):
        first_link = page.locator("a[href*='isomer-user-content']").first.get_attribute("href")
        next_btn = page.locator("button[aria-label='Go to next page']")
        if next_btn.count() == 0 or next_btn.get_attribute("disabled") is not None:
            break
        next_btn.click()
        try:
            page.wait_for_function(
                f"""() => {{
                    const links = document.querySelectorAll("a[href*='isomer-user-content']");
                    return links.length > 0 && links[0].href !== "{first_link}";
                }}""",
                timeout=8000
            )
        except:
            # If wait fails, this page might have NO isomer links - check all links
            all_links = page.evaluate("""
                () => [...document.querySelectorAll('a[href]')]
                    .map(a => a.href)
                    .filter(h => h.includes('.pdf') || h.includes('circular') || h.includes('/docs/'))
            """)
            if all_links:
                print(f"\n=== Page {target_page} has NON-ISOMER links ===")
                for l in all_links[:5]:
                    print(" ", l)
            break

        # Count both isomer and non-isomer links on this page
        counts = page.evaluate("""
            () => {
                const isomer = document.querySelectorAll("a[href*='isomer-user-content']").length;
                const docs = document.querySelectorAll("a[href*='bca.gov.sg/docs']").length;
                const allPdf = [...document.querySelectorAll("a[href]")]
                    .filter(a => a.href.includes('.pdf')).length;
                const nonIsomerPdf = [...document.querySelectorAll("a[href]")]
                    .filter(a => a.href.includes('.pdf') && !a.href.includes('isomer')).length;
                return { isomer, docs, allPdf, nonIsomerPdf };
            }
        """)

        if counts['nonIsomerPdf'] > 0 or counts['isomer'] < 10:
            print(f"Page {target_page}: isomer={counts['isomer']} | docs={counts['docs']} | nonIsomerPdf={counts['nonIsomerPdf']}")
            # Print the non-isomer links
            non_isomer = page.evaluate("""
                () => [...document.querySelectorAll("a[href]")]
                    .filter(a => a.href.includes('.pdf') && !a.href.includes('isomer'))
                    .map(a => a.href)
            """)
            for l in non_isomer:
                print("  NON-ISOMER:", l)
        else:
            print(f"Page {target_page}: OK (isomer={counts['isomer']})")

    browser.close()