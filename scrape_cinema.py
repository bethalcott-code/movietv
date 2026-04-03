import requests
import json

def get_google_listings():
    # YOUR KEY IS NOW INTEGRATED
    api_key = "cabfbdda7799cd435ca95f62e27e8c2d886f32a6"
    url = "https://google.serper.dev/search"
    
    payload = json.dumps({
        "q": "movie showtimes Edinburgh",
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
        
        # Google provides a 'knowledgeGraph' for local showtimes
        if 'knowledgeGraph' in results:
            kg = results['knowledgeGraph']
            # We look for the 'attributes' which contain the movie titles
            for movie in kg.get('attributes', []):
                listings.append({
                    "title": movie.get('label', 'Unknown Film'),
                    "venue": "Edinburgh Showtimes"
                })
        
        # If Knowledge Graph is empty, we check the organic results for titles
        if not listings and 'organic' in results:
            for item in results['organic'][:8]:
                listings.append({
                    "title": item.get('title', 'Check Cinema Website'),
                    "venue": "Search Result"
                })

    except Exception as e:
        listings = [{"title": f"Search Error: {e}", "venue": "System"}]
        
    return listings

if __name__ == "__main__":
    data = get_google_listings()
    with open('listings.json', 'w') as f:
        json.dump(data, f, indent=2)
