import requests
import json
import os

def get_listings():
    # Using your provided Master Key as the SerpApi key (Assumed shared)
    # [ASSUMPTION]: You are using the same key/account for SerpApi access.
    api_key = "2a10Lldb6jiELPRlGenC3mNPze71KWmcCM6a4IBBYvmEyoWi9s3maquL6"
    
    # Target Query: Cinema screenings in Edinburgh
    url = f"https://serpapi.com/search.json?q=cinema+showtimes+edinburgh+cameo+filmhouse&api_key={api_key}"
    
    try:
        r = requests.get(url, timeout=20)
        data = r.json()
        
        listings = []
        
        # 1. Look for 'knowledge_graph' movies (The cleanest data)
        if "knowledge_graph" in data and "movies" in data["knowledge_graph"]:
            for m in data["knowledge_graph"]["movies"][:10]:
                listings.append({"title": m.get("name"), "venue": "Cinema Feed"})
        
        # 2. Fallback to 'organic_results' if knowledge graph is empty
        if not listings:
            for res in data.get("organic_results", [])[:8]:
                title = res.get("title", "").split("-")[0].strip()
                listings.append({"title": title, "venue": "Search Result"})
                
        return listings if listings else [{"title": "Updating schedule...", "venue": "System"}]

    except Exception as e:
        print(f"Error: {e}")
        return [{"title": "Feed Error", "venue": "System"}]

if __name__ == "__main__":
    results = get_listings()
    with open('listings.json', 'w') as f:
        json.dump(results, f, indent=2)
