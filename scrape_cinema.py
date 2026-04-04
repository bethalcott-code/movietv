"""
scrape_cinema.py — Edinburgh cinema listings via film.datathistle.com
Structure confirmed from live HTML April 2026:
  - Film titles in <h4><a href="/listing/...">Title</a></h4>
  - Day headings in <h5>
  - Times in <li><a title="3:25pm"> or <li><a>15:25</a>
  - Strikethrough <li><del> = past screenings (skip)
  - Description in <p> after film metadata
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
                  "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

TMDB_KEY = os.getenv("TMDB_KEY")

VENUES = [
    ("524-cameo-cinema-edinburgh",            "Cameo Picturehouse"),
    ("794-filmhouse-edinburgh",               "Edinburgh Filmhouse"),
    ("12758-cineworld-fountainpark-edinburgh", "Cineworld Edinburgh"),
    ("16405-odeon-lothian-road-edinburgh",    "Odeon Lothian Road"),
    ("15902-vue-omni-centre-edinburgh",       "Vue Edinburgh Omni"),
    ("15006-vue-ocean-terminal-edinburgh",    "Vue Ocean Terminal"),
    ("132343-everyman-edinburgh",             "Everyman Edinburgh"),
]

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
    "nazi": "Anti-Nazi", "resistance": "Anti-Nazi", "gestapo": "Anti-Nazi",
    "holocaust": "Anti-Nazi", "spy": "Spy", "espionage": "Spy",
    "cold war": "Spy", "wwii": "WWII", "world war": "WWII",
    "documentary": "Documentary", "criterion": "Criterion",
    "arthouse": "Arthouse", "scottish": "Scottish", "scotland": "Scottish",
    "bergman": "Bergman", "tati": "Tati", "powell": "Powell & Pressburger",
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
        i_id, i_type = item["id"], item.get("media_type", "movie")
        if i_type not in ("movie", "tv"):
            i_type = "movie"
        pres = requests.get(
            f"https://api.themoviedb.org/3/{i_type}/{i_id}/watch/providers"
            f"?api_key={TMDB_KEY}", timeout=8).json()
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

def parse_time(el):
    """Extract HH:MM from an <a> element — check title attr first, then text."""
    title_attr = el.get("title", "")
    # title attr like "3:25pm" or "11am"
    m = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)?', title_attr, re.I)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if m.group(3) and m.group(3).lower() == "pm" and h != 12:
            h += 12
        return f"{h:02d}:{mi:02d}"
    # fallback: link text like "15:25"
    txt = el.get_text(strip=True)
    m2 = re.search(r'(\d{1,2})[:.:](\d{2})', txt)
    if m2:
        return f"{int(m2.group(1)):02d}:{m2.group(2)}"
    return None

def scrape_venue(slug, venue_name):
    films = []
    url = f"https://film.datathistle.com/cinema/{slug}/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Find the times section — it starts after the <a id="times"> anchor
        times_anchor = soup.find("a", id="times") or soup.find("h2", string=re.compile("This week", re.I))

        # Get all h4 elements that are film titles (contain /listing/ links)
        film_headers = []
        for h4 in soup.find_all("h4"):
            link = h4.find("a", href=re.compile(r"/listing/|/event/"))
            if link:
                film_headers.append((h4, link))

        for h4, link in film_headers:
            title = link.get_text(strip=True)
            href = link.get("href", "")
            film_url = ("https://film.datathistle.com" + href
                        if href.startswith("/") else href)

            # Get description: find the <p> sibling after this h4
            desc = ""
            year = ""
            # Walk siblings until next h4
            sib = h4.find_next_sibling()
            while sib and sib.name != "h4":
                if sib.name == "p" and not desc:
                    txt = sib.get_text(strip=True)
                    if len(txt) > 20 and not re.search(r'\d{1,2}[:.]\d{2}', txt):
                        desc = txt[:200]
                # Year: look in metadata lists
                if sib.name == "ul":
                    for li in sib.find_all("li"):
                        m = re.match(r'^(19|20)\d{2}$', li.get_text(strip=True))
                        if m:
                            year = li.get_text(strip=True)
                            break
                sib = sib.find_next_sibling()

            # Collect times from all h5+list sections after this h4, until next h4
            all_times = []
            sib = h4.find_next_sibling()
            while sib and sib.name != "h4":
                if sib.name in ("h5", "h6", "ul", "ol", "div"):
                    # Find all <li> items — skip strikethrough (<del> = past)
                    for li in sib.find_all("li"):
                        if li.find("del") or li.find("s"):
                            continue  # past screening
                        a = li.find("a")
                        if a:
                            t = parse_time(a)
                            if t:
                                all_times.append(t)
                        else:
                            # plain <li> with time text
                            txt = li.get_text(strip=True)
                            m = re.search(r'(\d{1,2})[:.:](\d{2})', txt)
                            if m and not li.find("del"):
                                all_times.append(f"{int(m.group(1)):02d}:{m.group(2)}")
                sib = sib.find_next_sibling()

            if all_times or True:  # include even if no current times (film exists this week)
                films.append({
                    "venue": venue_name,
                    "title": title,
                    "times": ", ".join(sorted(set(all_times))[:10]),
                    "tags": tag_film(title, desc),
                    "desc": desc[:150],
                    "url": film_url,
                    "year": year,
                })

        print(f"  {venue_name}: {len(films)} films")
    except Exception as e:
        print(f"  {venue_name} error: {e}")
    return films


def get_cinema():
    print(f"Scraping Edinburgh cinemas — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
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
            print(f"  {venue_name} failed: {e}")
        time.sleep(0.5)

    all_listings.sort(key=lambda x: (x["venue"], x["title"]))
    print(f"\nTotal: {len(all_listings)} entries")

    if TMDB_KEY and all_listings:
        print("Looking up UK streaming via TMDB...")
        cache = {}
        for item in all_listings:
            t = item["title"].lower()
            if t not in cache:
                cache[t] = get_streaming_uk(item["title"])
                time.sleep(0.2)
            item["streaming"], item["jw_url"] = cache[t]
        print("Done.")
    else:
        for item in all_listings:
            item.setdefault("streaming", "")
            item.setdefault("jw_url", "")

    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(all_listings, f, indent=2, ensure_ascii=False)
    print(f"Saved listings.json — {len(all_listings)} entries")


if __name__ == "__main__":
    get_cinema()
