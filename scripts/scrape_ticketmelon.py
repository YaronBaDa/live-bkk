#!/usr/bin/env python3
"""
Scraper for Ticketmelon (ticketmelon.com)
Uses sitemaps to discover events, then scrapes __NEXT_DATA__ from each page.
IMPROVED: Better Bangkok detection using venue data and location hints.
"""
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Expanded Bangkok detection keywords
BANGKOK_KEYWORDS = [
    "bangkok", "bkk", "krungthep", "krung thep",
    "sukhumvit", "silom", "sathorn", "ratchada", " RCA",
    "thonglor", "ekkamai", "ari", "ladprao", "ratchathewi",
    "pathumwan", "chatuchak", "huai khwang", "rama ",
    "impact arena", "thunder dome", "union hall",
    "live arena", "lido connect", "de commune", "horn",
    "mr.fox", "cloud 11", "blueprint", "melt livehouse",
    "speakerbox", "bangkok island", "jodd fairs",
]


def is_bangkok_event(page_data: dict, page_text: str) -> bool:
    """Determine if event is in Bangkok using multiple signals."""
    text = page_text.lower()
    # Check venue name
    venue = ""
    v = page_data.get("venue", {})
    if isinstance(v, dict):
        venue = str(v.get("name", "")) + " " + str(v.get("address", ""))
    # Check title — coerce to string in case API returns dict
    name_val = page_data.get("name", page_data.get("title", ""))
    title = str(name_val) if not isinstance(name_val, str) else name_val
    title = title.lower()
    # Check description
    desc = str(page_data.get("description", "")).lower()
    # Check timezone
    tz = str(page_data.get("timezone", "")).lower()

    combined = f"{title} {venue} {desc} {text} {tz}"
    return any(kw in combined for kw in BANGKOK_KEYWORDS)


def get_sitemap_urls() -> list[str]:
    urls = []
    for i in range(1, 10):
        sm_url = f"https://www.ticketmelon.com/sitemap-event{i}.xml"
        try:
            r = requests.get(sm_url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                break
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

        # Try __NEXT_DATA__ first
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>({.*?})</script>', r.text, re.S)
        if m:
            data = json.loads(m.group(1))
            page_data = data.get("props", {}).get("pageProps", {}).get("eventData", {})
            if not page_data:
                page_data = data.get("props", {}).get("pageProps", {}).get("event", {})

            if page_data:
                # Check if Bangkok event
                if not is_bangkok_event(page_data, r.text):
                    return None

                name_val = page_data.get("name", page_data.get("title", ""))
                title = str(name_val) if not isinstance(name_val, str) else name_val
                start = page_data.get("start_date", "")
                end = page_data.get("end_date", "")
                venue = ""
                v = page_data.get("venue", {})
                if isinstance(v, dict):
                    venue = str(v.get("name", ""))
                price = str(page_data.get("price_text", ""))
                image = ""
                if isinstance(page_data.get("image"), dict):
                    image = page_data["image"].get("url", "")
                elif isinstance(page_data.get("image"), str):
                    image = page_data["image"]
                # Try poster as fallback
                if not image and isinstance(page_data.get("poster"), dict):
                    image = page_data["poster"].get("url", "")

                return {
                    "title": title,
                    "date": start,
                    "endDate": end,
                    "venue": venue,
                    "price": price,
                    "image": image,
                }

        # Fallback: check if Bangkok via text, then regex extract
        if not any(kw in r.text.lower() for kw in BANGKOK_KEYWORDS):
            return None

        title_m = re.search(r'<h1[^>]*>(.*?)</h1>', r.text, re.S)
        title = re.sub(r'<.*?>', '', title_m.group(1)).strip() if title_m else ""
        date_m = re.search(r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})', r.text)
        date = date_m.group(1) if date_m else ""

        return {"title": title, "date": date, "venue": "", "price": "", "image": ""}
    except Exception as e:
        print(f"    Error parsing {url}: {e}")
        return None


def run():
    urls = get_sitemap_urls()
    print(f"Event URLs to scrape: {len(urls)}")

    events = []
    for i, url in enumerate(urls):
        if i % 20 == 0:
            print(f"[{i}/{len(urls)}] {url}")
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
                "image": data.get("image"),
                "scrapedAt": datetime.now().isoformat(),
            })
        time.sleep(0.3)

    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/ticketmelon_raw.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"source": "ticketmelon", "count": len(events), "events": events}, f, ensure_ascii=False, indent=2)
    print(f"Scraped {len(events)} Ticketmelon events -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
