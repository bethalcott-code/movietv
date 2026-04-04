import requests
import json
import os

# Ensure this secret is set in GitHub Settings > Secrets
SERPER_KEY = os.getenv("SERPER_KEY") 

def get_cinema():
    url = "https://google.serper.dev/search"
    # Query logic: 'movie showtimes' is more reliable than 'movies playing' [ASSUMPTION]
    payload = json.dumps({
        "q": "movie showtimes Edinburgh today",
        "gl": "gb", "hl": "en"
    })
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}

    try:
        res = requests.post(url, headers=headers, data=payload).json()
        listings = []
        
        # Check for structured movie block
        if 'movies' in res:
            for m in res['movies']:
                for c in m.get('cinemas', []):
                    listings.append({
                        "venue": c.get('name', 'EDINBURGH').upper(),
                        "title": m.get('name', 'UNKNOWN').upper(),
                        "times": ", ".join(c.get('showtimes', [])[:5]),
                        "tag": "LIVE",
                        "url": c.get('link', '#')
                    })
        
        print(f"Robot found {len(listings)} movies.")
        
        with open('listings.json', 'w') as f:
            json.dump(listings, f, indent=2)
            
    except Exception as e:
        print(f"Scraper Error: {e}")

if __name__ == "__main__":
    get_cinema()
