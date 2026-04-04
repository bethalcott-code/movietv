"""
scrape_cinema.py — Edinburgh cinema listings
Scrapes britinfo.net which aggregates all Edinburgh venue listings.
No API key required. Writes listings.json grouped by venue.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

import os
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

TMDB_KEY = os.getenv("TMDB_KEY")

PROVIDER_MAP = {
    "BBC iPlayer": "iPlayer", "Netflix": "Netflix",
    "Apple TV Plus": "Apple TV+", "Apple TV+": "Apple TV+",
    "Disney Plus": "Disney+", "Disney+": "Disney+",
    "Amazon Prime Video": "Prime Video", "Amazon Video": "Prime Video",
    "Channel 4": "Channel 4", "ITVX": "ITVX",
    "MUBI": "MUBI", "BFI Player": "BFI Player",
    "Paramount Plus": "Paramount+", "NOW": "NOW",
}

def get_streaming_uk(title):
    if not TMDB_KEY:
        return "", ""
    try:
        q = requests.utils.quote(title)
        res = requests.get(
            f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={q}&region=GB",
            timeout=8).json()
        results = res.get("results", [])
        if not results:
            return "", ""
        item = results[0]
        i_id, i_type = item["id"], item.get("media_type","movie")
        if i_type not in ("movie","tv"):
            i_type = "movie"
        pres = requests.get(
            f"https://api.themoviedb.org/3/{i_type}/{i_id}/watch/providers?api_key={TMDB_KEY}",
            timeout=8).json()
        uk = pres.get("results",{}).get("GB",{})
        all_p = uk.get("flatrate",[]) + uk.get("free",[]) + uk.get("ads",[])
        jw = uk.get("link","")
        for p in all_p:
            short = PROVIDER_MAP.get(p.get("provider_name",""),"")
            if short:
                return short, jw
        return (all_p[0].get("provider_name","") if all_p else ""), jw
    except:
        return "", ""

VENUE_URLS = {
    "Cameo Picturehouse":    "https://www.britinfo.net/cinema/cinema-listings-1003620.htm",
    "Edinburgh Filmhouse":   "https://www.britinfo.net/cinema/cinema-listings-1003611.htm",
    "Cineworld Edinburgh":   "https://www.britinfo.net/cinema/cinema-listings-1003617.htm",
    "Odeon Lothian Road":    "https://www.britinfo.net/cinema/cinema-listings-1003613.htm",
    "Vue Edinburgh Omni":    "https://www.britinfo.net/cinema/cinema-listings-1003615.htm",
    "Everyman Edinburgh":    "https://www.britinfo.net/cinema/cinema-listings-1054321.htm",
}

INTEREST_TAGS = {
    "nazi": "Anti-Nazi", "resistance": "Anti-Nazi", "occupation": "Anti-Nazi",
    "gestapo": "Anti-Nazi", "holocaust": "Anti-Nazi",
    "spy": "Spy", "espionage": "Spy", "cold war": "Spy", "mi5": "Spy", "mi6": "Spy",
    "wwii": "WWII", "world war": "WWII", "second world war": "WWII",
    "documentary": "Documentary",
    "criterion": "Criterion",
    "arthouse": "Arthouse", "art house": "Arthouse",
    "silent": "Silent",
    "scottish": "Scottish", "scotland": "Scottish",
    "repertory": "Classic", "revival": "Classic", "classic": "Classic",
    "bergman": "Bergman", "tati": "Jacques Tati",
    "powell": "Powell & Pressburger", "pressburger": "Powell & Pressburger",
}

def tag_film(title, synopsis=""):
    text = (title + " " + (synopsis or "")).lower()
    tags = []
    for kw, tag in INTEREST_TAGS.items():
        if kw in text and tag not in tags:
            tags.append(tag)
    return tags

def scrape_venue(venue_name, url):
    films = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # britinfo.net structure: films listed as table rows or divs
        # Each film typically has title + showtimes in adjacent cells/divs
        # Try multiple selector strategies

        # Strategy 1: look for film listing tables
        current_film = None
        current_times = []

        # britinfo uses a consistent pattern: film title in bold/strong, times follow
        for tag in soup.find_all(["b", "strong", "h3", "h4", "td", "div"]):
            text = tag.get_text(strip=True)
            if not text or len(text) < 2:
                continue

            # Detect time patterns like "15:30" "3:30 PM" "15:30, 18:00"
            time_pattern = re.compile(r'\b\d{1,2}[:.]\d{2}(?:\s*[AP]M)?\b')
            times_found = time_pattern.findall(text)

            # Is this a film title? (not just times, not nav/ui text)
            if (len(text) > 3 and len(text) < 100
                    and not times_found
                    and not any(skip in text.lower() for skip in [
                        "cinema", "tickets", "book", "buy", "find", "sponsored",
                        "listings", "all ", "contact", "home", "back", "next",
                        "showing", "week", "today", "film guide"
                    ])
                    and re.search(r'[A-Z]', text)  # has uppercase = likely a title
                    and tag.name in ["b", "strong", "h3", "h4"]):

                # Save previous film if we have one
                if current_film and current_film not in [f["title"] for f in films]:
                    films.append({
                        "venue": venue_name,
                        "title": current_film,
                        "times": ", ".join(current_times[:8]),
                        "tags": tag_film(current_film),
                        "desc": "",
                        "url": url,
                        "year": "",
                    })
                current_film = text
                current_times = []

            elif times_found and current_film:
                current_times.extend(times_found[:8])

        # Save last film
        if current_film and current_film not in [f["title"] for f in films]:
            films.append({
                "venue": venue_name,
                "title": current_film,
                "times": ", ".join(current_times[:8]),
                "tags": tag_film(current_film),
                "desc": "",
                "url": url,
                "year": "",
            })

        # Strategy 2: if strategy 1 got nothing, try a broader text scan
        if not films:
            # Look for any text that looks like a film title followed by times
            full_text = soup.get_text(separator="\n")
            lines = [l.strip() for l in full_text.split("\n") if l.strip()]
            i = 0
            while i < len(lines):
                line = lines[i]
                times_in_line = re.findall(r'\b\d{1,2}[:.]\d{2}(?:\s*[AP]M)?\b', line)
                # A film title: 3-80 chars, mixed case, no times, no nav text
                if (3 < len(line) < 80
                        and not times_in_line
                        and re.search(r'[A-Z][a-z]', line)
                        and not any(skip in line.lower() for skip in [
                            "cinema", "book", "buy", "home", "back", "contact",
                            "sponsored", "listings", "all cinemas"
                        ])):
                    # Look ahead for times
                    times = []
                    for j in range(i+1, min(i+5, len(lines))):
                        t = re.findall(r'\b\d{1,2}[:.]\d{2}(?:\s*[AP]M)?\b', lines[j])
                        if t:
                            times.extend(t)
                        elif times:
                            break
                    if times:  # only add if we found times (confirms it's a film)
                        films.append({
                            "venue": venue_name,
                            "title": line,
                            "times": ", ".join(times[:8]),
                            "tags": tag_film(line),
                            "desc": "",
                            "url": url,
                            "year": "",
                        })
                i += 1

        print(f"  {venue_name}: {len(films)} films")
    except Exception as e:
        print(f"  {venue_name} error: {e}")
    return films


def get_cinema():
    print(f"Scraping Edinburgh cinemas — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    all_listings = []
    seen = set()

    for venue_name, url in VENUE_URLS.items():
        films = scrape_venue(venue_name, url)
        for film in films:
            key = f"{film['venue']}::{film['title'].lower().strip()}"
            if key not in seen and len(film["title"]) > 2:
                seen.add(key)
                all_listings.append(film)

    all_listings.sort(key=lambda x: (x["venue"], x["title"]))
    print(f"\nTotal: {len(all_listings)} film/venue entries")

    # Enrich with UK streaming data via TMDB
    if TMDB_KEY:
        print("Looking up UK streaming availability...")
        seen_titles = {}
        for item in all_listings:
            t = item["title"].lower()
            if t in seen_titles:
                item["streaming"] = seen_titles[t][0]
                item["jw_url"]    = seen_titles[t][1]
            else:
                streaming, jw = get_streaming_uk(item["title"])
                item["streaming"] = streaming
                item["jw_url"]    = jw
                seen_titles[t]    = (streaming, jw)
                time.sleep(0.2)
        print("Streaming lookup complete.")
    else:
        print("TMDB_KEY not set — skipping streaming lookup.")

    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(all_listings, f, indent=2, ensure_ascii=False)
    print("Saved listings.json")


if __name__ == "__main__":
    get_cinema()
