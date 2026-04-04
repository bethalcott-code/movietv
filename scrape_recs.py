import requests
import json
import xml.etree.ElementTree as ET
import os
import re

# TMDB key goes in GitHub Secrets as TMDB_KEY — not hardcoded
TMDB_KEY = os.getenv("TMDB_KEY")

# ── RSS FEEDS ────────────────────────────────────────────────────────────
FEEDS = {
    "The Guardian":   "https://www.theguardian.com/film/rss",
    "BFI":            "https://www.bfi.org.uk/rss.xml",
    "Variety":        "https://variety.com/feed/",
    "New Yorker":     "https://www.newyorker.com/feed/culture",
    "Sight & Sound":  "https://www.bfi.org.uk/sight-and-sound/rss.xml",
}

# Try LRB — their RSS is inconsistent but worth attempting
LRB_FEED = "https://www.lrb.co.uk/feed"

# ── INTEREST KEYWORDS ────────────────────────────────────────────────────
# Maps keyword -> tag label
KEYWORD_TAGS = {
    "nazi": "Anti-Nazi",
    "resistance": "Anti-Nazi",
    "occupied": "Anti-Nazi",
    "gestapo": "Anti-Nazi",
    "holocaust": "Anti-Nazi",
    "spy": "Spy",
    "espionage": "Spy",
    "cold war": "Spy",
    "intelligence": "Spy",
    "wwii": "WWII",
    "world war": "WWII",
    "1940s": "WWII",
    "documentary": "Documentary",
    "criterion": "Criterion",
    "arthouse": "Arthouse",
    "art house": "Arthouse",
    "repertory": "Repertory",
    "silent film": "Silent",
    "synthesizer": "Synthesizers",
    "synth": "Synthesizers",
    "electronic music": "Synthesizers",
    "bergman": "Bergman",
    "powell and pressburger": "Powell & Pressburger",
    "pressburger": "Powell & Pressburger",
    "tati": "Jacques Tati",
    "nouvelle vague": "French New Wave",
    "new wave": "French New Wave",
    "fellini": "Italian Cinema",
    "kurosawa": "World Cinema",
    "review": "Critic Pick",
    "award": "Award",
    "oscar": "Award",
    "bafta": "Award",
    "palme": "Award",
}

# Broader terms that still qualify a piece as film-relevant
FILM_QUALIFIERS = [
    "film", "cinema", "movie", "director", "screen", "actor", "actress",
    "series", "season", "episode", "television", "streaming",
]

def extract_tags(text):
    text_lower = text.lower()
    tags = []
    for keyword, tag in KEYWORD_TAGS.items():
        if keyword in text_lower and tag not in tags:
            tags.append(tag)
    return tags

def is_film_relevant(title, description):
    combined = (title + " " + description).lower()
    return any(q in combined for q in FILM_QUALIFIERS + list(KEYWORD_TAGS.keys()))

def clean_title(raw):
    # Strip common review suffixes: "Film Name review", "Film Name — review"
    t = re.sub(r'\s*[–—-]\s*(review|interview|preview|trailer|clip|exclusive).*$', '', raw, flags=re.IGNORECASE)
    t = re.sub(r'\s+(review|interview|preview|exclusive)$', '', t, flags=re.IGNORECASE)
    # Strip HTML entities and tags
    t = re.sub(r'<[^>]+>', '', t)
    t = t.replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    return t.strip().strip('"').strip('\u201c\u201d')

def get_streaming_uk(title):
    if not TMDB_KEY:
        return ""
    try:
        search_url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={requests.utils.quote(title)}&region=GB"
        res = requests.get(search_url, timeout=8).json()
        if not res.get("results"):
            return ""
        item = res["results"][0]
        i_id, i_type = item["id"], item["media_type"]
        prov_url = f"https://api.themoviedb.org/3/{i_type}/{i_id}/watch/providers?api_key={TMDB_KEY}"
        p_res = requests.get(prov_url, timeout=8).json()
        uk = p_res.get("results", {}).get("GB", {})
        found = [p["provider_name"] for p in uk.get("flatrate", []) + uk.get("free", [])]
        # Filter to services we care about
        known = ["BBC iPlayer","Netflix","Apple TV","Disney","Prime Video","Channel 4","ITVX","MUBI","BFI"]
        matched = [f for f in found if any(k.lower() in f.lower() for k in known)]
        return matched[0] if matched else ""
    except:
        return ""

def scrape_feed(name, url):
    results = []
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(r.content)
        for item in root.findall(".//item")[:20]:
            title_el = item.find("title")
            desc_el = item.find("description")
            link_el = item.find("link")
            if title_el is None:
                continue
            raw_title = title_el.text or ""
            raw_desc = desc_el.text or "" if desc_el is not None else ""
            # Strip HTML from description
            clean_desc = re.sub(r'<[^>]+>', '', raw_desc)[:200]
            if not is_film_relevant(raw_title, clean_desc):
                continue
            title = clean_title(raw_title)
            if len(title) < 3:
                continue
            tags = extract_tags(raw_title + " " + clean_desc)
            streaming = get_streaming_uk(title)
            if streaming and "Streaming" not in tags:
                tags.append("Streaming")
            results.append({
                "title": title,
                "source": name,
                "url": link_el.text if link_el is not None else "#",
                "tags": tags,
                "desc": clean_desc.strip(),
                "streaming": streaming,
            })
    except Exception as e:
        print(f"  Feed error ({name}): {e}")
    return results

def get_recs():
    all_results = []
    seen_titles = set()

    all_feeds = dict(FEEDS)
    # Add LRB as a bonus attempt
    all_feeds["LRB"] = LRB_FEED

    for name, url in all_feeds.items():
        print(f"Fetching {name}...")
        items = scrape_feed(name, url)
        print(f"  {len(items)} relevant items")
        for item in items:
            key = item["title"].lower()[:40]
            if key not in seen_titles:
                seen_titles.add(key)
                all_results.append(item)

    print(f"\nTotal recommendations: {len(all_results)}")
    with open("recommendations.json", "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print("Saved recommendations.json")

if __name__ == "__main__":
    get_recs()
