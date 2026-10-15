# Casino bonus scraper

Scrapes welcome-bonus data for 3 casinos from their own promotions pages, uses an LLM (Anthropic API)
to turn free-text terms into structured fields, writes `bonuses.json`, and `index.html` renders it as a table.

## Install & run
```
cd path\to\casino-bonus-scraper
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set ANTHROPIC_API_KEY=
python scrape.py        # writes bonuses.json
python -m http.server   # view index.html at http://localhost:8000
```
Edit `SOURCES` in `scrape.py` to change casinos. The script checks robots.txt first, never bypasses
logins/CAPTCHAs/blocks (a block is logged as a failure), and exits non-zero if any casino fails.

## Deploy
Push to GitHub, enable Pages (Settings > Pages > main branch / root).

- The LLM extraction step could not be completed: the Anthropic API returned "credit balance too low" on my account, so bonuses.json contains no extracted values. The scraper, robots.txt check, web page and written part are complete.

## Known gaps
- Only 3 casinos are scraped, all from one source (casino.org South Africa bonus pages).
- Some pages list several offers or wagering figures (for example casino vs sports). The model picks one, so I checked each value in bonuses.json by hand against the page.
- Only plain HTML pages are supported. Pages that need JavaScript to render would return little text.
- The scraper runs on demand only. There are no retries, scheduling or automated tests. The production plan for those is in WRITTEN_PART.md.
- Extraction depends on casino.org's current page wording and layout, so a redesign could break it.
