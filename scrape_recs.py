import requests
import json
import xml.etree.ElementTree as ET

TMDB_KEY = "eb7044678f7a620007e3d11387ccb51f"

def get_streaming(title):
    try:
        # Step 1: Search for the movie/show ID
        search_url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={title}&region=GB"
        res = requests.get(search_url).json()
        if not res.get('results'): return "NOT ON STREAMING"
        
        item = res['results'][0]
        i_id, i_type = item['id'], item['media_type']
        
        # Step 2: Get UK Watch Providers
        prov_url = f"https://api.themoviedb.org/3/{i_type}/{i_id}/watch/providers?api_key={TMDB_KEY}"
        p_res = requests.get(prov_url).json()
        uk = p_res.get('results', {}).get('GB', {})
        
        # Combine Subscription (flatrate) and Free options [ASSUMPTION]
        found = [p['provider_name'] for p in uk.get('flatrate', []) + uk.get('free', [])]
        return ", ".join(found[:2]) if found else "RENT/CINEMA ONLY"
    except: return "CHECK JUSTWATCH"

def get_smart_recs():
    feeds = {
        "The Guardian": "https://www.theguardian.com/film/rss",
        "BFI": "https://www.bfi.org.uk/rss.xml",
        "Variety": "https://variety.com/feed/"
    }
    interests = ["nazi", "spy", "wwii", "espionage", "historical", "awards", "space", "moon", "nasa"]
    results = []

    for source, url in feeds.items():
        try:
            r = requests.get(url, timeout=10)
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:15]:
                t = item.find('title').text
                d = item.find('description').text.lower() if item.find('description') is not None else ""
                if any(w in d or w in t.lower() for w in interests) or "review" in t.lower():
                    clean_t = t.split(" review")[0].replace('“', '').replace('”', '')
                    results.append({
                        "title": clean_t,
                        "source": source,
                        "url": item.find('link').text,
                        "tag": "CRITIC PICK",
                        "streaming": get_streaming(clean_t) # The new logic call
                    })
        except: continue
    return results[:12]

if __name__ == "__main__":
    data = get_smart_recs()
    with open('recommendations.json', 'w') as f:
        json.dump(data, f, indent=2)
