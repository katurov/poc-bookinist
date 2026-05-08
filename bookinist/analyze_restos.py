import os
import csv
import json
import pandas as pd
from openai import OpenAI
import glob
import random
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_info(md_content):
    prompt = f"""
    Analyze the following Markdown content of a restaurant page from Gault&Millau.
    Extract the following information in JSON format:
    - name: The official name of the restaurant.
    - review: The Gault&Millau's review text (description of the experience, food, etc.).
    - phone: The phone number.
    - address: The physical address.
    - website: The official website URL.

    Markdown content:
    {md_content}

    Return ONLY valid JSON.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from text."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return None

def main():
    # Load original CSV to keep initial data
    original_data = {}
    with open('restosources.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            original_data[row['name']] = row

    source_files = glob.glob("source/*.md")
    extracted_results = []

    for file_path in source_files:
        print(f"Analyzing {file_path}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        info = extract_info(content)
        if info:
            # Try to match with original data by name (case-insensitive-ish)
            # Find the closest match or use file name
            file_name_stem = os.path.splitext(os.path.basename(file_path))[0]
            
            # Enrich with original description and url if available
            # Note: The names in CSV might not exactly match the 'name' extracted by GPT
            # We'll use the extracted name but try to keep the original URL.
            
            # Simple heuristic: find key in original_data that is a substring or vice versa
            match = None
            for orig_name in original_data:
                if orig_name.lower() in info['name'].lower() or info['name'].lower() in orig_name.lower():
                    match = original_data[orig_name]
                    break
            
            result = {
                "name": info.get('name'),
                "gault_millau_review": info.get('review'),
                "phone": info.get('phone'),
                "address": info.get('address'),
                "website": info.get('website'),
                "original_url": match['url'] if match else None,
                "original_description": match['description'] if match else None
            }
            extracted_results.append(result)

    df = pd.DataFrame(extracted_results)
    
    # Save as Pickle and CSV for convenience
    df.to_pickle("restaurants_data.pkl")
    df.to_csv("restaurants_data.csv", index=False)
    
    print(f"\nSuccessfully processed {len(extracted_results)} restaurants.")
    
    # Show 3 random
    if len(extracted_results) >= 3:
        samples = random.sample(extracted_results, 3)
        for i, s in enumerate(samples, 1):
            print(f"\n--- Random Sample {i} ---")
            print(f"Name: {s['name']}")
            print(f"Address: {s['address']}")
            print(f"Phone: {s['phone']}")
            print(f"Website: {s['website']}")
            print(f"Review Snippet: {s['gault_millau_review'][:200]}...")

if __name__ == "__main__":
    main()
