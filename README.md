# Job Alerts (free, open-source)

Polls free jobs APIs and sends Telegram alerts for new matches. No paid keys.

Sources in v1 (all free, no key): Arbeitnow, Remotive, RemoteOK.
LinkedIn has no official Jobs Search API and blocks scraping — add it later via a paid proxy
(Apify / JSearch / Adzuna) by implementing `fetch()` in `src/sources/`.

## Setup (Windows)

1. Install Python 3.12 from python.org (check "Add to PATH").
2. Open terminal in this folder:
```
pip install -r requirements.txt
copy .env.example .env
copy config.example.yaml config.yaml
```
3. Edit `.env` with your `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.
4. Edit `config.yaml` queries (Technical Support etc.).

## Run

```powershell
# test once, print only
python main.py --mode once --no-notify

# send to Telegram once
python main.py --mode once

# continuous watch (every POLL_SECONDS, default 600)
python main.py --mode watch

# manual GET trigger API
python main.py --mode api
# then: http://localhost:8000/search?q=technical%20support&location=india
# health: http://localhost:8000/health
```

Dedup is stored in `seen.db` — only new job IDs alert.

## Free 24/7 hosting options

- **GitHub Actions (easiest, free):** push repo, add `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
  as repo Secrets, workflow `.github/workflows/poll.yml` runs every 15 min.
- **Render / Fly.io free tier:** deploy with `Dockerfile`, set env vars, `python main.py --mode watch`.
- **Local:** keep PC on with `--mode watch`.

## Add LinkedIn later

Create `src/sources/linkedin.py` with `class LinkedinSource: async def fetch(self, client)`,
parse your provider, return `Job(...)` list, and add to `sources = [...]` in
`src/watcher.py` and `src/api.py`.
