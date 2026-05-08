import csv
import requests
import os
import time
from urllib.parse import quote

def download_markdown(csv_path, output_dir):
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Read CSV using the csv module for better control
    rows = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Using DictReader to handle columns by name
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        # If standard reading fails, try with more relaxed settings or manual fix
        # But for now, let's see if this works better than pandas defaults
        return

    total = len(rows)
    for index, row in enumerate(rows):
        name = row.get('name')
        url = row.get('url')
        
        if not name or not url:
            print(f"Skipping row {index+1} due to missing name or url")
            continue

        # Create a safe filename
        safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip()
        filename = f"{safe_name}.md"
        filepath = os.path.join(output_dir, filename)
        
        # Construct markdown.new URL
        md_url = f"https://markdown.new/{url}"
        
        print(f"Processing ({index+1}/{total}): {name}...")
        
        try:
            response = requests.get(md_url, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"  Saved to {filename}")
            else:
                print(f"  Failed to download {name}: Status {response.status_code}")
        except Exception as e:
            print(f"  Error downloading {name}: {str(e)}")
        
        # Small delay to be polite to the service
        time.sleep(1)

if __name__ == "__main__":
    download_markdown('restosources.csv', 'source')
