import asyncio
import os
import httpx
import yaml
from .store import SeenStore
from .notifier import TelegramNotifier, format_job
from .filtering import matches
from .sources.arbeitnow import ArbeitnowSource
from .sources.remotive import RemotiveSource
from .sources.remoteok import RemoteOKSource
from .sources.adzuna import AdzunaSource
from .sources.jsearch import JSearchSource
from .sources.serpapi import SerpAPIJobsSource
from .sources.company_boards import GreenhouseSource, LeverSource

def load_config(path="config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

async def check_once(config_path="config.yaml", db_path="seen.db", notify=True, limit_per_query=None) -> int:
    cfg = load_config(config_path)
    queries = cfg.get("queries", [])
    max_per = limit_per_query or cfg.get("max_per_query_per_run", 5)
    store = SeenStore(db_path)

    headers = {"User-Agent": "job-alerts-opensource/1.0"}
    # SerpAPI excluded from auto-watch by default (100/mo free quota).
    # Set SERPAPI_AUTO=1 to include it (uses ~1-3 calls per poll).
    sources = [ArbeitnowSource(), RemotiveSource(), RemoteOKSource(), AdzunaSource(), JSearchSource(), GreenhouseSource(), LeverSource()]
    if os.getenv("SERPAPI_AUTO", "0") == "1":
        sources.append(SerpAPIJobsSource())
    sent = 0

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        # fetch all sources in parallel
        async def _one(s):
            try:
                return await s.fetch(client)
            except Exception as e:
                print(f"[warn] {s.name} failed: {e}")
                return []
        parts = await asyncio.gather(*[_one(s) for s in sources])
        all_jobs = [j for sub in parts for j in sub]

        notifier = TelegramNotifier(client)
        for q in queries:
            qname = q.get("name", "query")
            kws = q.get("keywords", [])
            loc = q.get("location", "") or ""
            company = q.get("company", "") or ""
            remote_only = bool(q.get("remote_only", False))
            excl = q.get("exclude_keywords", []) or []
            matched = [j for j in all_jobs if matches(j, kws, loc, remote_only, excl, company)]
            # newest first if date present, else as-is
            fresh = [j for j in matched if store.is_new(j.id)][:max_per]
            for job in fresh:
                store.mark_seen(job.id)
                if notify:
                    try:
                        await notifier.send(format_job(qname, job))
                        sent += 1
                    except Exception as e:
                        print(f"[warn] telegram send failed: {e}")
                else:
                    print(format_job(qname, job))
                    sent += 1
            # mark remaining matched as seen to avoid backlog spam on first run?
            # No — leave unseen beyond max_per so next run picks them up.
    return sent
