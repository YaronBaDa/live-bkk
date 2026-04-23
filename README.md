# Live / BKK

A single-file static directory of upcoming live music and festivals in Bangkok.

The whole site is one self-contained `index.html` — no build step, no external data files. Open it in a browser locally, or host it via GitHub Pages (see below).

## Layout

- `index.html` — the entire site: HTML, CSS, JS, and the embedded `CONCERTS`, `VENUES`, and `ARTISTS` arrays.
- `.github/workflows/pages.yml` — GitHub Actions workflow that publishes the site to GitHub Pages on every push to `main`.

## Refreshing listings

The scraper + merger pipeline lives in the Cowork outputs folder (not in this repo). To run it manually:

```bash
python3 update.py            # scrape every source in parallel + merge into index.html
python3 update.py --dry-run  # scrape + merge but don't overwrite the file
python3 update.py --no-fetch # skip scrapers, just re-merge cached *_events.json
```

Each run:

1. Pulls events from Ticketmelon (`api-frontend.ticketmelon.com/v1/buyer/home-page/events`), Thai Ticket Major (HTML listing), and Live Nation Tero (homepage + per-event og: meta).
2. Merges into `CONCERTS` — preserving `added` dates and curated entries, flipping past events to `status: "past"`, deduping by `id` and by normalised title+date across sources.
3. Writes the file back, touching nothing outside the `CONCERTS` array.
4. Commits locally. **Push is manual** — run `git push` (or use GitHub Desktop) to publish.

## Hosting on GitHub Pages

The repo is **public** so Pages hosting is free.

1. **Settings → Pages → Source:** choose "GitHub Actions".
2. The included `.github/workflows/pages.yml` workflow does the rest — it deploys `index.html` (and any other static files) to Pages on every push to `main`.
3. Your site URL will be `https://<your-username>.github.io/live-bkk/`.

If you'd rather skip the workflow, you can also pick **Deploy from a branch → `main` → `/ (root)`** in the Pages settings.

## Local preview

```bash
cd ~/Documents/LiveBKK
python3 -m http.server 8080
# then open http://localhost:8080
```

## License

Personal project — no license declared.
