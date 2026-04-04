"""
scrape_cinema.py — Edinburgh cinema listings via film.datathistle.com
HTML structure confirmed from live fetch April 2026:
  Film titles: <h4><a href="/listing/...">Title</a></h4>
  Times: <li><a title="3:25pm"> (title attr) or <li><a>15:25</a>
  Past screenings: <li><del>...</del> — skip these
  Year: <ul><li>2026</li>... metadata block
  Description: <p> sibling after metadata ul
"""

import requests
from bs4 import BeautifulSoup
import json, re, os, time, sys
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Cache-Control": "no-cache",
}

TMDB_KEY = os.getenv("TMDB_KEY")

VENUES = [
    ("524-cameo-cinema-edinburgh",            "Cameo Picturehouse"),
    ("794-filmhouse-edinburgh",               "Edinburgh Filmhouse"),
    ("12758-cineworld-fountainpark-edinburgh","Cineworld Edinburgh"),
    ("16405-odeon-lothian-road-edinburgh",    "Odeon Lothian Road"),
    ("15902-vue-omni-centre-edinburgh",       "Vue Edinburgh Omni"),
    ("15006-vue-ocean-terminal-edinburgh",    "Vue Ocean Terminal"),
    ("132343-everyman-edinburgh",             "Everyman Edinburgh"),
]

PROVIDER_MAP = {
    "BBC iPlayer":"iPlayer","Netflix":"Netflix",
    "Apple TV Plus":"Apple TV+","Apple TV+":"Apple TV+",
    "Disney Plus":"Disney+","Disney+":"Disney+",
    "Amazon Prime Video":"Prime Video","Amazon Video":"Prime Video",
    "Channel 4":"Channel 4","ITVX":"ITVX",
    "MUBI":"MUBI","BFI Player":"BFI Player",
    "Paramount Plus":"Paramount+","NOW":"NOW",
}

INTEREST_TAGS = {
    "nazi":"Anti-Nazi","resistance":"Anti-Nazi","gestapo":"Anti-Nazi",
    "holocaust":"Anti-Nazi","spy":"Spy","espionage":"Spy","cold war":"Spy",
    "wwii":"WWII","world war":"WWII","documentary":"Documentary",
    "scottish":"Scottish","scotland":"Scottish","arthouse":"Arthouse",
    "criterion":"Criterion","bergman":"Bergman",
}

def log(msg): print(msg, flush=True)

def tag_film(title, synopsis=""):
    text = (title+" "+(synopsis or "")).lower()
    return list({tag for kw,tag in INTEREST_TAGS.items() if kw in text})

def get_streaming_uk(title):
    if not TMDB_KEY: return "",""
    try:
        res = requests.get(
            f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}"
            f"&query={requests.utils.quote(title)}&region=GB", timeout=8).json()
        results = res.get("results",[])
        if not results: return "",""
        item = results[0]
        i_id,i_type = item["id"],item.get("media_type","movie")
        if i_type not in ("movie","tv"): i_type="movie"
        pres = requests.get(
            f"https://api.themoviedb.org/3/{i_type}/{i_id}/watch/providers"
            f"?api_key={TMDB_KEY}", timeout=8).json()
        uk = pres.get("results",{}).get("GB",{})
        all_p = uk.get("flatrate",[])+uk.get("free",[])+uk.get("ads",[])
        jw = uk.get("link","")
        for p in all_p:
            short = PROVIDER_MAP.get(p.get("provider_name",""),"")
            if short: return short,jw
        return (all_p[0].get("provider_name","") if all_p else ""),jw
    except: return "",""

def parse_time_from_a(a_tag):
    """Extract HH:MM from <a title='3:25pm'> or <a>15:25</a>."""
    # Try title attribute first: "3:25pm", "11am", "11:30"
    for src in [a_tag.get("title",""), a_tag.get_text(strip=True)]:
        m = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)?', src, re.I)
        if m:
            h,mi = int(m.group(1)),int(m.group(2))
            if m.group(3) and m.group(3).lower()=="pm" and h!=12: h+=12
            if m.group(3) and m.group(3).lower()=="am" and h==12: h=0
            return f"{h:02d}:{mi:02d}"
        # "11am" without minutes
        m2 = re.search(r'(\d{1,2})\s*(am|pm)', src, re.I)
        if m2:
            h = int(m2.group(1))
            if m2.group(2).lower()=="pm" and h!=12: h+=12
            if m2.group(2).lower()=="am" and h==12: h=0
            return f"{h:02d}:00"
    return None

