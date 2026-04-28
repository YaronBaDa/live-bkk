#!/usr/bin/env python3
"""
Scraper for Ticketmelon (ticketmelon.com)
Uses sitemaps to discover events, then scrapes __NEXT_DATA__ from each page.
"""
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get_sitemap_urls() -> list[str]:
    urls = []
    for i in range(1, 10):
        sm_url = f"https://www.ticketmelon.com/sitemap-event{i}.xml"
        try:
            r = requests.get(sm_url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                break
            # Extract URLs
            for m in re.finditer(r"<loc>(.*?)</loc>", r.text):
                urls.append(m.group(1))
        except Exception:
            break
    print(f"Found {len(urls)} URLs from sitemaps")
    return urls


def parse_event_page(url: str) -> dict | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None

        # Check if it's a Bangkok event
        if "bangkok" not in r.text.lower():
            return None

        # Try __NEXT_DATA__
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>({.*?})</script>', r.text, re.S)
        if m:
            data = json.loads(m.group(1))
            page_data = data.get("props", {}).get("pageProps", {}).get("eventData", {})
            if not page_data:
                page_data = data.get("props", {}).get("pageProps", {}).get("event", {})
            if page_data:
                title = page_data.get("name", page_data.get("title", ""))
                start = page_data.get("start_date", "")
                venue = page_data.get("venue", {}).get("name", "") if isinstance(page_data.get("venue"), dict) else ""
                price = page_data.get("price_text", "")
                return {
                    "title": title,
                    "date": start,
                    "venue": venue,
                    "price": price,
                }

        # Fallback regex
        title_m = re.search(r'<h1[^>]*>(.*?)</h1>', r.text, re.S)
        title = re.sub(r'<.*?>', '', title_m.group(1)).strip() if title_m else ""

        date_m = re.search(r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})', r.text)
        date = date_m.group(1) if date_m else ""

        return {"title": title, "date": date, "venue": "", "price": ""}
    except Exception as e:
        print(f"    Error parsing {url}: {e}")
        return None


def run():
    urls = get_sitemap_urls()
    # Filter Bangkok events - check page content instead of URL
    event_urls = urls  # Scrape all and filter by content
    print(f"Event URLs to scrape: {len(event_urls)}")

    events = []
    for i, url in enumerate(event_urls):
        if i % 20 == 0:
            print(f"[{i}/{len(event_urls)}] {url}")
        data = parse_event_page(url)
        if data and data.get("title"):
            events.append({
                "source": "ticketmelon",
                "sourceId": url.rstrip("/").split("/")[-1],
                "title": data["title"],
                "artist": data["title"].split(":")[0].split("-")[0].strip(),
                "date": data.get("date"),
                "venue": data.get("venue", ""),
                "link": url,
                "linkLabel": "Ticketmelon",
                "isInternational": bool(re.search(r"[a-zA-Z]", data["title"])) and not re.search(r"[\u0e00-\u0e7f]", data["title"]),
                "genre": "Concert",
                "price": data.get("price"),
                "scrapedAt": datetime.now().isoformat(),
            })
        time.sleep(0.5)

    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/ticketmelon_raw.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"source": "ticketmelon", "count": len(events), "events": events}, f, ensure_ascii=False, indent=2)
    print(f"Scraped {len(events)} Ticketmelon events -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
