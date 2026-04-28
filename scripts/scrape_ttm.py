#!/usr/bin/env python3
"""Scraper for Thai Ticket Major (thaiticketmajor.com) public feed."""
import json
import sys
from datetime import datetime

import requests

FEED_URL = "https://www.thaiticketmajor.com/assets/event.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def run():
    print("Fetching TTM feed...")
    feed = requests.get(FEED_URL, headers=HEADERS, timeout=30).json()
    concerts = [item for item in feed if "concert" in item.get("link", "")]
    print(f"Found {len(concerts)} concert items")

    events = []
    for item in concerts:
        title = item.get("title_en") or item.get("title_th", "")
        link = item.get("link", "")
        url = link if link.startswith("http") else f"https://www.thaiticketmajor.com{link}"
        events.append({
            "source": "thaiticketmajor",
            "sourceId": link.rstrip(".html").split("/")[-1],
            "title": title,
            "artist": title.split(":")[0].split("-")[0].split("|")[0].strip(),
            "date": None,
            "dateText": None,
            "venue": None,
            "link": url,
            "linkLabel": "Thai Ticket Major",
            "isInternational": bool(__import__("re").search(r"[a-zA-Z]", title)) and not __import__("re").search(r"[\u0e00-\u0e7f]", title),
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
