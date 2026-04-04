"""
scrape_recs.py
Fetches film recommendations from RSS feeds.
Writes recommendations.json with tags, links, streaming info.
TMDB_KEY must be set as a GitHub Secret.
"""

import requests
import json
import xml.etree.ElementTree as ET
import os
import re
from datetime import datetime, timezone

TMDB_KEY = os.getenv("TMDB_KEY")

FEEDS = {
    "The Guardian":    "https://www.theguardian.com/film/rss",
    "BFI":             "https://www.bfi.org.uk/rss.xml",
    "Variety":         "https://variety.com/feed/",
    "New Yorker":      "https://www.newyorker.com/feed/culture",
    "Sight & Sound":   "https://www.bfi.org.uk/sight-and-sound/rss.xml",
    "RogerEbert.com":  "https://www.rogerebert.com/feed",
    "Chicago Reader":  "https://chicagoreader.com/feed/",
    "Little White Lies":"https://lwlies.com/feed/",
}

# LRB is worth trying but their feed is inconsistent
BONUS_FEEDS = {
    "LRB":             "https://www.lrb.co.uk/feed",
    "Criterion":       "https://www.criterion.com/feed",
    "MUBI":            "https://mubi.com/en/gb/feed",
}

KEYWORD_TAGS = {
    "nazi": "Anti-Nazi", "resistance": "Anti-Nazi", "occupied france": "Anti-Nazi",
    "gestapo": "Anti-Nazi", "holocaust": "Anti-Nazi",
    "spy": "Spy", "espionage": "Spy", "cold war": "Spy", "mi5": "Spy", "mi6": "Spy", "cia": "Spy",
    "wwii": "WWII", "world war ii": "WWII", "second world war": "WWII",
    "documentary": "Documentary", "doc ": "Documentary",
    "criterion": "Criterion",
    "arthouse": "Arthouse", "art house": "Arthouse",
    "silent film": "Silent", "silent era": "Silent",
    "synthesizer": "Synthesizers", "synth ": "Synthesizers", "electronic music": "Synthesizers",
    "bergman": "Bergman",
    "powell and pressburger": "Powell & Pressburger", "powell & pressburger": "Powell & Pressburger",
    "tati": "Jacques Tati", "monsieur hulot": "Jacques Tati",
    "nouvelle vague": "French New Wave", "french new wave": "French New Wave",
    "fellini": "Italian Cinema", "antonioni": "Italian Cinema", "visconti": "Italian Cinema",
    "kurosawa": "World Cinema", "satyajit ray": "World Cinema",
    "scottish": "Scottish", "scotland": "Scottish", "glasgow": "Scottish", "edinburgh film": "Scottish",
    "review": "Critic Pick",
    "four stars": "Highly Rated", "five stars": "Highly Rated", "★★★★": "Highly Rated",
    "oscar": "Award", "bafta": "Award", "palme d'or": "Award", "palme dor": "Award",
    "ebert": "Ebert Pick",
    "great movie": "Ebert Pick",
    "prestige tv": "Prestige TV", "limited series": "TV", "miniseries": "TV",
}

FILM_QUALIFIERS = [
    "film", "cinema", "movie", "director", "actor", "actress", "screen",
    "review", "series", "season", "streaming", "release", "preview", "interview",
]

def extract_tags(text):
    tl = text.lower()
    tags = []
    for kw, tag in KEYWORD_TAGS.items():
        if kw in tl and tag not in tags:
            tags.append(tag)
    return tags

def is_film_relevant(title, desc):
    combined = (title + " " + desc).lower()
    return any(q in combined for q in FILM_QUALIFIERS + list(KEYWORD_TAGS.keys()))

