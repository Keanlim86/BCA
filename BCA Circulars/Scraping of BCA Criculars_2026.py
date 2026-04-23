import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import time
import os
import re
import random
from datetime import datetime
from scraped_filenames import already_scraped_filenames

year = "2025"  # Set to "All" or a specific year like "2025"

def extract_title_and_context(link, href):
    title_tag = link.find('h3')
    if title_tag:
        title = title_tag.get_text(" ", strip=True)
    else:
        title = link.get_text(" ", strip=True)
        if title == "Read More":
            title = href.split('/')[-1].replace('.pdf', '').replace('-', ' ').title()

    context = link.get_text(" ", strip=True)
    return title, context


def get_final_pdf_url(redirect_url, headers):
    """Method with multiple longer waits"""
    try:
        print(f"📥 Starting extended redirect processing: {redirect_url}")
        
        session = requests.Session()
        session.headers.update(headers)
        
        # Wait before even making the first request
        print(f"⏰ Pre-request wait: 3 seconds...")
        time.sleep(3)
        
        # First request
        print(f"📤 Making first request...")
        response1 = session.get(redirect_url, allow_redirects=True, timeout=10)
        print(f"📍 First result: {response1.url}")
        
        # Wait longer - some redirects are very slow
        print(f"⏰ Waiting 10 seconds for delayed redirect...")
        time.sleep(10)
        
        # Second request
        print(f"📤 Making second request...")
        response2 = session.get(response1.url, allow_redirects=True, timeout=10)
        print(f"📍 Second result: {response2.url}")
        
        # Even longer wait
        print(f"⏰ Final wait: 6 seconds...")
        time.sleep(6)
        
        # Third request
        print(f"📤 Making final request...")
        response3 = session.get(response2.url, allow_redirects=True, timeout=10)
        final_url = response3.url
        
        print(f"📍 Final URL: {final_url}")
        
        if final_url.lower().endswith('.pdf') or 'pdf' in final_url.lower():
            return final_url
        else:
            return None
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return None

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www1.bca.gov.sg/resources/circulars/',
}

bca_circulars = []
page = 1

while True:
    if year == "All":
        url = "https://www1.bca.gov.sg/resources/circulars/"
    else:
        url = f"https://www1.bca.gov.sg/resources/circulars/?filters=%5B%7B%22id%22%3A%22year%22%2C%22items%22%3A%5B%7B%22id%22%3A%222025%22%7D%5D%7D%5D&page={page}"
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve page {page}. Status code: {response.status_code}")
        break
    
    soup = BeautifulSoup(response.content, 'html.parser')
    page_links = soup.find_all('a', href=True)
    
    if not page_links:
        print(f"No links found on page {page}. Stopping.")
        break
    
    print(f"Found {len(page_links)} links on page {page}")
    
    # Track circulars before processing this page
    len_before = len(bca_circulars)
    
    # Process links from this page
    skip_filenames = already_scraped_filenames
        
    # Separate patterns for direct PDFs and redirects
    direct_pdf_pattern = (
        r'https://www.corenet.gov.sg/.*\.pdf|'
        r'https://isomer-user-content\.by\.gov\.sg/.*\.pdf|'
        r'/docs/default-source/docs-corp-news-and-publications/circulars/.*\.pdf'
    )
    
    redirect_pattern = (
        r'https://go\.gov\.sg/bca-circular-.*|'
        r'https://go\.gov\.sg/bca-guidance-.*|'
        r'https://go\.gov\.sg/bca-advisory-.*|'
        r'https://go\.gov\.sg/bca-enhanced.*|'
        r'https://go\.gov\.sg/approved-.*|'
        r'https://go\.gov\.sg/iacc-.*|'
        r'https://go\.gov\.sg/annual-.*|'
        r'https://go\.gov\.sg/bca-ggbs-.*|'
        r'https://go\.gov\.sg/bca-adv-.*|'
        r'https://go\.gov\.sg/bca-nea-.*|'
        r'https://go\.gov\.sg/reopening-.*|'
        r'https://go\.gov\.sg/bca-distancing-.*|'
        r'https://go\.gov\.sg/covid19-.*|'
        r'https://go\.gov\.sg/bca-amusement-.*|'
        r'https://go\.gov\.sg/bca-sifma-.*|'
        r'https://go\.gov\.sg/bca-mom-.*|'
        r'https://go\.gov\.sg/bca-adjustment-.*|'
        r'https://go\.gov\.sg/bca-mandatory-.*|'
        r'https://go\.gov\.sg/bca-supplementary-.*|'
        r'https://go\.gov\.sg/cotma-.*|'
        r'https://go\.gov\.sg/bca-changes-.*|'
        r'https://go\.gov\.sg/circular-.*'
    )

    print(f"\nProcessing links from page {page}...")
    
    direct_pdf_count = 0
    redirect_count = 0

    for link in page_links:
        href = link['href']
        
        # Check for direct PDF links
        if re.search(direct_pdf_pattern, href, re.IGNORECASE):
            full_url = urljoin(url, href)
            filename = href.split('/')[-1].split('?')[0]

            if filename in skip_filenames:
                print(f"→ Skipping already scraped direct PDF: {filename}")
                continue

            title, context = extract_title_and_context(link, href)
                
            circular_info = {
                'Year': year,
                'filename': filename,
                'title': title,
                'url': full_url,
                'context': context[:200] + "..." if len(context) > 200 else context,
                'source_type': 'direct_pdf'
            }
            
            bca_circulars.append(circular_info)
            print(f"✓ Direct PDF: {filename}")
        
        # Check for go.gov.sg redirect links
        elif re.search(redirect_pattern, href, re.IGNORECASE):
            redirect_count += 1
            print(f"\n🔄 FOUND REDIRECT LINK #{redirect_count}: {href}")
            print(f"Link text: '{link.get_text(strip=True)}'")
            print(f"\nProcessing redirect link: {href}")
            
            print(f"Starting redirect processing... (this should take 8+ seconds)")
            start_time = time.time()
        
            final_pdf_url = get_final_pdf_url(href, headers)
            
            end_time = time.time()
            print(f"Redirect processing took {end_time - start_time:.2f} seconds")
            
            if final_pdf_url:
                # Extract filename from final URL
                filename = final_pdf_url.split('/')[-1].split('?')[0]
                if not filename.endswith('.pdf'):
                    filename = href.split('/')[-1] + '.pdf'  # Fallback filename

                if filename in skip_filenames:
                    print(f"→ Skipping already scraped redirect PDF: {filename}")
                    continue
                
                title, context = extract_title_and_context(link, href)
                    
                circular_info = {
                    'Year': year,
                    'filename': filename,
                    'title': title,
                    'url': final_pdf_url,
                    'context': context[:200] + "..." if len(context) > 200 else context,
                    'source_type': 'redirect',
                    'original_redirect_url': href
                }
                
                bca_circulars.append(circular_info)
                print(f"✓ Redirect PDF: {filename}")
            
            # Add a small delay between redirect requests to be respectful
            time.sleep(0.5)
    
    len_after = len(bca_circulars)
    new_circulars = len_after - len_before
    print(f"Added {new_circulars} new circulars from page {page}")
    
    if new_circulars == 0:
        print(f"No new circulars found on page {page}. Stopping pagination.")
        break
    
    page += 1

