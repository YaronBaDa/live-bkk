#!/usr/bin/env python3
"""Scraper for AllEvents.in RSS feed — Bangkok concerts."""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

RSS_URL = "https://allevents.in/rss3.php?city=bangkok&category=concerts"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def run():
    print("Fetching AllEvents.in RSS...")
    r = requests.get(RSS_URL, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        print(f"Failed: HTTP {r.status_code}")
        return 1

    items = re.findall(r"<item>(.*?)</item>", r.text, re.S)
    print(f"Found {len(items)} RSS items")

    events = []
    for item in items:
        title_m = re.search(r"<title>(.*?)</title>", item, re.S)
        link_m = re.search(r"<link>(.*?)</link>", item, re.S)
        desc_m = re.search(r"<description>(.*?)</description>", item, re.S)
        image_m = re.search(r"<image>(.*?)</image>", item, re.S)

        title = title_m.group(1).strip() if title_m else ""
        link = link_m.group(1).strip() if link_m else ""
        desc = desc_m.group(1).strip() if desc_m else ""
        image = image_m.group(1).strip() if image_m else ""

        # Clean CDATA if present
        title = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", title, flags=re.S).strip()
        desc = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", desc, flags=re.S).strip()

        # Extract date from description if possible
        date = None
        date_text = ""
        dm = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", desc)
        if dm:
            date_text = dm.group(1)
            try:
                dt = datetime.strptime(date_text, "%d %B %Y")
                date = dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        if title and link:
            events.append({
                "source": "allevents",
                "sourceId": link.rstrip("/").split("/")[-1],
                "title": title,
                "artist": title.split(":")[0].split("-")[0].strip(),
                "date": date,
                "dateText": date_text,
                "venue": "",
                "link": link,
                "linkLabel": "AllEvents.in",
                "isInternational": bool(re.search(r"[a-zA-Z]", title)) and not re.search(r"[\u0e00-\u0e7f]", title),
                "genre": "Concert",
                "image": image,
                "scrapedAt": datetime.now().isoformat(),
            })

    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/allevents_raw.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"source": "allevents", "count": len(events), "events": events}, f, ensure_ascii=False, indent=2)
    print(f"Scraped {len(events)} AllEvents.in events -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