def scrape_venue(slug, venue_name):
    films = []
    url = f"https://film.datathistle.com/cinema/{slug}/"
    log(f"  Fetching {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        log(f"  HTTP {r.status_code}, {len(r.text)} bytes")
        if r.status_code != 200:
            log(f"  Non-200 response, skipping")
            return films

        soup = BeautifulSoup(r.text, "html.parser")

        # DEBUG: show first few h4s to confirm structure
        all_h4 = soup.find_all("h4")
        log(f"  Found {len(all_h4)} h4 elements")
        for h in all_h4[:3]:
            log(f"    h4: {repr(h.get_text(strip=True)[:50])}")

        # Each film is in a <h4> containing <a href="/listing/...">
        film_h4s = [(h, h.find("a", href=re.compile(r"/(listing|event)/")))
                    for h in all_h4
                    if h.find("a", href=re.compile(r"/(listing|event)/"))]
        log(f"  Film h4s with /listing/ links: {len(film_h4s)}")

        for h4, link in film_h4s:
            title = link.get_text(strip=True)
            href  = link.get("href","")
            film_url = ("https://film.datathistle.com"+href
                        if href.startswith("/") else href)
            year = ""
            desc = ""
            all_times = []

            # Walk all siblings after this h4 until the next h4
            sib = h4.find_next_sibling()
            while sib and sib.name != "h4":
                # Year from metadata ul (first ul after h4, contains 4-digit year)
                if sib.name == "ul" and not year:
                    for li in sib.find_all("li", recursive=False):
                        txt = li.get_text(strip=True)
                        if re.match(r'^(19|20)\d{2}$', txt):
                            year = txt
                            break

                # Description: <p> with substantial text, no times
                if sib.name == "p" and not desc:
                    txt = sib.get_text(strip=True)
                    if len(txt) > 30 and not re.search(r'\d{1,2}[:.]\d{2}', txt):
                        desc = txt[:200]

                # Times from h5 day-sections: <h5>Sat 21 Mar</h5><ul><li><a...>
                if sib.name in ("h5","h6"):
                    # Collect <ul>/<ol> immediately after this heading
                    nxt = sib.find_next_sibling()
                    while nxt and nxt.name in ("ul","ol","h6","div"):
                        if nxt.name in ("ul","ol"):
                            for li in nxt.find_all("li"):
                                # Skip past/struck-through screenings
                                if li.find(["del","s"]):
                                    continue
                                a = li.find("a")
                                if a:
                                    t = parse_time_from_a(a)
                                    if t:
                                        all_times.append(t)
                        if nxt.name in ("h5","h6"):
                            break
                        nxt = nxt.find_next_sibling()

                # Also catch bare <ul> with times (some venues format differently)
                if sib.name in ("ul","ol"):
                    for li in sib.find_all("li"):
                        if li.find(["del","s"]):
                            continue
                        a = li.find("a")
                        if a:
                            t = parse_time_from_a(a)
                            if t:
                                all_times.append(t)

                sib = sib.find_next_sibling()

            films.append({
                "venue":  venue_name,
                "title":  title,
                "times":  ", ".join(sorted(set(all_times))[:10]),
                "tags":   tag_film(title, desc),
                "desc":   desc[:150],
                "url":    film_url,
                "year":   year,
            })
            log(f"    + {title} ({year}) — {len(all_times)} times")

        log(f"  {venue_name}: {len(films)} films total")
    except Exception as e:
        log(f"  {venue_name} ERROR: {type(e).__name__}: {e}")
    return films


def get_cinema():
    log(f"=== Edinburgh cinema scraper {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
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
            log(f"  {venue_name} FAILED: {e}")
        time.sleep(0.75)

    all_listings.sort(key=lambda x: (x["venue"], x["title"]))
    log(f"\n=== Total: {len(all_listings)} entries ===")

    if TMDB_KEY and all_listings:
        log("Looking up UK streaming via TMDB...")
        cache = {}
        for item in all_listings:
            t = item["title"].lower()
            if t not in cache:
                cache[t] = get_streaming_uk(item["title"])
                time.sleep(0.2)
            item["streaming"],item["jw_url"] = cache[t]
    else:
        for item in all_listings:
            item.setdefault("streaming","")
            item.setdefault("jw_url","")

    with open("listings.json","w",encoding="utf-8") as f:
        json.dump(all_listings, f, indent=2, ensure_ascii=False)
    log(f"Saved listings.json")

if __name__ == "__main__":
    get_cinema()
