#!/usr/bin/env python3
"""Scraper for Thai Ticket Major detail pages with rate-limit handling."""
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

FEED_URL = "https://www.thaiticketmajor.com/assets/event.json"
BASE_URL = "https://www.thaiticketmajor.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

THAI_MONTHS = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3,
    "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
    "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9,
    "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3,
    "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
    "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9,
    "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
}


def parse_thai_date(date_text: str) -> str | None:
    if not date_text:
        return None
    text = re.sub(r'^วัน[^ที่]*ที่\s*', '', date_text).strip()
    m = re.search(r'(\d{1,2})\s+([^ที่\d\s]+)\s+(\d{4})', text)
    if not m:
        return None
    day = int(m.group(1))
    month_str = m.group(2).strip()
    buddhist_year = int(m.group(3))
    gregorian_year = buddhist_year - 543
    month = THAI_MONTHS.get(month_str)
    if not month:
        for key, val in THAI_MONTHS.items():
            if key in month_str or month_str in key:
                month = val
                break
    if not month:
        return None
    try:
        return datetime(gregorian_year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return None


def extract_fields(text: str) -> dict:
    result = {"dateText": None, "venue": None, "doorTime": None, "price": None, "date": None}
    dm = re.search(r'วันที่แสดง\s*\n\s*([^\n]+)', text)
    if dm:
        result["dateText"] = dm.group(1).strip()
        result["date"] = parse_thai_date(result["dateText"])
    vm = re.search(r'สถานที่แสดง\s*\n\s*([^\n]+)', text)
    if vm:
        result["venue"] = vm.group(1).strip()
    tm = re.search(r'ประตูเปิด\s*\n\s*([^\n]+)', text)
    if tm:
        result["doorTime"] = tm.group(1).strip()
    pm = re.search(r'ราคาบัตร\s*\n\s*([^\n]+)', text)
    if pm:
        result["price"] = pm.group(1).strip()
    return result


def scrape_detail(page, link: str) -> dict:
    url = link if link.startswith("http") else f"{BASE_URL}{link}"
    result = {"url": url, "dateText": None, "venue": None, "doorTime": None, "price": None, "date": None, "blocked": False}
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)
        text = page.evaluate("() => document.body.innerText")
        if "วันที่แสดง" in text:
            result.update(extract_fields(text))
        elif "Verification Required" in text or "too frequent" in text.lower():
            result["blocked"] = True
    except Exception as e:
        print(f"    Error: {e}")
    return result


def run():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/ttm_detail.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing progress
    existing = {}
    if out_path.exists():
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for e in data.get("events", []):
            existing[e["sourceId"]] = e
        print(f"Loaded {len(existing)} existing events from {out_path}")

    print("Fetching TTM feed...")
    feed = requests.get(FEED_URL, headers=HEADERS, timeout=30).json()
    concerts = [item for item in feed if "concert" in item.get("link", "")]
    print(f"Found {len(concerts)} concert items in feed")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page.set_viewport_size({"width": 1366, "height": 768})

        enriched = []
        for i, item in enumerate(concerts):
            title = item.get("title_en") or item.get("title_th", "")
            link = item.get("link", "")
            source_id = link.rstrip(".html").split("/")[-1]
            url = link if link.startswith("http") else f"{BASE_URL}{link}"

            # Skip if already scraped and has date
            if source_id in existing and existing[source_id].get("date"):
                print(f"[{i+1}/{len(concerts)}] SKIP (cached) {title[:45]}")
                enriched.append(existing[source_id])
                continue

            print(f"[{i+1}/{len(concerts)}] SCRAPE {title[:45]}...")

            detail = scrape_detail(page, link)
            if detail.get("blocked"):
                print("    BLOCKED. Waiting 60s...")
                time.sleep(60)
                detail = scrape_detail(page, link)
                if detail.get("blocked"):
                    print("    Still blocked. Saving progress and exiting.")
                    break

            enriched.append({
                "source": "thaiticketmajor",
                "sourceId": source_id,
                "title": title,
                "artist": title.split(":")[0].split("-")[0].split("|")[0].strip(),
                "date": detail["date"],
                "dateText": detail["dateText"],
                "venue": detail["venue"],
                "link": url,
                "linkLabel": "Thai Ticket Major",
                "isInternational": bool(re.search(r'[a-zA-Z]', title)) and not re.search(r'[฀-๿]', title),
                "genre": "Concert",
                "price": detail["price"],
                "doorTime": detail["doorTime"],
                "scrapedAt": datetime.now().isoformat(),
            })

            # Longer delay to avoid rate limiting
            delay = random.uniform(8, 15)
            time.sleep(delay)

        browser.close()

    # Merge with existing cached items we didn't process
    for source_id, event in existing.items():
        if not any(e["sourceId"] == source_id for e in enriched):
            enriched.append(event)

    output = {"source": "thaiticketmajor", "count": len(enriched), "events": enriched}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    with_dates = sum(1 for e in enriched if e["date"])
    print(f"\nScraped {len(enriched)} TTM concerts -> {out_path}")
    print(f"  With dates: {with_dates}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
