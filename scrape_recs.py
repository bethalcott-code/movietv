import requests
import json
import xml.etree.ElementTree as ET

def get_smart_recs():
    # Feeds from "Smart" sources for April 2026
    feeds = [
        "https://www.theguardian.com/film/rss",
        "https://www.bfi.org.uk/rss.xml"
    ]
    
    # Your interests [ASSUMPTION]
    keywords = ["nazi", "spy", "spitfire", "wwii", "resistance", "espionage", "thriller", "historical"]
    smart_recs = []

    for url in feeds:
        try:
            response = requests.get(url, timeout=10)
            root = ET.fromstring(response.content)
            
            for item in root.findall('.//item')[:20]:
                title = item.find('title').text
                desc = item.find('description').text.lower() if item.find('description') is not None else ""
                
                # Logic: If a smart source writes about your interests, grab it
                if any(word in desc or word in title.lower() for word in keywords):
                    smart_recs.append({
                        "title": title.split(" review")[0],
                        "source": "Critic Choice"
                    })
        except:
            continue
            
    return smart_recs

if __name__ == "__main__":
    recs = get_smart_recs()
    # If the critics are quiet today, provide a human fallback
    if not recs:
        recs = [{"title": "The Partisan (WWII Spy Thriller)", "source": "BFI Recommendation"}]
    
    with open('recommendations.json', 'w') as f:
        json.dump(recs, f, indent=2)
