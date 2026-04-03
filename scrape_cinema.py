import requests
import json

def get_google_listings():
    # Your verified Serper key
    api_key = "cabfbdda7799cd435ca95f62e27e8c2d886f32a6"
    url = "https://google.serper.dev/search"
    
    # We ask for a very specific list to force Google to give us titles
    payload = json.dumps({
        "q": "current movie showtimes Edinburgh Filmhouse Dominion Everyman Vue Odeon Cameo",
        "gl": "gb",
        "hl": "en"
    })
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}

    listings = []
    seen_titles = set() # This prevents the 'Dominion Cinema' repeat

    try:
        response = requests.post(url, headers=headers, data=payload)
        results = response.json()
        
        # 1. PULL FROM KNOWLEDGE GRAPH (The 'Gold Standard' for titles)
        if 'knowledgeGraph' in results:
            for movie in results['knowledgeGraph'].get('attributes', []):
                title = movie.get('label')
                if title and title not in seen_titles:
                    listings.append({"title": title, "venue": "Now Playing"})
                    seen_titles.add(title)
        
        # 2. PULL FROM ORGANIC (The 'Arthouse' backup for Filmhouse/Dominion)
        if 'organic' in results:
            for item in results['organic'][:15]:
                raw_title = item.get('title', '')
                # Clean up the title by removing common website 'junk'
                clean_title = raw_title.split(' - ')[0].split(' | ')[0].replace('Cinema', '').strip()
                
                # Only add if it's not a repeat and doesn't look like a generic link
                if clean_title not in seen_titles and len(clean_title) > 3:
                    # Logic: If it mentions a specific theater, label it
                    venue = "Edinburgh"
                    if 'Dominion' in raw_title: venue = "Dominion"
                    if 'Everyman' in raw_title: venue = "Everyman"
                    if 'Filmhouse' in raw_title: venue = "Filmhouse"
                    
                    listings.append({"title": clean_title, "venue": venue})
                    seen_titles.add(clean_title)

    except Exception as e:
        listings = [{"title": f"Sync Error: {e}", "venue": "System"}]
        
    return listings

if __name__ == "__main__":
    data = get_google_listings()
    with open('listings.json', 'w') as f:
        json.dump(data, f, indent=2)
