import requests
from bs4 import BeautifulSoup
import json

def get_listings():
    listings = []
    
    # Example: Scraping a generic Edinburgh cinema structure
    # [ASSUMPTION] We target the 'What's On' page of a major Edinburgh cinema
    url = "https://www.picturehouses.com/cinema/cameo-picturehouse" 
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # This looks for film titles in a common web format
        for film in soup.find_all('h3', class_='showing-title')[:10]:
            listings.append({
                "title": film.get_text().strip(),
                "venue": "The Cameo",
                "time": "See website for times"
            })
    except Exception as e:
        print(f"Error scraping: {e}")
        
    return listings

# Save the results to your JSON file
if __name__ == "__main__":
    data = get_listings()
    with open('listings.json', 'w') as f:
        json.dump(data, f, indent=2)
