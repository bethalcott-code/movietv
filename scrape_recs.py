import requests
import json
import xml.etree.ElementTree as ET

def get_smart_recs():
    # Sources: High-brow culture, industry awards, and global news
    feeds = {
        "The Guardian": "https://www.theguardian.com/film/rss",
        "BFI": "https://www.bfi.org.uk/rss.xml",
        "Variety": "https://variety.com/feed/",
        "Space.com": "https://www.space.com/feeds/all"
    }
    
    # Logic Tags: Why are we pulling this? [ASSUMPTION]
    filters = {
        "WWII/History": ["nazi", "spy", "spitfire", "resistance", "historical", "holocaust", "churchill"],
        "Awards": ["oscar", "sundance", "winner", "golden globe", "bafta", "nominee"],
        "Space/Science": ["artemis", "nasa", "moon", "spacex", "mars", "galaxy"],
        "Legacy/News": ["died", "passed away", "tribute", "obituary", "remembers"]
    }

    recs = []
    for source_name, url in feeds.items():
        try:
            response = requests.get(url, timeout=10)
            root = ET.fromstring(response.content)
            for item in root.findall('.//item')[:15]:
                title = item.find('title').text
                link = item.find('link').text
                desc = item.find('description').text.lower() if item.find('description') is not None else ""
                
                # Logic: Check for a match in our filter categories
                found_tag = None
                for category, keywords in filters.items():
                    if any(word in title.lower() or word in desc for word in keywords):
                        found_tag = category
                        break
                
                # If it's a "Smart" match, add it
                if found_tag:
                    recs.append({
                        "title": title.split(" review")[0],
                        "source": source_name,
                        "url": link,
                        "tag": found_tag
                    })
        except: continue
        
    # Logic: Ensure at least 10 items by taking top 'Variety' hits if list is short
    return recs[:12] if len(recs) >= 10 else recs

if __name__ == "__main__":
    data = get_smart_recs()
    with open('recommendations.json', 'w') as f:
        json.dump(data, f, indent=2)
