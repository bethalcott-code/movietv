"""
enrich_canonical.py
One-time (or periodic) script to add UK streaming provider data to canonical.json.
Run locally or add as a GitHub Actions step (needs TMDB_KEY env var).
Updates canonical.json in place.
"""

import requests
import json
import os
import time

TMDB_KEY = os.getenv("TMDB_KEY")

# Map TMDB provider names to our short labels
PROVIDER_MAP = {
    "BBC iPlayer":          "iPlayer",
    "Netflix":              "Netflix",
    "Apple TV Plus":        "Apple TV+",
    "Apple TV+":            "Apple TV+",
    "Disney Plus":          "Disney+",
    "Disney+":              "Disney+",
    "Amazon Prime Video":   "Prime Video",
    "Amazon Video":         "Prime Video",
    "Channel 4":            "Channel 4",
    "ITVX":                 "ITVX",
    "MUBI":                 "MUBI",
    "BFI Player":           "BFI Player",
    "Paramount Plus":       "Paramount+",
    "NOW":                  "NOW",
    "Curzon Home Cinema":   "Curzon",
}

def get_providers(title, year=None, media_type=None):
    """Returns (short_provider_name, justwatch_url) or ('', '')"""
    if not TMDB_KEY:
        return "", ""
    try:
        # Search
        query = requests.utils.quote(title)
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={query}&region=GB"
        res = requests.get(url, timeout=8).json()
        results = res.get("results", [])
        if not results:
            return "", ""

        # Try to match by year if provided
        item = results[0]
        if year:
            yr = str(year)
            for r in results[:5]:
                rd = r.get("release_date","") or r.get("first_air_date","")
                if rd.startswith(yr):
                    item = r
                    break

        i_id = item["id"]
        i_type = item.get("media_type", "movie")
        if i_type not in ("movie", "tv"):
            i_type = "movie"

        # Get UK providers
        purl = f"https://api.themoviedb.org/3/{i_type}/{i_id}/watch/providers?api_key={TMDB_KEY}"
        pres = requests.get(purl, timeout=8).json()
        uk = pres.get("results", {}).get("GB", {})

        # Subscription (flatrate) first, then free
        all_providers = uk.get("flatrate", []) + uk.get("free", []) + uk.get("ads", [])
        jw_link = uk.get("link", "")

        for p in all_providers:
            name = p.get("provider_name", "")
            short = PROVIDER_MAP.get(name, "")
            if short:
                return short, jw_link

        # Return first even if not in our map
        if all_providers:
            return all_providers[0].get("provider_name",""), jw_link

        return "", jw_link
    except Exception as e:
        return "", ""

def enrich():
    if not TMDB_KEY:
        print("ERROR: TMDB_KEY not set. Export it as an environment variable.")
        return

    with open("canonical.json", encoding="utf-8") as f:
        canon = json.load(f)

    print(f"Enriching {len(canon)} canonical entries with UK streaming data...")
    updated = 0

    for i, item in enumerate(canon):
        title = item.get("title", "")
        year = item.get("year", "")
        print(f"  [{i+1}/{len(canon)}] {title} ({year})...", end=" ", flush=True)

        provider, jw_url = get_providers(title, year)

        if provider:
            item["streaming"] = provider
            item["jw_url"] = jw_url
            print(f"✓ {provider}")
            updated += 1
        else:
            item["streaming"] = item.get("streaming", "")
            item["jw_url"] = jw_url or item.get("jw_url", "")
            print("—")

        # Be gentle with the API
        time.sleep(0.25)

    with open("canonical.json", "w", encoding="utf-8") as f:
        json.dump(canon, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {updated}/{len(canon)} entries have streaming data.")
    print("Saved canonical.json")

if __name__ == "__main__":
    enrich()
