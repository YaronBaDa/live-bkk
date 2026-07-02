# Live / BKK — Principal Engineer Review
**Date:** 2026-07-02  
**Reviewer:** Ludwig (Principal Engineer)  
**Scope:** Production readiness, scalability, multi-city expansion  
**Current State:** 262 concerts · 92 venues · 101 artists · Single-file SPA + Python scrapers

---

## Executive Summary

The product is **beautifully designed and functionally solid** for a personal prototype. The frontend is accessible, responsive, and performant. The data pipeline works. But **it is not production-ready for public use** in its current form. The scrapers are brittle, data integrity is unguarded, there is no observability, and the architecture is locked to a single city.

**Verdict:** Fix P0s before sharing publicly. Address P1s within 2–4 weeks of launch. P2s can follow.

---

## P0 — CRITICAL (Fix Before Public Launch)

### 1. No CI/CD Pipeline — Data Is Stale
**Problem:** The `.github/workflows/` directory referenced in README is **missing from the repo**. The scrapers are not running automatically. The site shows "Updated weekly" but the last manual commit was some time ago. Data will rot within days of sharing.

**Fix:**
- Add `.github/workflows/daily-scrape.yml` (see skill reference)
- Use `continue-on-error: true` per source so one broken scraper doesn't kill the whole run
- Commit `data/` changes back to repo with a bot identity
- Add a `data/meta.json` with `lastScrapedAt` and `sourceHealth` so the frontend can show "Updated 2 hours ago" vs "Updated 6 days ago (may be stale)"

### 2. Scrapers Are Brittle and Untested
**Problem:**
- **Ticketmelon:** `parse_event_page()` does a `"bangkok" in r.text.lower()` which will silently drop Bangkok events if the page says "BKK" or "Krungthep". The `__NEXT_DATA__` extraction has no fallback if the JSON shape changes.
- **TTM detail:** Uses Playwright for 49 detail pages with 8–15s delays. No retry logic, no circuit breaker. If blocked, it waits 60s once and gives up.
- **LNT:** Infers year from current month — this will produce **wrong dates** in December for January events. Playwright is overkill for what could be a static fetch.
- **Eventpop:** Not in the current pipeline at all, yet 13 events in the dataset depend on it.

**Fix:**
- Add `tenacity` retry decorators with exponential backoff
- Add schema validation on scraped output (Pydantic or dataclasses)
- Add a `--health-check` mode that reports which sources returned data vs failed
- Cache raw HTML responses for 24h to speed up re-runs and reduce hammering
- Replace LNT Playwright with `requests` + BeautifulSoup if possible (check if the data is in the initial HTML)

### 3. Deduplication Is Broken
**Problem:** `merge.py` dedupes by `sourceId` (title slug). Two sources listing the same show get different slugs → duplicate entries. Example: TTM and Ticketmelon both listing the same arena show.

**Current:**
```python
eid = e.get("sourceId") or re.sub(r"[^a-z0-9]+", "-", e.get("title", "").lower()).strip("-")
```

**Fix:**
- Generate a canonical fingerprint: `normalize_title(title) + "::" + dateSort + "::" + normalize_venue(venue)`
- Maintain a `canonical_id` mapping table
- Add a manual `merge_candidates.json` for ambiguous cases (human-reviewed)

### 4. No Data Validation = Silent Corruption
**Problem:** Bad scraper output flows straight into `concerts.json`. A single malformed date or missing `id` can break the frontend router. There are no schema guards.

**Fix:**
```python
from pydantic import BaseModel, HttpUrl, Field, validator

class Concert(BaseModel):
    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    dateSort: str | None = None
    status: Literal["upcoming", "past", "festival"]
    link: HttpUrl
    # ... validators for date format, price parsing, etc.
```
- Validate after every scrape, before merge
- Fail the pipeline on validation errors (with clear logs)

### 5. Frontend Loads Everything Into Memory
**Problem:** `CONCERTS = await cRes.json()` loads all 262 events (and growing) into a single array. Filtering, sorting, and rendering are all O(n) on the full dataset. At 1,000+ events, mobile browsers will lag.

**Fix (short-term):**
- Add pagination or "Load more" to the grid
- Virtualize the list if keeping infinite scroll (but simpler: page numbers)

**Fix (long-term):** See Architecture section below.

