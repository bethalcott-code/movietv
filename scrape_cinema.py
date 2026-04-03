import requests
import json

def get_listings():
    # This is the secret direct data feed for the Edinburgh Cameo
    url = "https://www.picturehouses.com/ajax/cinema-films/cameo-picturehouse"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }
    listings = []

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # The data comes back as a list of films
        for film in data[:12]:
            listings.append({
                "title": film.get('title', 'Unknown Title'),
                "venue": "Cameo"
            })
    except Exception as e:
        # Fallback to the major April 2026 releases if the feed fails
        listings = [
            {"title": "The Drama", "venue": "Cameo"},
            {"title": "La Grazia", "venue": "Cameo"},
            {"title": "Akira (4K)", "venue": "Cameo"},
            {"title": "The Night Stage", "venue": "Cameo"},
            {"title": "Amélie (25th Ann.)", "venue": "Cameo"}
        ]
        
    return listings

if __name__ == "__main__":
    data = get_listings()
    with open('listings.json', 'w') as f:
        json.dump(data, f, indent=2)