print(f"\nProcessing complete!")
print("=" * 50)

# Remove duplicates based on final URL
seen_urls = set()
unique_circulars = []
for circular in bca_circulars:
    if circular['url'] not in seen_urls:
        unique_circulars.append(circular)
        seen_urls.add(circular['url'])

print(f"Found {len(unique_circulars)} unique BCA circular PDFs:")
print("=" * 80)

# Display results
for i, circular in enumerate(unique_circulars, 1):
    print(f"{i:2d}. {circular['title']}")
    print(f"    File: {circular['filename']}")
    print(f"    Type: {circular['source_type']}")
    if circular['source_type'] == 'redirect':
        print(f"    Original: {circular['original_redirect_url']}")
    print(f"    URL:  {circular['url']}")
    print()
    
# Save to CSV
if unique_circulars:
    save_directory1 = f"C:\\Users\\USER\\0. Coding\\BCA Circulars\\Extracted CSV_{year}"
    save_directory2 = f"C:\\Users\\USER\\0. Coding\\BCA Circulars\\Extracted URL_{year}"

    if not os.path.exists(save_directory1):
        os.makedirs(save_directory1)
    if not os.path.exists(save_directory2):
        os.makedirs(save_directory2)

    df = pd.DataFrame(unique_circulars)
    timestamp = datetime.now().strftime("%Y%m%d")
    csv_filename = os.path.join(save_directory1, f'bca_circulars_{year}_{timestamp}.csv')
    df.to_csv(csv_filename, index=False)
    print(f"✓ Saved {len(unique_circulars)} circulars to '{csv_filename}'")
    
    # Also create a simple list of URLs for easy copying
    urls_filename = os.path.join(save_directory2, f'bca_circular_urls_{year}_{timestamp}.txt')
    with open(urls_filename, 'w') as f:
        for circular in unique_circulars:
            f.write(f"{circular['url']}\n")
    print(f"✓ Saved URLs list to '{urls_filename}'")

# Optional: Download all PDFs
download_choice = input("\nDo you want to download all PDF files? (y/n): ").lower()

if download_choice == 'y':
    download_folder = f"C:\\Users\\USER\\0. Coding\\BCA Circulars\\bca_circulars_{year}"
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
    
    print(f"\nDownloading {len(unique_circulars)} PDF files...")
    
    for i, circular in enumerate(unique_circulars, 1):
        try:
            print(f"Downloading {i}/{len(unique_circulars)}: {circular['filename']}")
            
            filepath = os.path.join(download_folder, circular['filename'])
            if os.path.exists(filepath):
                print(f"→ File already exists, skipping: {circular['filename']}")
                continue
            
            pdf_response = requests.get(circular['url'], headers=headers, stream=True)
            pdf_response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in pdf_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✓ Downloaded: {circular['filename']}")
            
        except requests.RequestException as e:
            print(f"✗ Failed to download {circular['filename']}: {e}")
        
        # Be respectful with requests
        if i < len(unique_circulars):
            time.sleep(random.uniform(2,4))  # Random delay between 2 to 4 seconds
    
    print(f"\n✓ Download complete! Files saved to '{download_folder}' folder")

print("\n" + "="*80)
print("SCRAPING COMPLETE")
print("="*80)

