import requests
import json
import os

# Securely pull the key from GitHub Secrets
SERPER_KEY = os.getenv("SERPER_KEY") 

def get_edinburgh_cinema():
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": "movies playing in Edinburgh today showtimes",
        "gl": "gb", "hl": "en"
    })
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}

    try:
        res = requests.post(url, headers=headers, data=payload).json()
        listings = []
        if 'movies' in res:
            for m in res['movies']:
                for c in m.get('cinemas', []):
                    # Standardizing ingredients for the UI
                    listings.append({
                        "venue": c.get('name', 'EDINBURGH').upper(),
                        "title": m.get('name', 'UNKNOWN').upper(),
                        "times": ", ".join(c.get('showtimes', [])[:5]),
                        "tag": "LIVE",
                        "url": c.get('link', '#')
                    })
        
        # Save to the file the index.html reads
        with open('listings.json', 'w') as f:
            json.dump(listings[:30], f, indent=2)
            
    except Exception as e:
        print(f"Update failed: {e}")

if __name__ == "__main__":
    get_edinburgh_cinema()
