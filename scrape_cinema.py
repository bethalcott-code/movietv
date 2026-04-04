"""
scrape_cinema.py — Edinburgh cinema listings
Sources:
  1. Cineworld JSON API (reliable, no auth)
  2. Vue JSON API (reliable, no auth)
  3. Filmhouse.org.uk (simple HTML, scrapeable)
  4. cinemaguide.co.uk aggregator API (covers Cameo, Odeon, Everyman + others)
Writes listings.json grouped by venue with TMDB UK streaming data.
"""

import requests
import json
import re
import os
import time
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
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
            f"https://api.themoviedb.org/3/search/multi"
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

# ── SOURCE 1: CINEWORLD JSON API ──────────────────────────────────────────
def scrape_cineworld():
    results = []
    try:
        # Edinburgh Fountainpark cinema ID: 037
        url = ("https://www.cineworld.co.uk/uk/data-api-service/v1/quickbook"
               "/10100/film-events/in-cinema/037/at-date/now")
        r = requests.get(url, headers=HEADERS, timeout=15).json()
        body = r.get("body", {})
        films = body.get("films", [])
        events = body.get("events", [])

        # Build showtime map: filmId -> [times]
        time_map = {}
        for ev in events:
            fid = ev.get("filmId", "")
            dt = ev.get("eventDateTime", "")
            m = re.search(r'T(\d{2}:\d{2})', dt)
            if m and fid:
                time_map.setdefault(fid, []).append(m.group(1))

        for film in films:
            fid = film.get("id", "")
            title = film.get("name", "").strip()
            if not title:
                continue
            times = sorted(set(time_map.get(fid, [])))
            results.append({
                "venue": "Cineworld Edinburgh",
                "title": title,
                "times": ", ".join(times[:8]),
                "tags": tag_film(title, film.get("synopsis", "")),
                "desc": (film.get("synopsis") or "")[:150],
                "url": f"https://www.cineworld.co.uk/films/{film.get('slug','')}",
                "year": str(film.get("releaseYear", "")),
            })
        print(f"  Cineworld: {len(results)} films")
    except Exception as e:
        print(f"  Cineworld error: {e}")
    return results

