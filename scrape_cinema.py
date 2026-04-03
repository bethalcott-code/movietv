import requests
from bs4 import BeautifulSoup
import json

def get_listings():
    listings = []
    # Targeting the main 'What's On' feed for Edinburgh Picturehouses
    url = "https://www.picturehouses.com/whats-on/edinburg" 
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for movie titles in the 'movie-title' class
        for film in soup.select('.movie-title'):
            title_text = film.get_text().strip()
            if title_text and len(listings) < 15:
                listings.append({
                    "title": title_text,
                    "venue": "Cameo",
                })
    except Exception as e:
        print(f"Error scraping: {e}")
        
    return listings

if __name__ == "__main__":
    data = get_listings()
    # If we found nothing, let's at least put a 'Service Active' message
    if not data:
        data = [{"title": "Check Cinema Website", "venue": "Feed updating"}]
    
    with open('listings.json', 'w') as f:
        json.dump(data, f, indent=2)
