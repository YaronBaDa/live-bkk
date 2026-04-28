#!/usr/bin/env python3
"""Scraper for Live Nation Tero (livenationtero.co.th)"""
import json
import re
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://www.livenationtero.co.th/event/allevents"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

THAI_MONTHS = {
    "\u0e21.\u0e04.": 1, "\u0e01.\u0e1e.": 2, "\u0e21\u0e35.\u0e04.": 3,
    "\u0e40\u0e21.\u0e22.": 4, "\u0e1e.\u0e04.": 5, "\u0e21\u0e34.\u0e22.": 6,
    "\u0e01.\u0e04.": 7, "\u0e2a.\u0e04.": 8, "\u0e01.\u0e22.": 9,
    "\u0e15.\u0e04.": 10, "\u0e1e.\u0e22.": 11, "\u0e18.\u0e04.": 12,
    "\u0e21\u0e04": 1, "\u0e01\u0e1e": 2, "\u0e21\u0e35\u0e04": 3,
    "\u0e40\u0e21\u0e22": 4, "\u0e1e\u0e04": 5, "\u0e21\u0e34\u0e22": 6,
    "\u0e01\u0e04": 7, "\u0e2a\u0e04": 8, "\u0e01\u0e22": 9,
    "\u0e15\u0e04": 10, "\u0e1e\u0e22": 11, "\u0e18\u0e04": 12,
}


def parse_thai_date(day_str: str, month_str: str) -> str:
    day = int(re.search(r"\d+", day_str).group())
    month = THAI_MONTHS.get(month_str)
    if not month:
        for key, val in THAI_MONTHS.items():
            if key in month_str or month_str in key:
                month = val
                break
    if not month:
        return None
    year = datetime.now().year if month >= datetime.now().month else datetime.now().year + 1
    return datetime(year, month, day).strftime("%Y-%m-%d")


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        page.set_viewport_size({"width": 1366, "height": 768})
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        events = page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('a[href*="/event/"]').forEach(a => {
                    const href = a.href;
                    if (href.includes('/event/allevents') || href.includes('/login')) return;
                    const container = a.closest('li, article, div[class*="card"]') || a.parentElement;
                    const text = container ? container.innerText : '';
                    const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
                    results.push({href, lines});
                });
                return results;
            }
        """)
        browser.close()

    scraped = []
    for e in events:
        lines = e["lines"]
        if len(lines) < 4:
            continue
        # Lines: [day_of_week, day, month, title, artist, venue_city, cta]
        title = lines[3]
        artist = lines[4] if len(lines) > 4 else title
        date = None
        date_text = None
        if len(lines) > 2:
            date_text = f"{lines[1]} {lines[2]}"
            try:
                date = parse_thai_date(lines[1], lines[2])
            except Exception:
                pass
        venue = lines[5] if len(lines) > 5 else "TBC"
        venue = venue.replace("Bangkok | ", "") if venue else "TBC"

        scraped.append({
            "source": "livenationtero",
            "sourceId": e["href"].rstrip("/").split("/")[-1],
            "title": title,
            "artist": artist,
            "date": date,
            "dateText": date_text,
            "venue": venue,
            "link": e["href"],
            "linkLabel": "Live Nation Tero",
            "isInternational": bool(re.search(r"[a-zA-Z]", title)) and not re.search(r"[\u0e00-\u0e7f]", title),
            "genre": "Concert",
            "scrapedAt": datetime.now().isoformat(),
        })

    output = {"source": "livenationtero", "count": len(scraped), "events": scraped}
    out_path = sys.argv[1] if len(sys.argv) > 1 else "data/lnt_raw.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Scraped {len(scraped)} events from Live Nation Tero -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
