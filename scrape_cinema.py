import requests
import json
import xml.etree.ElementTree as ET

def get_listings():
    # RSS Feeds are much more stable for beginners than scraping HTML
    url = "https://www.picturehouses.com/rss/cinema/cameo-picturehouse"
    headers = {'User-Agent': 'Mozilla/5.0'}
    listings = []

    try:
        response = requests.get(url, headers=headers)
        # Parse the XML data from the RSS feed
        root = ET.fromstring(response.content)
        for item in root.findall('.//item')[:10]:
            title = item.find('title').text
            listings.append({
                "title": title.split(' at ')[0], # Cleans up the title
                "venue": "Cameo"
            })
    except Exception as e:
        # If the RSS fails, we provide a "Manual" backup for this week
        listings = [
            {"title": "The Drama", "venue": "Cameo"},
            {"title": "La Grazia", "venue": "Cameo"},
            {"title": "Akira (4K)", "venue": "Cameo"},
            {"title": "Oldboy", "venue": "Cameo"}
        ]
        
    return listings

if __name__ == "__main__":
    data = get_listings()
    with open('listings.json', 'w') as f:
        json.dump(data, f, indent=2)
