import requests
import json

def get_google_listings():
    # Your verified Serper key
    api_key = "cabfbdda7799cd435ca95f62e27e8c2d886f32a6"
    url = "https://google.serper.dev/search"
    
    # We use a broader query to catch independent theaters like Filmhouse and Dominion
    payload = json.dumps({
        "q": "cinema movie showtimes Edinburgh Filmhouse Dominion Everyman Cameo Vue",
        "gl": "gb",
        "hl": "en"
    })
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}

    listings = []
    seen_titles = set()

    try:
        response = requests.post(url, headers=headers, data=payload)
        results = response.json()
        
        # 1. Look in the Knowledge Graph (Usually has the best movie list)
        if 'knowledgeGraph' in results:
            kg = results['knowledgeGraph']
            # Serper often puts movie lists in 'attributes' or 'relatedSearches'
            for attr in kg.get('attributes', []):
                title = attr.get('label')
                if title and title not in seen_titles:
                    listings.append({"title": title, "venue": "Now Playing"})
                    seen_titles.add(title)

        # 2. Look in Organic Results (Great for picking up specific theater names)
        if 'organic' in results:
            for item in results['organic'][:15]:
                title_line = item.get('title', '')
                # Clean up the string to find the actual movie title
                # Usually follows format: "Movie Title - Venue - Date"
                clean_title = title_line.split(' - ')[0].split(' | ')[0].strip()
                
                if clean_title and clean_title not in seen_titles and len(clean_title) > 3:
                    venue = "Edinburgh"
                    if "Filmhouse" in title_line: venue = "Filmhouse"
                    elif "Dominion" in title_line: venue = "Dominion"
                    elif "Everyman" in title_line: venue = "Everyman"
                    
                    listings.append({"title": clean_title, "venue": venue})
                    seen_titles.add(clean_title)

    except Exception as e:
        listings = [{"title": f"Sync Error: {e}", "venue": "System"}]
    
    # If it's still empty, we use a slightly more generic fallback
    if not listings:
        listings = [{"title": "Updating listings...", "venue": "Check back shortly"}]
        
    return listings

if __name__ == "__main__":
    data = get_google_listings()
    with open('listings.json', 'w') as f:
        json.dump(data, f, indent=2)
