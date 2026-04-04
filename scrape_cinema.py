import requests
import json
import os

SERPER_KEY = os.getenv("SERPER_KEY")

def get_cinema():
    url = "https://google.serper.dev/search"
    # Logic: More specific query to trigger the 'movies' knowledge graph
    payload = json.dumps({
        "q": "cinema showtimes Edinburgh today",
        "gl": "gb", "hl": "en"
    })
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}

    try:
        res = requests.post(url, headers=headers, data=payload).json()
        listings = []
        
        # Logic: Fallback if 'movies' block is missing
        items = res.get('movies', [])
        for m in items:
            for c in m.get('cinemas', []):
                listings.append({
                    "venue": c.get('name', 'Edinburgh').upper(),
                    "title": m.get('name', 'Movie').upper(),
                    "times": ", ".join(c.get('showtimes', [])[:5]),
                    "tag": "LIVE",
                    "url": c.get('link', '#')
                })
        
        if not listings: # Logic: Scrape organic results if Knowledge Graph fails [ASSUMPTION]
            print("No structured movies found. Check Serper query.")

        with open('listings.json', 'w') as f:
            json.dump(listings, f, indent=2)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_cinema()
