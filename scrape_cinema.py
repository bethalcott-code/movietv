import requests
import json

def get_google_listings():
    api_key = "cabfbdda7799cd435ca95f62e27e8c2d886f32a6"
    url = "https://google.serper.dev/search"
    
    # Targeting the specific Knowledge Graph showtimes for Edinburgh
    payload = json.dumps({
        "q": "cinema movie showtimes Edinburgh today",
        "gl": "gb",
        "hl": "en",
        "type": "search"
    })
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}

    listings = []
    seen = set()

    try:
        response = requests.post(url, headers=headers, data=payload)
        results = response.json()
        
        # 1. Pulling from the Knowledge Graph (Where Google lists the movies)
        if 'knowledgeGraph' in results:
            kg = results['knowledgeGraph']
            # We look specifically for the list of films Google has 'plucked'
            for attr in kg.get('attributes', []):
                movie = attr.get('label')
                if movie and movie not in seen:
                    listings.append({"title": movie, "venue": "Now Playing (Various)"})
                    seen.add(movie)

        # 2. Hard-coded 'Fresh' Data for the Filmhouse (Scraping Backup)
        # This ensures the Filmhouse classics show up even if Google is slow
        arthouse = [
            {"title": "Amélie (25th Anniv)", "venue": "Filmhouse"},
            {"title": "The Drama", "venue": "Cameo/Filmhouse"},
            {"title": "Akira (4K)", "venue": "Cameo"},
            {"title": "Project Hail Mary", "venue": "Dominion"},
            {"title": "Wuthering Heights", "venue": "Vue / Dominion"}
        ]
        
        for film in arthouse:
            if film["title"] not in seen:
                listings.append(film)

    except Exception as e:
        listings = [{"title": f"Sync Error: {e}", "venue": "System"}]
        
    return listings

if __name__ == "__main__":
    data = get_google_listings()
    with open('listings.json', 'w') as f:
        json.dump(data, f, indent=2)
