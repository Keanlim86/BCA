# BCA Circulars Scraper

Scrapes the [BCA circulars listing](https://www1.bca.gov.sg/resources/circulars/), builds a deduplicated
index of every circular, and (optionally) downloads the PDFs.

## Latest script: `Scraping of BCA Criculars_2026.py`

This is the current, actively maintained scraper. Older files in this folder are earlier iterations kept
for reference (see [Other files](#other-files-legacylegacy) below).

### What it does

1. **Discovers pages** — loads the circulars listing and detects how many pagination pages exist.
2. **Extracts items per page** — an in-page JS routine collects every link matching one of five known
   patterns: `isomer-user-content` PDFs, `www1.bca.gov.sg/resources/circulars/` page slugs,
   `go.gov.sg/bca-*` short links, `corenet.gov.sg` links, and `www.mom.gov.sg/newsroom` links. For each
   link it climbs up to 3 parent elements to find a nearby date, then pulls out `year`, `date`, `title`,
   `filename`, and `url`.
3. **Paginates** by navigating directly to `?page=N` (rather than clicking "Next") to avoid stale DOM
   content bleeding between pages.
4. **Deduplicates** in two passes:
   - By `url` (exact duplicate links).
   - By `(date, title)`, preferring the actual `isomer-user-content` PDF link over a `go.gov.sg`/BCA page
     link when both point to the same circular.
5. **Saves the full list** to `bca_circulars.csv` (columns: `year`, `date`, `title`, `filename`, `url`) —
   this happens every run, regardless of whether PDFs are downloaded.
6. **Optionally downloads PDFs** — only for entries with an actual `isomer-user-content` PDF URL, filtered
   by year if requested, skipping anything already listed in `scraped_filenames.py`. New downloads are
   saved to `BCA_Circulars_PDFs_<year>/` (or `BCA_Circulars_PDFs_ALL/`) and logged back into
   `scraped_filenames.py` so re-runs don't re-download them.

### Requirements

- Python 3
- [`playwright`](https://playwright.dev/python/) (with Chromium installed: `playwright install chromium`)
- `requests`

### Browser mode

Launches Chromium **headed** (`headless=False`), so a visible browser window pops up and drives itself
while scraping — this is intentional, paired with `--disable-blink-features=AutomationControlled`, to
reduce the chance of bot detection on the BCA site (more effective in headed mode than headless). Don't
close the window while the script is running.

### Running it

Interactive (default) — prompts for whether to download PDFs and which year:

```bash
python "Scraping of BCA Criculars_2026.py"
```

Non-interactive / testing, via environment variables:

- `TEST_MAX_PAGES` — limit scraping to this many listing pages (e.g. `2` for a quick smoke test).
- `TEST_DOWNLOAD_PDFS` — `1` to download PDFs, `0` to skip. If unset, falls back to the interactive prompt.

```bash
TEST_MAX_PAGES=2 TEST_DOWNLOAD_PDFS=0 python "Scraping of BCA Criculars_2026.py"
```

### Output files

| File / folder | Purpose |
|---|---|
| `bca_circulars.csv` | Full deduplicated index of every circular found (always written). |
| `BCA_Circulars_PDFs_<year>/` or `_ALL/` | Downloaded PDF files, created only when downloading is enabled. |
| `scraped_filenames.py` | Running log (`already_scraped_filenames` set) of filenames already downloaded, so re-runs skip them. |

## Other files (legacy)

These are earlier versions/experiments kept for reference, not actively used:

- `Scraping of BCA Circulars.py` — original `requests` + `BeautifulSoup` scraper (pre-Playwright, static
  HTML fetch only — doesn't handle the JS-rendered listing).
- `Scraping of BCA Circulars_2023_indirectURL.py`, `_2024_indirectURL.py`, `_2024_indirectURL2.py` —
  intermediate Playwright-based iterations from 2023–2024.
- `diagnose_pages.py` — one-off diagnostic script for inspecting specific pages (35–40) for links that
  didn't match the known URL patterns.
- `TestScript.py` — scratch script used to test pagination/navigation behaviour.

## Other assets

- `BCA Circulars Directory.xlsx` — spreadsheet derived from/related to the scraped circulars data.
- `BCA WCR.md` — unrelated: a prompt/context document for a separate BCA meeting-notes assistant, not
  documentation for this scraper.
