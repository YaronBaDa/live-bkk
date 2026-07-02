#!/usr/bin/env python3
"""Merge data from all sources into frontend-ready JSON files."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def normalize_title(title):
    t = (title or "").lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\bin bangkok\b|\bthailand\b|\b20\d{2}\b|\btour\b|\blive\b|\bfestival\b|\bconcert\b", "", t)
    return re.sub(r"\s+", " ", t).strip()


def normalize_venue(venue):
    v = (venue or "").lower()
    v = re.sub(r"[^\w\s]", " ", v)
    return re.sub(r"\s+", " ", v).strip()


def normalize_date(date_str):
    if not date_str:
        return None
    # ISO format
    if re.match(r"\d{4}-\d{2}-\d{2}", str(date_str)):
        ds = date_str[:10]
        # Fix obvious year errors (2126 -> 2026)
        if ds.startswith("21") and int(ds[:4]) > 2100:
            ds = "20" + ds[2:]
        return ds
    # "Thu 23 Apr 2026" format
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", str(date_str))
    if m:
        try:
            dt = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %b %Y")
            ds = dt.strftime("%Y-%m-%d")
            if ds.startswith("21") and int(ds[:4]) > 2100:
                ds = "20" + ds[2:]
            return ds
        except ValueError:
            pass
    return None


# Keywords that indicate non-music events to filter out
NON_MUSIC_KEYWORDS = [
    "comic con", "marathon", "run ", "ride ", "yoga", "workshop", "conference",
    "seminar", "expo", "fair ", "flea market", "badminton", "muay thai",
    "kickboxing", "card ", "cardgame", "tcg", "barber", "business", "sme ",
    "webinar", "bootcamp", "dance camp", "dance class", "cooking class",
    "film screening", "art battle", "runclub", "fun run", "5k", "10k",
    "muaythai", "boxing", "mma ", "fight ", "match ", "tournament",
    "football", "soccer", "basketball", "volleyball", "badminton",
    "triathlon", "cycling", "swim ", "swimming", "climbing", "hiking",
    "marche ", "market ", "bazaar", "garage sale", "open house",
    "career fair", "job fair", "networking", "summit", "symposium",
    "training ", "course ", "class ", "lesson ", "retreat ",
    "food tour", "walking tour", "city tour", "pub crawl",
    "wine tasting", "beer tasting", "whisky tasting",
    "fashion show", "beauty pageant", "modelling",
    "dog show", "pet show", "cat expo", "animal ",
    "magic show", "circus", "stand-up comedy", "comedy night",
    "poetry slam", "poetry reading", "book club", "book launch",
    "art exhibition", "art show", "gallery opening",
    "photo shoot", "photography", "camera ",
    "tech ", "startup", "hackathon", "coding",
    "fitness", "gym ", "crossfit", "pilates", "aerobics",
    "health ", "wellness", "spa ", "massage",
    "charity ", "fundraising", "donation", "blood drive",
    "political", "rally", "protest", "demonstration",
    "religious", "prayer", "meditation", "spiritual",
    "wedding", "bridal", "engagement", "anniversary party",
    "birthday party", "private party", "house party",
    "game night", "board game", "quiz night", "trivia",
    "escape room", "vr experience", "arcade",
    "camping", "glamping", "outdoor ", "nature ",
    "beach clean", "volunteer", "community service",
    "graduation", "ceremony", "awards", "graduation",
    "reunion", "alumni", "homecoming",
    "school ", "university ", "college ", "academic",
    "kids ", "children", "family day", "parent",
    "baby ", "toddler", "preschool", "kindergarten",
    "summer camp", "winter camp", "day camp",
    "language ", "english class", "thai class", "chinese class",
    "cooking ", "baking ", "culinary",
    "dance ", "ballet", "contemporary dance", "traditional dance",
    "cultural ", "heritage", "history ", "museum ",
    "science ", "robotics", "astronomy", "planetarium",
    "carnival", "fun fair", "amusement", "theme park",
]


def is_music_event(title: str) -> bool:
    """Filter out obvious non-music events."""
    t = title.lower()
    # Check non-music keywords
    for kw in NON_MUSIC_KEYWORDS:
        if kw in t:
            return False
    return True


def load_json(path):
    if Path(path).exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def dedup_key(title, date, venue):
    """Canonical fingerprint for deduplication."""
    return f"{normalize_title(title)}::{date or 'tba'}::{normalize_venue(venue)}"


def run():
    existing = load_json("data/existing_raw.json")
    ttm = load_json("data/ttm_raw.json")
    lnt = load_json("data/lnt_raw.json")
    ticketmelon = load_json("data/ticketmelon_raw.json")
    eventpop = load_json("data/eventpop_raw.json")
    allevents = load_json("data/allevents_raw.json")

    # Start with existing data (has the most complete info)
    all_events = {}
    seen_keys = {}

    def add_event(e, source_name):
        title = e.get("title", "")
        if not title:
            return
        # Filter out non-music events
        if not is_music_event(title):
            return
        eid = e.get("id") or e.get("sourceId") or re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        date = normalize_date(e.get("date"))
        venue = e.get("venueName") or e.get("venue", "")
        key = dedup_key(title, date, venue)

        # Filter out events before 2024 (unless no date — keep as TBA)
        if date and date < "2024-01-01":
            return

        # Check for duplicates by canonical key
        if key in seen_keys:
            existing_id = seen_keys[key]
            # Merge: prefer existing data, but fill gaps from new source
            existing_event = all_events[existing_id]
            if not existing_event.get("dateSort") and date:
                existing_event["dateSort"] = date
            if not existing_event.get("venueId") and e.get("venueId"):
                existing_event["venueId"] = e["venueId"]
            if not existing_event.get("image") and e.get("image"):
                existing_event["image"] = e["image"]
            # Track all sources that found this event
            if "sources" not in existing_event:
                existing_event["sources"] = [existing_event.get("source", "unknown")]
            if source_name not in existing_event["sources"]:
                existing_event["sources"].append(source_name)
            return

        # Check by sourceId as fallback
        if eid in all_events:
            existing_event = all_events[eid]
            if not existing_event.get("dateSort") and date:
                existing_event["dateSort"] = date
            return

        seen_keys[key] = eid

        if "id" in e and "dateSort" in e:
            # Already in frontend format (from existing)
            all_events[eid] = e
            return

        # Convert to frontend format
        event = {
            "id": eid,
            "title": title,
            "date": e.get("dateText") or e.get("date", ""),
            "time": e.get("time", ""),
            "dateSort": date,
            "added": e.get("added") or datetime.now().strftime("%Y-%m-%d"),
            "tags": e.get("tags") or [e.get("genre", "other").lower().replace(" ", "-")],
            "venueId": e.get("venueId", ""),
            "venueName": venue,
            "artistText": e.get("artistText") or e.get("artist", ""),
            "artists": e.get("artists", []),
            "genre": e.get("genre", "Live"),
            "status": e.get("status") or ("upcoming" if date and date >= datetime.now().strftime("%Y-%m-%d") else "upcoming"),
            "price": e.get("price") or "On sale",
            "minPrice": e.get("minPrice"),
            "currency": e.get("currency", "THB"),
            "tag": e.get("tag", ""),
            "image": e.get("image", ""),
            "fallback": "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?auto=format&fit=crop&w=1600&q=80",
            "blurb": e.get("blurb") or f"{title} — live in Bangkok via {e.get('linkLabel', 'Unknown')}.",
            "long": e.get("long") or e.get("blurb") or f"{title} — live in Bangkok via {e.get('linkLabel', 'Unknown')}.",
            "link": e.get("link", ""),
            "linkLabel": e.get("linkLabel") or e.get("source", "Tickets"),
            "source": e.get("source", source_name),
        }
        all_events[eid] = event

    # Add existing events first (they have richest data)
    for e in existing.get("events", []):
        add_event(e, "existing")

    # Add scraped data from all sources
    for source_name, source_data in [
        ("thaiticketmajor", ttm),
        ("livenationtero", lnt),
        ("ticketmelon", ticketmelon),
        ("eventpop", eventpop),
        ("allevents", allevents),
    ]:
        for e in source_data.get("events", []):
            add_event(e, source_name)

    concerts = list(all_events.values())

    # Load venues and artists from existing
    venues = load_json("data/venues.json")
    artists = load_json("data/artists.json")

    # Sort: upcoming first, then by date
    def sort_key(c):
        ds = c.get("dateSort") or "9999-99-99"
        is_past = c.get("status") == "past"
        return (is_past, ds)

    concerts.sort(key=sort_key)

    # Save
    with open("data/concerts.json", "w", encoding="utf-8") as f:
        json.dump(concerts, f, ensure_ascii=False, indent=2)
    with open("data/venues.json", "w", encoding="utf-8") as f:
        json.dump(venues, f, ensure_ascii=False, indent=2)
    with open("data/artists.json", "w", encoding="utf-8") as f:
        json.dump(artists, f, ensure_ascii=False, indent=2)

    # Stats
    from collections import Counter
    sources = Counter(c.get("source", "unknown") for c in concerts)
    print(f"Merged {len(concerts)} concerts -> data/concerts.json")
    print(f"  By source: {dict(sources)}")
    print(f"  Venues: {len(venues)}")
    print(f"  Artists: {len(artists)}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(run())
