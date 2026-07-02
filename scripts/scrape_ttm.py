#!/usr/bin/env python3
"""Scraper for Thai Ticket Major (thaiticketmajor.com) public feed.
IMPROVED: Includes ticketmaster.co.th subdomain events and broader concert detection."""
import json
import re
import sys
from datetime import datetime

import requests

FEED_URL = "https://www.thaiticketmajor.com/assets/event.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Keywords that indicate a live music event even if not under /concert/
MUSIC_KEYWORDS = [
    "concert", "tour", "live", "music", "festival", "fan meeting",
    "fan-con", "fan con", "showcase", "world tour", "asia tour",
]


def is_music_event(item: dict) -> bool:
    """Broader detection for music/live events."""
    link = item.get("link", "").lower()
    title = (item.get("title_en", "") + " " + item.get("title_th", "")).lower()
    # Always include /concert/ links
    if "concert" in link:
        return True
    # Include ticketmaster.co.th activity links (these are concerts)
    if "ticketmaster" in link and any(k in title for k in MUSIC_KEYWORDS):
        return True
    # Check title for music keywords
    if any(k in title for k in MUSIC_KEYWORDS):
        return True
    return False


def run():
    print("Fetching TTM feed...")
    feed = requests.get(FEED_URL, headers=HEADERS, timeout=30).json()
    concerts = [item for item in feed if is_music_event(item)]
    print(f"Found {len(concerts)} music/live items (was {len([i for i in feed if 'concert' in i.get('link','')])} with old filter)")

    events = []
    for item in concerts:
        title = item.get("title_en") or item.get("title_th", "")
        link = item.get("link", "")
        url = link if link.startswith("http") else f"https://www.thaiticketmajor.com{link}"
        # Source ID
        if "ticketmaster" in link:
            source_id = link.rstrip("/").split("/")[-1]
        else:
            source_id = link.rstrip(".html").split("/")[-1]
        events.append({
            "source": "thaiticketmajor",
            "sourceId": source_id,
            "title": title,
            "artist": title.split(":")[0].split("-")[0].split("|")[0].strip(),
            "date": None,
            "dateText": None,
            "venue": None,
            "link": url,
            "linkLabel": "Thai Ticket Major",
            "isInternational": bool(re.search(r"[a-zA-Z]", title)) and not re.search(r"[\u0e00-\u0e7f]", title),
            "genre": "Concert",
            "scrapedAt": datetime.now().isoformat(),
        })

    out_path = sys.argv[1] if len(sys.argv) > 1 else "data/ttm_raw.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"source": "thaiticketmajor", "count": len(events), "events": events}, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(events)} TTM feed events -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