# ── SOURCE 2: VUE JSON API ────────────────────────────────────────────────
def scrape_vue():
    results = []
    try:
        # Vue Edinburgh Omni: site ID 10032
        # Vue Edinburgh Ocean Terminal: site ID 10059
        for site_id, venue_name in [("10032", "Vue Edinburgh Omni"),
                                      ("10059", "Vue Ocean Terminal")]:
            url = f"https://www.myvue.com/data/filmswithshowings/{site_id}"
            r = requests.get(url, headers=HEADERS, timeout=15).json()
            for film in r.get("films", []):
                title = film.get("title", "").strip()
                if not title:
                    continue
                times = []
                for showing in film.get("showings", [])[:8]:
                    t = showing.get("time", "")
                    if t:
                        times.append(t[:5])
                results.append({
                    "venue": venue_name,
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

# ── SOURCE 3: FILMHOUSE ───────────────────────────────────────────────────
def scrape_filmhouse():
    """
    Filmhouse Edinburgh (filmhouse.org.uk) — plain HTML, no JS required.
    Their what's-on page lists films with dates and times.
    """
    results = []
    try:
        from bs4 import BeautifulSoup
        for url in [
            "https://www.filmhouse.org.uk/whats-on/",
            "https://www.filmhousecinema.com/whats-on/",
        ]:
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "html.parser")
                # Filmhouse uses article/div cards for each film
                for card in soup.select("article, .film-listing, .event-item, .film-card"):
                    title_el = card.select_one("h1, h2, h3, .title, .film-title")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    if not title or len(title) < 2:
                        continue
                    times = []
                    for t in card.select(".time, .showtime, time, .performance")[:8]:
                        txt = t.get_text(strip=True)
                        if re.search(r'\d{1,2}[:.]\d{2}', txt):
                            times.append(txt[:5])
                    desc = ""
                    desc_el = card.select_one("p, .synopsis, .description")
                    if desc_el:
                        desc = desc_el.get_text(strip=True)[:150]
                    link_el = card.select_one("a[href]")
                    film_url = ""
                    if link_el:
                        href = link_el["href"]
                        film_url = href if href.startswith("http") else url.rstrip("/whats-on/") + href
                    results.append({
                        "venue": "Edinburgh Filmhouse",
                        "title": title,
                        "times": ", ".join(times),
                        "tags": tag_film(title, desc),
                        "desc": desc,
                        "url": film_url,
                        "year": "",
                    })
                if results:
                    break
            except:
                continue
        print(f"  Filmhouse: {len(results)} films")
    except Exception as e:
        print(f"  Filmhouse error: {e}")
    return results

# ── SOURCE 4: CINEMAGUIDE.CO.UK API ──────────────────────────────────────
def scrape_cinemaguide():
    """
    cinemaguide.co.uk aggregates Edinburgh cinemas including Cameo, Odeon,
    Everyman. Try their API endpoints.
    """
    results = []
    try:
        # cinemaguide uses a search API
        # Edinburgh area code / cinema IDs to try
        venues_to_try = [
            ("https://cinemaguide.co.uk/api/cinema/EDI/showtimes", "Edinburgh (CinemaGuide)"),
            ("https://cinemaguide.co.uk/api/cinemas/edinburgh", "Edinburgh (CinemaGuide)"),
        ]
        for api_url, default_venue in venues_to_try:
            try:
                r = requests.get(api_url, headers=HEADERS, timeout=12)
                if r.status_code != 200:
                    continue
                data = r.json()
                # Handle various response shapes
                films = data if isinstance(data, list) else data.get("films", data.get("results", []))
                for film in films:
                    title = (film.get("title") or film.get("name") or "").strip()
                    if not title:
                        continue
                    venue = (film.get("cinema") or film.get("venue") or default_venue)
                    times = film.get("times", film.get("showtimes", []))
                    if isinstance(times, list):
                        times_str = ", ".join(str(t)[:5] for t in times[:8])
                    else:
                        times_str = str(times)[:50]
                    results.append({
                        "venue": venue,
                        "title": title,
                        "times": times_str,
                        "tags": tag_film(title, film.get("synopsis", "")),
                        "desc": (film.get("synopsis") or film.get("description") or "")[:150],
                        "url": film.get("url", film.get("link", "")),
                        "year": str(film.get("year", film.get("release_year", ""))),
                    })
                if results:
                    break
            except:
                continue
        print(f"  CinemaGuide: {len(results)} films")
    except Exception as e:
        print(f"  CinemaGuide error: {e}")
    return results

# ── SOURCE 5: ODEON JSON API ──────────────────────────────────────────────
def scrape_odeon():
    results = []
    try:
        # Odeon has a GraphQL/JSON API — try the listings endpoint
        # Edinburgh Lothian Road site code: EDI
        for cinema_id, venue_name in [
            ("edi", "Odeon Lothian Road"),
            ("ediw", "Odeon Edinburgh West"),
        ]:
            url = f"https://www.odeon.co.uk/api/cinema/{cinema_id}/films/"
            r = requests.get(url, headers=HEADERS, timeout=12)
            if r.status_code != 200:
                continue
            data = r.json()
            films = data if isinstance(data, list) else data.get("films", [])
            for film in films:
                title = (film.get("title") or film.get("name") or "").strip()
                if not title:
                    continue
                results.append({
                    "venue": venue_name,
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

# ── SOURCE 6: EVERYMAN API ────────────────────────────────────────────────
def scrape_everyman():
    results = []
    try:
        # Everyman Edinburgh venue slug: edinburgh
        url = "https://www.everymancinema.com/api/v2/whats-on?venue=edinburgh"
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code == 200:
            data = r.json()
            films = data if isinstance(data, list) else data.get("films", data.get("events", []))
            for film in films:
                title = (film.get("title") or film.get("name") or "").strip()
                if not title:
                    continue
                results.append({
                    "venue": "Everyman Edinburgh",
                    "title": title,
                    "times": "",
                    "tags": tag_film(title, film.get("synopsis", "")),
                    "desc": (film.get("synopsis") or "")[:150],
                    "url": film.get("url", "https://www.everymancinema.com"),
                    "year": str(film.get("year", "")),
                })
        print(f"  Everyman: {len(results)} films")
    except Exception as e:
        print(f"  Everyman error: {e}")
    return results

# ── MAIN ──────────────────────────────────────────────────────────────────
def get_cinema():
    print(f"Scraping Edinburgh cinemas — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    all_listings = []

    for scraper in [scrape_cineworld, scrape_vue, scrape_filmhouse,
                    scrape_odeon, scrape_everyman, scrape_cinemaguide]:
        try:
            results = scraper()
            all_listings.extend(results)
        except Exception as e:
            print(f"  Scraper failed: {e}")

    # Deduplicate by venue + title
    seen = set()
    deduped = []
    for item in all_listings:
        key = f"{item['venue']}::{item['title'].lower().strip()}"
        if key not in seen and len(item["title"]) > 2:
            seen.add(key)
            deduped.append(item)

    deduped.sort(key=lambda x: (x["venue"], x["title"]))
    print(f"\nTotal before streaming lookup: {len(deduped)} entries")

    # TMDB streaming lookup — deduplicate by title
    if TMDB_KEY:
        print("Looking up UK streaming availability via TMDB...")
        title_cache = {}
        for item in deduped:
            t = item["title"].lower()
            if t not in title_cache:
                streaming, jw = get_streaming_uk(item["title"])
                title_cache[t] = (streaming, jw)
                time.sleep(0.2)
            item["streaming"] = title_cache[t][0]
            item["jw_url"] = title_cache[t][1]
        print("Streaming lookup done.")
    else:
        for item in deduped:
            item.setdefault("streaming", "")
            item.setdefault("jw_url", "")
        print("TMDB_KEY not set — skipping streaming lookup.")

    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)
    print(f"Saved listings.json — {len(deduped)} entries")

if __name__ == "__main__":
    get_cinema()
