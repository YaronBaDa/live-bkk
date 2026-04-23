# Live / BKK

A single-file static directory of upcoming live music and festivals in Bangkok.

The whole site is one self-contained `index.html` — no build step, no external data files. Open it in a browser locally, or host it via GitHub Pages (see below).

## Layout

- `index.html` — the entire site: HTML, CSS, JS, and the embedded `CONCERTS`, `VENUES`, and `ARTISTS` arrays.
- `.github/workflows/pages.yml` — GitHub Actions workflow that publishes the site to GitHub Pages on every push to `main`.

## How the listings get refreshed

Listings are refreshed by a Cowork scheduled task (`livebkk-scrape`, defined in `SKILL.md` outside this repo) that runs three times a day. Each run:

1. Reads the existing `CONCERTS = [ ... ];` array out of `index.html`.
2. Pulls events from a tiered set of sources (Ticketmelon, Eventpop, Megatix, venue pages, promoter pages, editorial sites).
3. Merges new events in, updates mutable fields on existing ones, flips past events to `status: "past"`, and caps the array at 200.
4. Writes the file back, preserving CSS / VENUES / ARTISTS / filter JS.
5. Commits the change locally. **Push is manual** — run `git push` to publish.

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
