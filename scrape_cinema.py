import requests
from bs4 import BeautifulSoup
import json

def get_listings():
    listings = []
    # Target: Cameo / Picturehouse Edinburgh
    url = "https://www.picturehouses.com/cinema/cameo-picturehouse"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Look for the specific 'booking-title' class used on Picturehouse sites
        films = soup.find_all(['h3', 'span'], class_=['showing-title', 'booking-title'])
        
        for f in films[:15]:
            title = f.get_text().strip()
            if title and len(title) > 2:
                listings.append({"title": title, "venue": "The Cameo"})
                
        # If still empty, a fallback search for any bold titles
        if not listings:
            for b in soup.find_all('b')[:10]:
                listings.append({"title": b.get_text().strip(), "venue": "Cameo Fallback"})
                
    except Exception as e:
        print(f"Error: {e}")
        
    return listings if listings else [{"title": "No titles found - check scraper logic", "venue": "System"}]

if __name__ == "__main__":
    data = get_listings()
    with open('listings.json', 'w') as f:
        json.dump(data, f, indent=2)
