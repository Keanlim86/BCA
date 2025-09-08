
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse
import time
import os
import re
from datetime import datetime

url = "https://www1.bca.gov.sg/about-us/news-and-publications/circulars"  # Replace with your URL

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
# Send GET request to the URL
response = requests.get(url, headers=headers)

# Check if request was successful
if response.status_code == 200:
    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Now you can work with the parsed content
    print("Page title:", soup.title.text if soup.title else "No title found")
    
    # Example: Find all links
    links = soup.find_all('a')
    print(f"Found {len(links)} links on the page")
    
    # Print first 5 links
    for i, link in enumerate(links[50:120]):
        print(f"{i+1}. {link.get('href')} - {link.text.strip()}")

    all_links = soup.find_all('a', href=True)
    bca_circulars = []
    circular_pattern = r'/docs/default-source/docs-corp-news-and-publications/circulars/.*\.pdf'

    for link in all_links:
        href = link['href']
            
        # Check if link matches BCA circular pattern
        if re.search(circular_pattern, href, re.IGNORECASE):
            full_url = urljoin(url, href)
                
            # Extract filename from URL
            filename = href.split('/')[-1].split('?')[0]
                
            # Get link text (title)
            title = link.get_text(strip=True)
                
            # Try to get more context from parent elements
            parent_text = ""
            parent = link.find_parent()
            if parent:
                parent_text = parent.get_text(strip=True)
                
            circular_info = {
                'filename': filename,
                'title': title if title and title != "Read More" else filename.replace('.pdf', '').replace('-', ' ').title(),
                'url': full_url,
                'context': parent_text[:200] + "..." if len(parent_text) > 200 else parent_text
            }
                
            bca_circulars.append(circular_info)
            print(bca_circulars)

    # Remove duplicates based on URL
    seen_urls = set()
    unique_circulars = []
    for circular in bca_circulars:
        if circular['url'] not in seen_urls:
            unique_circulars.append(circular)
            seen_urls.add(circular['url'])

    print(f"Found {len(unique_circulars)} BCA circular PDFs:")
    print("=" * 80)

    # Display results
    for i, circular in enumerate(unique_circulars, 1):
        print(f"{i:2d}. {circular['title']}")
        print(f"    File: {circular['filename']}")
        print(f"    URL:  {circular['url']}")
        print()
        
    # Save to CSV
    if unique_circulars:
        save_directory1 = r"C:\Users\USER\Python Coding\Data Scraping_BCA Circular\Extracted CSV"  # Full C: drive path
        save_directory2 = r"C:\Users\USER\Python Coding\Data Scraping_BCA Circular\Extracted URL"  # Full C: drive path

        if not os.path.exists(save_directory1):
            os.makedirs(save_directory1)
        if not os.path.exists(save_directory2):
            os.makedirs(save_directory2)

        df = pd.DataFrame(unique_circulars)
        timestamp = datetime.now().strftime("%Y%m%d")
        csv_filename = os.path.join(save_directory1, f'bca_circulars_{timestamp}.csv')
        df.to_csv(csv_filename, index=False)
        print(f"✓ Saved {len(unique_circulars)} circulars to '{csv_filename}'")
        
        # Also create a simple list of URLs for easy copying
        urls_filename = os.path.join(save_directory2, f'bca_circular_urls_{timestamp}.txt')
        with open(urls_filename, 'w') as f:
            for circular in unique_circulars:
                f.write(f"{circular['url']}\n")
        print(f"✓ Saved URLs list to '{urls_filename}'")

    # Optional: Download all PDFs
    download_choice = input("\nDo you want to download all PDF files? (y/n): ").lower()

    if download_choice == 'y':
        download_folder = r"C:\Users\USER\Python Coding\Data Scraping_BCA Circular\bca_circulars"
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
        
        print(f"\nDownloading {len(unique_circulars)} PDF files...")
        
        for i, circular in enumerate(unique_circulars, 1):
            try:
                print(f"Downloading {i}/{len(unique_circulars)}: {circular['filename']}")
                
                pdf_response = requests.get(circular['url'], headers=headers, stream=True)
                pdf_response.raise_for_status()
                
                filepath = os.path.join(download_folder, circular['filename'])
                
                with open(filepath, 'wb') as f:
                    for chunk in pdf_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"✓ Downloaded: {circular['filename']}")
                
            except requests.RequestException as e:
                print(f"✗ Failed to download {circular['filename']}: {e}")
            
            # Be respectful with requests
            if i < len(unique_circulars):
                time.sleep(1)
        
        print(f"\n✓ Download complete! Files saved to '{download_folder}' folder")

    print("\n" + "="*80)
    print("SCRAPING COMPLETE")
    print("="*80)

else:
    print(f"Failed to retrieve the page. Status code: {response.status_code}")