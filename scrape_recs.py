import requests
import json
import xml.etree.ElementTree as ET

def get_smart_recs():
    # Expanded feeds to include TV and more depth
    feeds = {
        "The Guardian": "https://www.theguardian.com/tv-and-radio/rss",
        "BFI": "https://www.bfi.org.uk/rss.xml",
        "Empire": "https://www.empireonline.com/global/rss/"
    }
    
    keywords = ["nazi", "spy", "wwii", "espionage", "thriller", "historical", "series", "season"]
    smart_recs = []

    for name, url in feeds.items():
        try:
            response = requests.get(url, timeout=10)
            root = ET.fromstring(response.content)
            for item in root.findall('.//item')[:15]:
                title = item.find('title').text
                link = item.find('link').text
                desc = item.find('description').text.lower() if item.find('description') is not None else ""
                
                if any(word in desc or word in title.lower() for word in keywords):
                    smart_recs.append({
                        "title": title.split(" review")[0],
                        "source": name,
                        "url": link,
                        "type": "TV" if "season" in desc or "episode" in desc else "Movie"
                    })
        except: continue
    return smart_recs

if __name__ == "__main__":
    recs = get_smart_recs()
    with open('recommendations.json', 'w') as f:
        json.dump(recs, f, indent=2)
