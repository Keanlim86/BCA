import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse
import time
import os
import re
from datetime import datetime

def get_final_pdf_url(redirect_url, headers):
    """Follow redirects to get the final PDF URL"""
    try:
        print(f"Following redirect: {redirect_url}")
        response = requests.head(redirect_url, headers=headers, allow_redirects=True, timeout=10)
        final_url = response.url
        
        # Check if final URL is a PDF
        if final_url.lower().endswith('.pdf') or 'pdf' in final_url.lower():
            print(f"✓ Found final PDF URL: {final_url}")
            return final_url
        else:
            print(f"⚠ Final URL doesn't appear to be a PDF: {final_url}")
            return None
            
    except requests.RequestException as e:
        print(f"✗ Error following redirect {redirect_url}: {e}")
        return None

url = "https://www1.bca.gov.sg/about-us/news-and-publications/circulars?year=2024"  # Replace with your URL

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
    
    all_links = soup.find_all('a', href=True)
    bca_circulars = []
    
    # Separate patterns for direct PDFs and redirects
    direct_pdf_pattern = r'/docs/default-source/docs-corp-news-and-publications/circulars/.*\.pdf'
    redirect_pattern = r'https://go\.gov\.sg/bca-circular-.*'

    print("\nProcessing links...")
    print("=" * 50)

    direct_pdf_count = 0
    redirect_count = 0

    for link in all_links:
        href = link['href']
        
        # Check for direct PDF links
        if re.search(direct_pdf_pattern, href, re.IGNORECASE):
            full_url = urljoin(url, href)
            filename = href.split('/')[-1].split('?')[0]
            title = link.get_text(strip=True)
            
            # Get context from parent elements
            parent_text = ""
            parent = link.find_parent()
            if parent:
                parent_text = parent.get_text(strip=True)
                
            circular_info = {
                'Year': "2024",  # Fixed the year
                'filename': filename,
                'title': title if title and title != "Read More" else filename.replace('.pdf', '').replace('-', ' ').title(),
                'url': full_url,
                'context': parent_text[:200] + "..." if len(parent_text) > 200 else parent_text,
                'source_type': 'direct_pdf'
            }
            
            bca_circulars.append(circular_info)
            print(f"✓ Direct PDF: {filename}")
        
        # Check for go.gov.sg redirect links
        elif re.search(redirect_pattern, href, re.IGNORECASE):
            redirect_count += 1
            print(f"\n🔄 FOUND REDIRECT LINK #{redirect_count}: {href}")  # ADD THIS LINE
            print(f"Link text: '{link.get_text(strip=True)}'")  # ADD THIS LINE
            print(f"\nProcessing redirect link: {href}")
            
            # Follow the redirect to get final PDF URL
            print(f"Starting redirect processing... (this should take 8+ seconds)")  # ADD THIS LINE
            start_time = time.time()  # ADD THIS LINE
        
            final_pdf_url = get_final_pdf_url(href, headers)
            
            end_time = time.time()  # ADD THIS LINE
            print(f"Redirect processing took {end_time - start_time:.2f} seconds")  # ADD THIS LINE
            
            if final_pdf_url:
                # Extract filename from final URL
                filename = final_pdf_url.split('/')[-1].split('?')[0]
                if not filename.endswith('.pdf'):
                    filename = href.split('/')[-1] + '.pdf'  # Fallback filename
                
                title = link.get_text(strip=True)
                
                # Get context from parent elements
                parent_text = ""
                parent = link.find_parent()
                if parent:
                    parent_text = parent.get_text(strip=True)
                    
                circular_info = {
                    'Year': "2024",
                    'filename': filename,
                    'title': title if title and title != "Read More" else href.split('/')[-1].replace('-', ' ').title(),
                    'url': final_pdf_url,  # Use the final PDF URL
                    'context': parent_text[:200] + "..." if len(parent_text) > 200 else parent_text,
                    'source_type': 'redirect',
                    'original_redirect_url': href  # Keep track of original redirect
                }
                
                bca_circulars.append(circular_info)
                print(f"✓ Redirect PDF: {filename}")
            
            # Add a small delay between redirect requests to be respectful
            time.sleep(0.5)

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
        save_directory1 = r"C:\Users\USER\0. Coding\BCA Circulars\Extracted CSV"
        save_directory2 = r"C:\Users\USER\0. Coding\BCA Circulars\Extracted URL"

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
        download_folder = r"C:\Users\USER\0. Coding\BCA Circulars\bca_circulars"
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