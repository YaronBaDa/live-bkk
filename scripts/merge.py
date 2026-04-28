#!/usr/bin/env python3
"""Merge data from all sources into frontend-ready JSON files."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def normalize_date(date_str):
    if not date_str:
        return None
    # Try ISO format
    if re.match(r"\d{4}-\d{2}-\d{2}", str(date_str)):
        return date_str[:10]
    # Try "Thu 23 Apr 2026" format
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", str(date_str))
    if m:
        try:
            dt = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %b %Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def load_json(path):
    if Path(path).exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def run():
    existing = load_json("data/existing_raw.json")
    ttm = load_json("data/ttm_raw.json")
    lnt = load_json("data/lnt_raw.json")
    ticketmelon = load_json("data/ticketmelon_raw.json")

    # Start with existing data (has the most complete info)
    all_events = {}
    for e in existing.get("events", []):
        eid = e.get("id") or re.sub(r"[^a-z0-9]+", "-", e.get("title", "").lower()).strip("-")
        all_events[eid] = e

    # Add/merge scraped data
    for source in [ttm, lnt, ticketmelon]:
        for e in source.get("events", []):
            eid = e.get("sourceId") or re.sub(r"[^a-z0-9]+", "-", e.get("title", "").lower()).strip("-")
            if eid in all_events:
                # Update if new data has a date and existing doesn't
                if e.get("date") and not all_events[eid].get("dateSort"):
                    all_events[eid]["dateSort"] = e["date"]
                continue
            # Convert to frontend format
            event = {
                "id": eid,
                "title": e.get("title", ""),
                "date": e.get("dateText") or e.get("date", ""),
                "time": "",
                "dateSort": normalize_date(e.get("date")),
                "added": datetime.now().strftime("%Y-%m-%d"),
                "tags": [e.get("genre", "other").lower().replace(" ", "-")],
                "venueId": "",
                "venueName": e.get("venue", ""),
                "artistText": e.get("artist", ""),
                "artists": [],
                "genre": e.get("genre", "Live"),
                "status": "upcoming" if e.get("date") and e.get("date") >= datetime.now().strftime("%Y-%m-%d") else "upcoming",
                "price": e.get("price") or "On sale",
                "minPrice": None,
                "currency": "THB",
                "tag": "",
                "image": "",
                "fallback": "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?auto=format&fit=crop&w=1600&q=80",
                "blurb": f"{e.get('title', '')} — live in Bangkok via {e.get('linkLabel', 'Unknown')}.",
                "long": f"{e.get('title', '')} — live in Bangkok via {e.get('linkLabel', 'Unknown')}.",
                "link": e.get("link", ""),
                "linkLabel": e.get("linkLabel", "Tickets"),
            }
            all_events[eid] = event

    concerts = list(all_events.values())

    # Load venues and artists from existing
    venues = load_json("data/venues.json")
    artists = load_json("data/artists.json")

    # Save
    with open("data/concerts.json", "w", encoding="utf-8") as f:
        json.dump(concerts, f, ensure_ascii=False, indent=2)
    with open("data/venues.json", "w", encoding="utf-8") as f:
        json.dump(venues, f, ensure_ascii=False, indent=2)
    with open("data/artists.json", "w", encoding="utf-8") as f:
        json.dump(artists, f, ensure_ascii=False, indent=2)

    print(f"Merged {len(concerts)} concerts -> data/concerts.json")
    print(f"  Venues: {len(venues)}")
    print(f"  Artists: {len(artists)}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(run())