---

## P1 — HIGH (Within 2–4 Weeks of Launch)

### 6. No Observability
**Problem:** When a scraper breaks, you won't know until a user DMs you. There are no logs, alerts, or dashboards.

**Fix:**
- Add structured logging to every scraper (`structlog` or plain JSON logs)
- Emit a `health.json` after each run:
```json
{
  "runAt": "2026-07-02T06:00:00+07:00",
  "sources": {
    "ticketmelon": {"events": 194, "durationSec": 45, "status": "ok"},
    "ttm": {"events": 0, "durationSec": 120, "status": "error", "error": "Rate limited"}
  }
}
```
- If a source fails 3 runs in a row, flag it on the frontend ("Some sources may be missing")

### 7. Image Strategy Is Risky
**Problem:** All 262 concerts have `image` URLs pointing to Ticketmelon S3, Unsplash, or source CDNs. If Ticketmelon changes their bucket path or deletes old posters, you get broken images. No fallback handling beyond a single Unsplash URL.

**Fix:**
- Download and self-host images in a `data/images/` directory (Git LFS or separate assets repo)
- Or use a thumbnail proxy service (Cloudflare Images, Imgix) with fallback
- At minimum: add `onerror` handlers on `<img>` tags to swap to fallback

### 8. No PWA / Offline Support
**Problem:** Users in Bangkok often have spotty mobile data (BTS/MRT dead zones). The site is a blank page without connectivity.

**Fix:**
- Add a Service Worker that caches `index.html`, CSS/JS, and the JSON data
- Add a `manifest.json` for "Add to Home Screen"
- Show cached data with a "Last updated: X" banner when offline

### 9. Search Is Client-Side Only
**Problem:** Search does `hay.includes(needle)` across all fields. This is fine for 262 items, but at 1,000+ it will feel sluggish on mid-range Android phones.

**Fix:**
- Short-term: debounce properly (already done at 120ms — good)
- Medium-term: build an inverted index at merge time (word → concert IDs) and ship it as `data/search-index.json`
- Long-term: use a search API (Algolia, Meilisearch, or a lightweight Cloudflare Worker)

### 10. Missing SEO / Shareability
**Problem:**
- No Open Graph meta tags per concert (every share looks identical)
- No `sitemap.xml`
- Hash-based routing (`#/concert/id`) is invisible to crawlers
- No server-side rendering

**Fix:**
- Add dynamic OG tags via a Cloudflare Worker or pre-render popular pages
- Generate `sitemap.xml` in the pipeline
- Consider migrating to `history.pushState` + a lightweight static site generator (11ty, Astro) for pre-rendered detail pages

---

## P2 — MEDIUM (Post-Launch / Expansion Prep)

### 11. Schema Is Not Multi-City Ready
**Problem:** The data model assumes Bangkok:
- `venueName` is a string, not a structured object with city/region/country
- `VENUES` is a flat dict with no geographic hierarchy
- Footer says "Krungthep · 13.7563°N · 100.5018°E"
- Brand is "Live / BKK"

**Fix:**
- Add `city`, `region`, `country` to venue schema
- Add `location` object to concerts (lat/lon for map views later)
- Move brand/city config to a `config.json` so the same frontend can render as "Live / SGN" or "Live / BKK"

### 12. No Test Suite
**Problem:** Zero tests. Changing the merge logic or a scraper regex is scary.

**Fix:**
- Unit tests for `normalize_date`, dedup logic, genre heuristics
- Snapshot tests for scraper output (check in a sample HTML file, assert parsed result)
- Frontend: basic Cypress/Playwright smoke tests (load page, filter by genre, click into detail)

### 13. No Admin / Curation UI
**Problem:** Fixing a bad genre, merging duplicates, or hiding a cancelled show requires editing JSON by hand.

**Fix:**
- A simple admin HTML page (password-protected via Cloudflare Access or a static hash check) that lets you:
  - Override genres
  - Mark events as cancelled
  - Merge duplicates
  - Write back to JSON

### 14. Monetization / Sustainability
**Problem:** If this gets popular, you'll want to cover costs or pay contributors.

**Options:**
- Affiliate links to ticketing platforms (check TTM / Ticketmelon affiliate programs)
- "Promoted" listings for venues/organizers
- Patreon / Ko-fi for "supporter" early access
- Keep it clean and non-commercial — your call, but decide before launch

