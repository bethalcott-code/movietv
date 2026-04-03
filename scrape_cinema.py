import requests
import json

def get_google_listings():
    api_key = "cabfbdda7799cd435ca95f62e27e8c2d886f32a6"
    url = "https://google.serper.dev/search"
    
    # We target specific venue names in the query
    payload = json.dumps({
        "q": "showtimes today at Cameo Edinburgh, Filmhouse, Dominion, Everyman Edinburgh, Vue Omni",
        "gl": "gb",
        "hl": "en"
    })
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}

    listings = []
    seen_titles = set()

    try:
        response = requests.post(url, headers=headers, data=payload)
        results = response.json()
        
        # We look at the organic links because they often contain the Venue + Title
        if 'organic' in results:
            for item in results['organic'][:20]:
                title_line = item.get('title', '')
                snippet = item.get('snippet', '').lower()
                
                # Logic to identify the venue from the link title or description
                venue = "Edinburgh"
                if "cameo" in title_line.lower() or "cameo" in snippet: venue = "Cameo"
                elif "filmhouse" in title_line.lower() or "filmhouse" in snippet: venue = "Filmhouse"
                elif "dominion" in title_line.lower() or "dominion" in snippet: venue = "Dominion"
                elif "everyman" in title_line.lower() or "everyman" in snippet: venue = "Everyman"
                elif "vue" in title_line.lower() or "vue" in snippet: venue = "Vue (Omni)"

                # Extract the movie title (usually before the first dash or pipe)
                clean_title = title_line.split(' - ')[0].split(' | ')[0].split(': ')[-1].strip()
                
                # Add to list if it's a unique movie for that venue
                unique_key = f"{clean_title}-{venue}"
                if len(clean_title) > 3 and unique_key not in seen_titles:
                    listings.append({"title": clean_title, "venue": venue})
                    seen_titles.add(unique_key)

    except Exception as e:
        listings = [{"title": f"Search Error: {e}", "venue": "System"}]
        
    return listings

if __name__ == "__main__":
    data = get_google_listings()
    with open('listings.json', 'w') as f:
        json.dump(data, f, indent=2)
