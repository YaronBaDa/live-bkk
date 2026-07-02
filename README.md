# Live / BKK

A directory of upcoming live music and festivals in Bangkok.

**Live site:** [yaronbada.github.io/live-bkk](https://yaronbada.github.io/live-bkk)

## Architecture

```
index.html          → Single-page app (fetches JSON data)
data/
  concerts.json     → Merged, deduplicated concert listings
  venues.json       → Venue profiles
  artists.json      → Artist profiles
  health.json       → Pipeline health report
scripts/
  scrape_ticketmelon.py
  scrape_ttm.py
  scrape_eventpop.py
  scrape_allevents.py
  scrape_lnt.py
  merge.py
  run_pipeline.py
.github/workflows/
  daily-scrape.yml  → Automated daily scraping + deployment
```

## Data Sources

| Source | Method | Coverage |
|--------|--------|----------|
| **Ticketmelon** | Sitemap + `__NEXT_DATA__` | ~500 Bangkok events |
| **Thai Ticket Major** | Public feed + detail pages | ~100 events |
| **Eventpop** | Search + OG metadata | ~30 events |
| **Live Nation Tero** | Playwright (homepage) | ~15 events |
| **AllEvents.in** | RSS feed | ~15 events |

## Automation

The site is automatically updated every day at **6:00 AM Bangkok time** via GitHub Actions:

1. All scrapers run in parallel
2. Data is merged, deduplicated, and filtered
3. `index.html` footer timestamp is updated
4. Changes are committed and pushed to `main`
5. GitHub Pages redeploys automatically

You can also trigger a manual run from **Actions → Daily Scrape & Deploy → Run workflow**.

## Local Development

```bash
# Clone
git clone https://github.com/YaronBaDa/live-bkk.git
cd live-bkk

# Install deps
pip install requests beautifulsoup4 playwright
playwright install chromium

# Run pipeline manually
python3 scripts/run_pipeline.py

# Serve locally
python3 -m http.server 8080
# open http://localhost:8080
```

## Pipeline Details

### Deduplication
Events are matched by canonical fingerprint: `normalize_title + date + venue`. Same show on multiple sources appears once.

### Filtering
- Non-music events are filtered out (workshops, sports, marathons, etc.)
- Events before 2024 are dropped
- Year errors (e.g., 2126) are auto-corrected

### Cache Busting
The frontend appends `?v=YYYY-MM-DD` to JSON fetch URLs, so users get fresh data daily without hard reloads.

## License

Personal project — no license declared.