---

## Expansion Roadmap: Beyond Bangkok

### Phase 1 — Multi-City Schema (2–3 days)
1. Update `Concert` schema:
```json
{
  "id": "sgn-tyler-creator",
  "title": "Tyler, The Creator",
  "location": { "city": "Ho Chi Minh City", "country": "VN", "lat": 10.8, "lon": 106.7 },
  "venueId": "vietnam-nhathat",
  ...
}
```
2. Update ` Venue` schema with `city`, `country`
3. Add `config.json`:
```json
{ "brand": "Live / SEA", "cities": ["bangkok", "ho-chi-minh-city", "kuala-lumpur", "singapore"] }
```
4. Make the frontend city-aware (filter by city, city selector in nav)

### Phase 2 — Source Plugin Architecture (1 week)
Each city needs its own scrapers. Abstract the scraper interface:
```python
class BaseScraper(ABC):
    city: str
    def scrape(self) -> list[RawEvent]: ...
    def health_check(self) -> ScraperHealth: ...
```
- `BangkokScraper` wraps TTM, Ticketmelon, LNT, Eventpop
- `SingaporeScraper` wraps SISTIC, BookMyShow SG
- `KLScraper` wraps BookMyShow MY, Ticket2U

Run all city scrapers in parallel. Merge into a single `concerts.json` with city tags.

### Phase 3 — Edge Deployment (1–2 weeks)
- Move data to a **Cloudflare D1** or **SQLite-on-Workers** database
- Frontend queries a **Cloudflare Worker** API: `GET /api/concerts?city=bangkok&genre=hiphop`
- Workers handle caching, pagination, search, and geo-routing
- Scrapers run in GitHub Actions, push to D1 via REST API
- This removes the GitHub Pages file-size limit and enables real-time features

### Phase 4 — User Features (ongoing)
- User accounts (Clerk/Auth0) + "Save this show"
- Push notifications for price drops or new announcements
- Community submissions ("I found a show on Facebook — add it")
- Calendar export (.ics)
- WhatsApp/Telegram bot for daily digest

---

## Recommended Architecture (Target State)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  GitHub Actions │────▶│  Cloudflare D1   │◀────│  Cloudflare     │
│  (scrapers)     │     │  (SQLite DB)     │     │  Worker (API)   │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                           ┌──────────────────────────────┘
                           ▼
                    ┌──────────────┐
                    │  Static SPA  │  (Vercel / Cloudflare Pages)
                    │  (React/Vue) │
                    └──────────────┘
```

**Why this over keeping GitHub Pages?**
- GitHub Pages is static-file only. No API, no server-side search, no user accounts.
- At 1,000+ concerts, a 500KB JSON file on every page load is wasteful.
- A Worker API returns only what the user needs (20 concerts, filtered, sorted).
- D1 costs ~$0 for low traffic. Workers have a generous free tier.

**Why not keep it simple?**
You can! The SPA-on-GitHub-Pages approach works for <500 events and <1,000 DAU. The migration path above is incremental — you don't have to do it all at once.

---

## Immediate Action Items (This Week)

| # | Task | Effort | Owner |
|---|------|--------|-------|
| 1 | Add GitHub Actions workflow for daily scraping | 2h | You + Me |
| 2 | Add Pydantic schema validation to `merge.py` | 3h | Me |
| 3 | Fix LNT year inference bug | 30m | Me |
| 4 | Add `data/health.json` and surface it in footer | 1h | Me |
| 5 | Add `onerror` image fallback + lazy loading | 1h | Me |
| 6 | Write scraper unit tests (snapshot) | 2h | Me |
| 7 | Add `city` field to schema (Bangkok default) | 1h | Me |

---

## Conclusion

Live / BKK is a **great product** with a clear value prop and beautiful execution. The gap between "works for me" and "works for thousands" is well understood and addressable. The biggest risks are **data staleness** (no CI), **data corruption** (no validation), and **silent scraper failures** (no observability). Fix those three and you can share it with confidence.

Expansion to SEA cities is architecturally straightforward once the schema and scraper interfaces are city-agnostic. The core challenge becomes **source discovery** in each new market, not the tech.

**Ready to start on the P0s?**