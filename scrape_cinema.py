"""
scrape_cinema.py
Scrapes Edinburgh cinema websites directly for reliable film+showtime data.
Runs via GitHub Actions (see .github/workflows/).
Writes listings.json grouped by venue.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

INTEREST_TAGS = {
    "nazi": "Anti-Nazi", "resistance": "Anti-Nazi", "occupation": "Anti-Nazi",
    "gestapo": "Anti-Nazi", "holocaust": "Anti-Nazi", "wartime": "WWII",
    "spy": "Spy", "espionage": "Spy", "cold war": "Spy", "intelligence agency": "Spy",
    "wwii": "WWII", "world war": "WWII", "1940s": "WWII",
    "documentary": "Documentary", "criterion": "Criterion",
    "arthouse": "Arthouse", "art house": "Arthouse",
    "silent": "Silent", "synthesizer": "Synthesizers", "synth": "Synthesizers",
    "bergman": "Bergman", "tati": "Jacques Tati", "fellini": "Fellini",
    "repertory": "Repertory", "classic": "Classic", "revival": "Classic",
    "scottish": "Scottish", "scotland": "Scottish",
}

def tag_film(title, description=""):
    text = (title + " " + (description or "")).lower()
    tags = []
    for kw, tag in INTEREST_TAGS.items():
        if kw in text and tag not in tags:
            tags.append(tag)
    return tags

# ── CAMEO (Picturehouse) ──────────────────────────────────────────────────
def scrape_cameo():
    results = []
    try:
        url = "https://www.picturehouses.com/cinema/the-cameo/whats-on"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        # Picturehouse uses film listing cards
        for card in soup.select(".film-listing, .whats-on-film, article.film, .listing-film"):
            title_el = card.select_one("h2, h3, .film-title, .listing-title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 2:
                continue

            # Showtimes
            times = []
            for t in card.select(".showtime, .time, time, .performance-time")[:10]:
                txt = t.get_text(strip=True)
                if re.match(r'\d{1,2}[:.]\d{2}', txt):
                    times.append(txt)

            desc = ""
            desc_el = card.select_one(".synopsis, .description, p")
            if desc_el:
                desc = desc_el.get_text(strip=True)[:150]

            film_url = ""
            link = card.select_one("a[href]")
            if link:
                href = link["href"]
                film_url = href if href.startswith("http") else "https://www.picturehouses.com" + href

            results.append({
                "venue": "Cameo Picturehouse",
                "title": title,
                "times": ", ".join(times) if times else "",
                "tags": tag_film(title, desc),
                "desc": desc,
                "url": film_url,
                "year": "",
            })

        print(f"  Cameo: {len(results)} films")
    except Exception as e:
        print(f"  Cameo error: {e}")
        # Fallback: try the API endpoint Picturehouse sometimes exposes
        try:
            api_url = "https://www.picturehouses.com/api/cinema/CAM/whats-on"
            r2 = requests.get(api_url, headers=HEADERS, timeout=10).json()
            for film in (r2 if isinstance(r2, list) else r2.get("films", [])):
                title = film.get("title") or film.get("name", "")
                results.append({
                    "venue": "Cameo Picturehouse",
                    "title": title,
                    "times": "",
                    "tags": tag_film(title),
                    "desc": (film.get("synopsis") or "")[:150],
                    "url": film.get("url", ""),
                    "year": str(film.get("year", "")),
                })
        except:
            pass
    return results

# ── CINEWORLD ─────────────────────────────────────────────────────────────
def scrape_cineworld():
    results = []
    try:
        # Cineworld has a JSON endpoint for their listings
        url = "https://www.cineworld.co.uk/uk/data-api-service/v1/quickbook/10100/film-events/in-cinema/037/at-date/now"
        r = requests.get(url, headers=HEADERS, timeout=15).json()
        films = r.get("body", {}).get("films", [])
        events = r.get("body", {}).get("events", [])

        # Build showtime map by film id
        showtime_map = {}
        for ev in events:
            fid = ev.get("filmId", "")
            t = ev.get("eventDateTime", "")
            if t and fid:
                # Extract HH:MM
                m = re.search(r'T(\d{2}:\d{2})', t)
                if m:
                    showtime_map.setdefault(fid, []).append(m.group(1))

        for film in films:
            fid = film.get("id", "")
            title = film.get("name", "")
            if not title:
                continue
            times = showtime_map.get(fid, [])
            results.append({
                "venue": "Cineworld Edinburgh",
                "title": title,
                "times": ", ".join(sorted(set(times))[:8]),
                "tags": tag_film(title, film.get("synopsis", "")),
                "desc": (film.get("synopsis") or "")[:150],
                "url": f"https://www.cineworld.co.uk/films/{film.get('slug', '')}",
                "year": str(film.get("releaseYear", "")),
            })
        print(f"  Cineworld: {len(results)} films")
    except Exception as e:
        print(f"  Cineworld error: {e}")
    return results

# ── FILMHOUSE ─────────────────────────────────────────────────────────────
def scrape_filmhouse():
    results = []
    try:
        url = "https://www.filmhousecinemaseries.com/whats-on"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        for card in soup.select(".film-card, .event-card, article, .whats-on-item"):
            title_el = card.select_one("h1, h2, h3, .title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 2:
                continue

            times = []
            for t in card.select(".time, .showtime, time")[:8]:
                txt = t.get_text(strip=True)
                if re.match(r'\d{1,2}[:.]\d{2}', txt):
                    times.append(txt)

            desc = ""
            desc_el = card.select_one("p, .synopsis")
            if desc_el:
                desc = desc_el.get_text(strip=True)[:150]

            film_url = ""
            link = card.select_one("a[href]")
            if link:
                href = link["href"]
                film_url = href if href.startswith("http") else "https://www.filmhousecinemaseries.com" + href

            results.append({
                "venue": "Edinburgh Filmhouse",
                "title": title,
                "times": ", ".join(times),
                "tags": tag_film(title, desc),
                "desc": desc,
                "url": film_url,
                "year": "",
            })
        print(f"  Filmhouse: {len(results)} films")
    except Exception as e:
        print(f"  Filmhouse error: {e}")
    return results

# ── EVERYMAN ──────────────────────────────────────────────────────────────
def scrape_everyman():
    results = []
    try:
        url = "https://www.everymancinema.com/venues-list/g018l-everyman-edinburgh/whats-on"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        for card in soup.select(".film-listing-card, .film-card, article[class*='film']"):
            title_el = card.select_one("h2, h3, .film-title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 2:
                continue

            desc = ""
            desc_el = card.select_one("p, .synopsis, .description")
            if desc_el:
                desc = desc_el.get_text(strip=True)[:150]

            film_url = ""
            link = card.select_one("a[href]")
            if link:
                href = link["href"]
                film_url = href if href.startswith("http") else "https://www.everymancinema.com" + href

            results.append({
                "venue": "Everyman Edinburgh",
                "title": title,
                "times": "",
                "tags": tag_film(title, desc),
                "desc": desc,
                "url": film_url,
                "year": "",
            })
        print(f"  Everyman: {len(results)} films")
    except Exception as e:
        print(f"  Everyman error: {e}")
    return results

# ── ODEON ─────────────────────────────────────────────────────────────────
def scrape_odeon():
    results = []
    try:
        # Odeon has a JSON API
        url = "https://www.odeon.co.uk/api/cinemas/edinburgh-lothian-road/films/"
        r = requests.get(url, headers=HEADERS, timeout=15).json()
        for film in (r if isinstance(r, list) else r.get("films", [])):
            title = film.get("title") or film.get("name", "")
            if not title:
                continue
            results.append({
                "venue": "Odeon Lothian Road",
                "title": title,
                "times": "",
                "tags": tag_film(title, film.get("synopsis", "")),
                "desc": (film.get("synopsis") or "")[:150],
                "url": film.get("url", "https://www.odeon.co.uk"),
                "year": str(film.get("year", "")),
            })
        print(f"  Odeon: {len(results)} films")
    except Exception as e:
        print(f"  Odeon error: {e}")
    return results

# ── VUE ───────────────────────────────────────────────────────────────────
def scrape_vue():
    results = []
    try:
        url = "https://www.myvue.com/data/filmswithshowings/10032"
        r = requests.get(url, headers=HEADERS, timeout=15).json()
        for film in r.get("films", []):
            title = film.get("title", "")
            if not title:
                continue
            times = []
            for showing in film.get("showings", [])[:8]:
                t = showing.get("time", "")
                if t:
                    times.append(t[:5])
            results.append({
                "venue": "Vue Edinburgh Omni",
                "title": title,
                "times": ", ".join(times),
                "tags": tag_film(title, film.get("synopsis_short", "")),
                "desc": (film.get("synopsis_short") or "")[:150],
                "url": f"https://www.myvue.com/film/{film.get('slug', '')}",
                "year": str(film.get("release_year", "")),
            })
        print(f"  Vue: {len(results)} films")
    except Exception as e:
        print(f"  Vue error: {e}")
    return results

# ── MAIN ──────────────────────────────────────────────────────────────────
def get_cinema():
    print("Scraping Edinburgh cinemas...")
    all_listings = []

    scrapers = [
        scrape_cameo,
        scrape_cineworld,
        scrape_filmhouse,
        scrape_everyman,
        scrape_odeon,
        scrape_vue,
    ]

    for scraper in scrapers:
        try:
            results = scraper()
            all_listings.extend(results)
        except Exception as e:
            print(f"  Scraper failed: {e}")

    # Deduplicate: same venue + same title
    seen = set()
    deduped = []
    for item in all_listings:
        key = f"{item['venue']}::{item['title'].lower().strip()}"
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    # Sort by venue then title
    deduped.sort(key=lambda x: (x["venue"], x["title"]))

    print(f"\nTotal: {len(deduped)} film/venue entries")
    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)
    print(f"Saved listings.json — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    get_cinema()