def clean_title(raw):
    t = re.sub(r'\s*[–—\-]\s*(review|interview|preview|trailer|clip|podcast|recap).*$', '', raw, flags=re.IGNORECASE)
    t = re.sub(r'\s+(review|interview|preview|exclusive|podcast)$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'<[^>]+>', '', t)
    for ent, rep in [('&amp;','&'),('&quot;','"'),('&#39;',"'"),('&nbsp;',' '),('&ldquo;','"'),('&rdquo;','"')]:
        t = t.replace(ent, rep)
    return t.strip().strip('"').strip('\u201c\u201d').strip()

def get_streaming_uk(title):
    if not TMDB_KEY:
        return "", ""
    try:
        search_url = (f"https://api.themoviedb.org/3/search/multi"
                      f"?api_key={TMDB_KEY}&query={requests.utils.quote(title)}&region=GB")
        res = requests.get(search_url, timeout=8).json()
        if not res.get("results"):
            return "", ""
        item = res["results"][0]
        i_id, i_type = item["id"], item["media_type"]
        if i_type not in ("movie","tv"):
            return "", ""
        prov_url = (f"https://api.themoviedb.org/3/{i_type}/{i_id}/watch/providers"
                    f"?api_key={TMDB_KEY}")
        p_res = requests.get(prov_url, timeout=8).json()
        uk = p_res.get("results", {}).get("GB", {})
        found = [p["provider_name"] for p in uk.get("flatrate", []) + uk.get("free", [])]
        known = ["BBC iPlayer","Netflix","Apple TV","Disney","Prime Video",
                 "Channel 4","ITVX","MUBI","BFI Player","Paramount"]
        matched = [f for f in found if any(k.lower() in f.lower() for k in known)]
        jw_link = uk.get("link", "")
        return matched[0] if matched else "", jw_link
    except:
        return "", ""

def parse_date(raw):
    if not raw:
        return None
    for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"]:
        try:
            return datetime.strptime(raw.strip(), fmt)
        except:
            pass
    return None

def scrape_feed(name, url, limit=50):
    results = []
    try:
        r = requests.get(url, timeout=12,
                         headers={"User-Agent": "Mozilla/5.0", "Accept": "application/rss+xml,application/xml,*/*"})
        root = ET.fromstring(r.content)
        for item in root.findall(".//item")[:limit]:
            title_el = item.find("title")
            desc_el  = item.find("description")
            link_el  = item.find("link")
            date_el  = item.find("pubDate") or item.find("{http://purl.org/dc/elements/1.1/}date")

            if title_el is None:
                continue

            raw_title = title_el.text or ""
            raw_desc  = desc_el.text or "" if desc_el is not None else ""
            clean_desc = re.sub(r'<[^>]+>', '', raw_desc)[:250]
            pub_date  = date_el.text if date_el is not None else ""

            if not is_film_relevant(raw_title, clean_desc):
                continue

            title = clean_title(raw_title)
            if len(title) < 3:
                continue

            tags = extract_tags(raw_title + " " + clean_desc)
            streaming, jw_link = get_streaming_uk(title)
            if streaming and "Streaming" not in tags:
                tags.append("Streaming")

            article_url = link_el.text if link_el is not None else "#"

            results.append({
                "title":     title,
                "source":    name,
                "url":       article_url,       # link to the article
                "tags":      tags,
                "desc":      clean_desc.strip(),
                "streaming": streaming,
                "jw_url":    jw_link,           # JustWatch link for streaming info
                "pub_date":  pub_date,
            })
    except Exception as e:
        print(f"  Feed error ({name}): {e}")
    return results

def get_recs():
    all_results = []
    seen = set()

    all_feeds = dict(FEEDS)
    for name, url in BONUS_FEEDS.items():
        all_feeds[name] = url

    for name, url in all_feeds.items():
        print(f"Fetching {name}...")
        items = scrape_feed(name, url)
        print(f"  {len(items)} relevant items")
        for item in items:
            key = item["title"].lower()[:50]
            if key not in seen:
                seen.add(key)
                all_results.append(item)

    # Sort newest first (items without date go last)
    def sort_key(x):
        d = parse_date(x.get("pub_date",""))
        return d if d else datetime.min.replace(tzinfo=timezone.utc)

    all_results.sort(key=sort_key, reverse=True)

    print(f"\nTotal recommendations: {len(all_results)}")
    with open("recommendations.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print("Saved recommendations.json")

if __name__ == "__main__":
    get_recs()
