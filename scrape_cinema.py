"""
scrape_cinema.py — Edinburgh cinema listings
Source: film.datathistle.com — plain HTML, no JS, no auth, all Edinburgh venues.
Venue IDs confirmed from live search April 2026.
Writes listings.json with title, venue, times, tags, desc, streaming.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import os
import time
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

TMDB_KEY = os.getenv("TMDB_KEY")

VENUES = [
    ("524-cameo-cinema-edinburgh",           "Cameo Picturehouse"),
    ("794-filmhouse-edinburgh",              "Edinburgh Filmhouse"),
    ("12758-cineworld-fountainpark-edinburgh","Cineworld Edinburgh"),
    ("16405-odeon-lothian-road-edinburgh",   "Odeon Lothian Road"),
    ("15902-vue-omni-centre-edinburgh",      "Vue Edinburgh Omni"),
    ("15006-vue-ocean-terminal-edinburgh",   "Vue Ocean Terminal"),
    ("132343-everyman-edinburgh",            "Everyman Edinburgh"),
]

BASE = "https://film.datathistle.com/cinema/{slug}/"

PROVIDER_MAP = {
    "BBC iPlayer": "iPlayer", "Netflix": "Netflix",
    "Apple TV Plus": "Apple TV+", "Apple TV+": "Apple TV+",
    "Disney Plus": "Disney+", "Disney+": "Disney+",
    "Amazon Prime Video": "Prime Video", "Amazon Video": "Prime Video",
    "Channel 4": "Channel 4", "ITVX": "ITVX",
    "MUBI": "MUBI", "BFI Player": "BFI Player",
    "Paramount Plus": "Paramount+", "NOW": "NOW",
}

INTEREST_TAGS = {
    "nazi": "Anti-Nazi", "resistance": "Anti-Nazi", "occupied": "Anti-Nazi",
    "gestapo": "Anti-Nazi", "holocaust": "Anti-Nazi",
    "spy": "Spy", "espionage": "Spy", "cold war": "Spy",
    "wwii": "WWII", "world war": "WWII",
    "documentary": "Documentary", "criterion": "Criterion",
    "arthouse": "Arthouse", "scottish": "Scottish", "scotland": "Scottish",
    "classic": "Classic", "revival": "Classic", "repertory": "Classic",
    "bergman": "Bergman", "tati": "Jacques Tati",
    "powell": "Powell & Pressburger",
}

def tag_film(title, synopsis=""):
    text = (title + " " + (synopsis or "")).lower()
    return list({tag for kw, tag in INTEREST_TAGS.items() if kw in text})

def get_streaming_uk(title):
    if not TMDB_KEY:
        return "", ""
    try:
        res = requests.get(
            "https://api.themoviedb.org/3/search/multi"
            f"?api_key={TMDB_KEY}&query={requests.utils.quote(title)}&region=GB",
            timeout=8).json()
        results = res.get("results", [])
        if not results:
            return "", ""
        item = results[0]
        i_id = item["id"]
        i_type = item.get("media_type", "movie")
        if i_type not in ("movie", "tv"):
            i_type = "movie"
        pres = requests.get(
            f"https://api.themoviedb.org/3/{i_type}/{i_id}/watch/providers"
            f"?api_key={TMDB_KEY}",
            timeout=8).json()
        uk = pres.get("results", {}).get("GB", {})
        all_p = uk.get("flatrate", []) + uk.get("free", []) + uk.get("ads", [])
        jw = uk.get("link", "")
        for p in all_p:
            short = PROVIDER_MAP.get(p.get("provider_name", ""), "")
            if short:
                return short, jw
        return (all_p[0].get("provider_name", "") if all_p else ""), jw
    except:
        return "", ""

def scrape_venue(slug, venue_name):
    films = []
    url = BASE.format(slug=slug)
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # datathistle structure: each film is in a section with h3/h4 title
        # followed by day headings (h5) and time links (a.btn or li items)
        # Film blocks are separated by <hr> or are siblings in main content

        # Find all film listing blocks — datathistle uses <h3> or <h4> for film titles
        # with an <a> linking to the film detail page
        current_film = None
        current_desc = ""
        current_times = []
        current_url = ""
        current_year = ""

        # Walk all elements in order
        content = soup.find("main") or soup.find("div", class_=re.compile("content|listing|films"))
        if not content:
            content = soup

        for el in content.find_all(["h3", "h4", "h5", "p", "a", "li", "div"], recursive=False) if content != soup \
                else soup.find_all(["h3", "h4", "h5", "p", "a", "li"]):

            tag = el.name
            text = el.get_text(strip=True)

            # Film title: h3 or h4 with a link to /listing/
            if tag in ("h3", "h4"):
                link = el.find("a", href=re.compile(r"/listing/"))
                if link:
                    # Save previous film
                    if current_film and current_times:
                        films.append({
                            "venue": venue_name,
                            "title": current_film,
                            "times": ", ".join(sorted(set(current_times))[:10]),
                            "tags": tag_film(current_film, current_desc),
                            "desc": current_desc[:150],
                            "url": current_url,
                            "year": current_year,
                        })
                    current_film = link.get_text(strip=True)
                    current_times = []
                    current_desc = ""
                    href = link.get("href", "")
                    current_url = "https://film.datathistle.com" + href if href.startswith("/") else href
                    current_year = ""
                    continue

            # Year/metadata: look for 4-digit year near film title
            if current_film and not current_year:
                m = re.search(r'\b(19|20)\d{2}\b', text)
                if m and not current_times:
                    current_year = m.group(0)

            # Description: <p> after a film title, before times
            if tag == "p" and current_film and not current_times and len(text) > 30:
                if not re.search(r'\d{1,2}[:.]\d{2}', text):
                    current_desc = text[:200]

            # Times: look for time patterns in any element
            if current_film:
                times_found = re.findall(r'\b(\d{1,2}[:.]\d{2})\b', text)
                for t in times_found:
                    # Normalise separator
                    norm = t.replace(".", ":")
                    current_times.append(norm)

        # Save last film
        if current_film and current_times:
            films.append({
                "venue": venue_name,
                "title": current_film,
                "times": ", ".join(sorted(set(current_times))[:10]),
                "tags": tag_film(current_film, current_desc),
                "desc": current_desc[:150],
                "url": current_url,
                "year": current_year,
            })

        # If recursive=False missed things, try a broader approach
        if not films:
            for link in soup.find_all("a", href=re.compile(r"/listing/")):
                title = link.get_text(strip=True)
                if not title or len(title) < 2:
                    continue
                href = link.get("href", "")
                film_url = "https://film.datathistle.com" + href if href.startswith("/") else href
                # Look for times near this link
                parent = link.find_parent()
                times = []
                for sib in parent.find_next_siblings()[:10]:
                    t = re.findall(r'\b(\d{1,2}[:.]\d{2})\b', sib.get_text())
                    times.extend(t)
                    if times and not t:
                        break
                if times:
                    films.append({
                        "venue": venue_name,
                        "title": title,
                        "times": ", ".join(sorted(set(times[:10]))[:10]),
                        "tags": tag_film(title),
                        "desc": "",
                        "url": film_url,
                        "year": "",
                    })

        print(f"  {venue_name}: {len(films)} films")
    except Exception as e:
        print(f"  {venue_name} error: {e}")
    return films


def get_cinema():
    print(f"Scraping Edinburgh cinemas via datathistle.com — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    all_listings = []
    seen = set()

    for slug, venue_name in VENUES:
        try:
            films = scrape_venue(slug, venue_name)
            for film in films:
                key = f"{film['venue']}::{film['title'].lower().strip()}"
                if key not in seen and len(film["title"]) > 2:
                    seen.add(key)
                    all_listings.append(film)
        except Exception as e:
            print(f"  {venue_name} scraper failed: {e}")
        time.sleep(0.5)  # be polite

    all_listings.sort(key=lambda x: (x["venue"], x["title"]))
    print(f"\nTotal before streaming lookup: {len(all_listings)} entries")

    # TMDB streaming lookup — deduplicate by title
    if TMDB_KEY and all_listings:
        print("Looking up UK streaming availability via TMDB...")
        title_cache = {}
        for item in all_listings:
            t = item["title"].lower()
            if t not in title_cache:
                streaming, jw = get_streaming_uk(item["title"])
                title_cache[t] = (streaming, jw)
                time.sleep(0.2)
            item["streaming"] = title_cache[t][0]
            item["jw_url"] = title_cache[t][1]
        print("Streaming lookup done.")
    else:
        for item in all_listings:
            item.setdefault("streaming", "")
            item.setdefault("jw_url", "")
        if not TMDB_KEY:
            print("TMDB_KEY not set — skipping streaming lookup.")

    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(all_listings, f, indent=2, ensure_ascii=False)
    print(f"Saved listings.json — {len(all_listings)} entries")


if __name__ == "__main__":
    get_cinema()
