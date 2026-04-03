import requests
import json

def get_google_listings():
    # Using your Serper key
    api_key = "cabfbdda7799cd435ca95f62e27e8c2d886f32a6"
    url = "https://google.serper.dev/search"
    
    # We broaden the search to capture all Edinburgh venues
    payload = json.dumps({
        "q": "cinema showtimes Edinburgh Filmhouse Dominion Everyman Vue Odeon",
        "gl": "gb",
        "hl": "en"
    })
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    listings = []
    try:
        response = requests.post(url, headers=headers, data=payload)
        results = response.json()
        
        # 1. Check Google's Knowledge Graph (Best for Vue/Odeon)
        if 'knowledgeGraph' in results:
            kg = results['knowledgeGraph']
            for movie in kg.get('attributes', []):
                listings.append({
                    "title": movie.get('label', 'Unknown Film'),
                    "venue": "Various Edinburgh"
                })
        
        # 2. Check Organic Results (Best for Filmhouse/Everyman)
        if 'organic' in results:
            for item in results['organic'][:12]:
                title = item.get('title', '')
                # Filter for things that look like movie titles or cinema pages
                if any(x in title.lower() for x in ['filmhouse', 'dominion', 'everyman', 'vue']):
                    listings.append({
                        "title": title.split(' - ')[0], 
                        "venue": "Theater Feed"
                    })

    except Exception as e:
        listings = [{"title": f"Search Error: {e}", "venue": "System"}]
        
    return listings

if __name__ == "__main__":
    data = get_google_listings()
    with open('listings.json', 'w') as f:
        json.dump(data, f, indent=2)
