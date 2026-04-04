import requests
import json
import os

SERPER_KEY = os.getenv("SERPER_KEY")

# Query one per venue to get full listings rather than Google's one-film-per-cinema block
EDINBURGH_VENUES = [
    "Cameo Cinema Edinburgh",
    "Filmhouse Cinema Edinburgh",
    "Everyman Cinema Edinburgh",
    "Cineworld Edinburgh Fountainpark",
    "Odeon Lothian Road Edinburgh",
    "Vue Edinburgh Omni Centre",
]

# Tags we want to surface on matching films
INTEREST_TAGS = {
    "nazi": "Anti-Nazi", "resistance": "Anti-Nazi", "occupation": "Anti-Nazi",
    "spy": "Spy", "espionage": "Spy", "cold war": "Spy",
    "wwii": "WWII", "world war": "WWII",
    "powell": "Powell & Pressburger", "pressburger": "Powell & Pressburger",
    "criterion": "Criterion",
    "repertory": "Repertory", "classic": "Classic",
    "documentary": "Documentary",
    "arthouse": "Arthouse", "art house": "Arthouse",
}

def tag_film(title, description=""):
    text = (title + " " + description).lower()
    tags = []
    for keyword, tag in INTEREST_TAGS.items():
        if keyword in text and tag not in tags:
            tags.append(tag)
    return tags

def search_venue(venue_name):
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": f"what's on at {venue_name} this week showtimes",
        "gl": "gb",
        "hl": "en",
        "num": 20
    })
    headers = {"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"}
    try:
        res = requests.post(url, headers=headers, data=payload, timeout=15).json()
        films = []

        # Google structured movie block — multiple films per cinema when queried by venue
        if "movies" in res:
            for m in res["movies"]:
                for c in m.get("cinemas", []):
                    # Only include if venue name roughly matches
                    if any(word.lower() in c.get("name","").lower()
                           for word in venue_name.split()[:2]):
                        showtimes = c.get("showtimes", [])
                        films.append({
                            "venue": c.get("name", venue_name).upper(),
                            "title": m.get("name", "UNKNOWN"),
                            "year": str(m.get("year", "")),
                            "times": ", ".join(showtimes[:8]),
                            "tags": tag_film(m.get("name",""), m.get("description","")),
                            "url": c.get("link", "#"),
                            "desc": (m.get("description","") or "")[:120],
                        })

        # Fallback: organic results for this venue
        if not films and "organic" in res:
            for r in res["organic"][:8]:
                t = r.get("title","")
                if any(word.lower() in t.lower() for word in ["showing","on now","listings","what's on","cinema"]):
                    continue
                films.append({
                    "venue": venue_name.upper(),
                    "title": t.split(" - ")[0].split(" | ")[0],
                    "times": "",
                    "tags": tag_film(t),
                    "url": r.get("link","#"),
                    "desc": r.get("snippet","")[:120],
                })

        return films
    except Exception as e:
        print(f"  Error searching {venue_name}: {e}")
        return []

def get_cinema():
    if not SERPER_KEY:
        print("ERROR: SERPER_KEY secret not set.")
        return

    all_listings = []
    seen = set()  # deduplicate by venue+title

    for venue in EDINBURGH_VENUES:
        print(f"Searching: {venue}...")
        films = search_venue(venue)
        print(f"  Found {len(films)} films")
        for film in films:
            key = f"{film['venue']}::{film['title'].lower()}"
            if key not in seen:
                seen.add(key)
                all_listings.append(film)

    print(f"\nTotal listings: {len(all_listings)}")
    with open("listings.json", "w") as f:
        json.dump(all_listings, f, indent=2, ensure_ascii=False)
    print("Saved listings.json")

if __name__ == "__main__":
    get_cinema()
