#!/usr/bin/env python3
"""Scraper for Eventpop (eventpop.me) — Bangkok music events."""
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://www.eventpop.me"


def parse_search_page(page_num: int) -> list[dict]:
    """Scrape a single search results page."""
    url = f"{BASE}/search?q=bangkok&category=music&page={page_num}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  Page {page_num}: HTTP {r.status_code}")
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.find_all("a", href=lambda x: x and x.startswith("/e/"))
        events = []
        for a in cards:
            href = a.get("href", "")
            # Extract event ID from /e/12345/slug
            m = re.match(r"/e/(\d+)", href)
            if not m:
                continue
            event_id = m.group(1)
            # Get title and date from card text
            text = a.get_text(separator="\n", strip=True)
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            title = lines[0] if lines else ""
            date = lines[1] if len(lines) > 1 else ""
            events.append({
                "eventId": event_id,
                "slug": href,
                "title": title,
                "dateText": date,
            })
        return events
    except Exception as e:
        print(f"  Error on page {page_num}: {e}")
        return []


def parse_detail_page(event_id: str, slug: str) -> dict | None:
    """Scrape event detail page for rich metadata."""
    url = f"{BASE}{slug}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return None
        text = r.text
        soup = BeautifulSoup(text, "html.parser")

        # OG metadata
        def og(prop):
            tag = soup.find("meta", property=f"og:{prop}")
            return tag["content"] if tag else ""

        title = og("title") or soup.find("title")
        title = title.get_text() if hasattr(title, "get_text") else str(title)
        title = title.replace("Eventpop | ", "").strip()

        start_time = og("start_time")
        end_time = og("end_time")
        location = og("location")

        # Extract gon data (Eventpop's injected JS config)
        gon_match = re.search(r'gon\.event_detail_id="?(\d+)"?', text)
        detail_id = gon_match.group(1) if gon_match else event_id

        venue_match = re.search(r'gon\.map_title="([^"]+)"', text)
        venue_name = venue_match.group(1) if venue_match else location

        # Price from page text
        price_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*THB', text)
        price = f"{price_match.group(1)} THB" if price_match else ""

        # Image
        image = og("image")

        # Parse date from start_time (ISO 8601)
        date_str = None
        if start_time:
            try:
                dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d")
            except:
                pass

        return {
            "title": title,
            "date": date_str,
            "dateText": start_time,
            "venue": venue_name,
            "price": price,
            "image": image,
            "link": url,
        }
    except Exception as e:
        print(f"    Error parsing detail {event_id}: {e}")
        return None


def run():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/eventpop_raw.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Discover events from search pages
    all_discovered = []
    for page in range(1, 10):
        print(f"-> Eventpop search page {page}")
        events = parse_search_page(page)
        if not events:
            break
        all_discovered.extend(events)
        time.sleep(0.8)

    print(f"Discovered {len(all_discovered)} events from search")

    # Scrape detail pages
    scraped = []
    for i, ev in enumerate(all_discovered):
        print(f"[{i+1}/{len(all_discovered)}] {ev['title'][:50]}...")
        detail = parse_detail_page(ev["eventId"], ev["slug"])
        if detail and detail.get("title"):
            scraped.append({
                "source": "eventpop",
                "sourceId": ev["eventId"],
                "title": detail["title"],
                "artist": detail["title"].split(":")[0].split("-")[0].strip(),
                "date": detail["date"],
                "dateText": detail["dateText"],
                "venue": detail["venue"],
                "link": detail["link"],
                "linkLabel": "Eventpop",
                "isInternational": bool(re.search(r"[a-zA-Z]", detail["title"])) and not re.search(r"[\u0e00-\u0e7f]", detail["title"]),
                "genre": "Concert",
                "price": detail["price"],
                "image": detail["image"],
                "scrapedAt": datetime.now().isoformat(),
            })
        time.sleep(0.5)

    output = {"source": "eventpop", "count": len(scraped), "events": scraped}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Scraped {len(scraped)} Eventpop events -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
