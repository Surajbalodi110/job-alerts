"""Adzuna free-tier API — signup at developer.adzuna.com for free app_id/app_key.
Covers India onsite jobs (aggregates many boards). Skips gracefully if keys missing."""
import os
from typing import List
from ..models import Job

COUNTRY = os.getenv("ADZUNA_COUNTRY", "in")

# NCR-focused seeds — fetch Delhi/Noida/Gurgaon directly so strict filter has hits
SEEDS = [
    ("IT support", "Delhi"),
    ("help desk", "Noida"),
    ("technical support", "Gurgaon"),
    ("security analyst", "Delhi"),
    ("SOC analyst", "India"),
]

class AdzunaSource:
    name = "adzuna"

    async def fetch(self, client) -> List[Job]:
        app_id = os.getenv("ADZUNA_APP_ID", "")
        app_key = os.getenv("ADZUNA_APP_KEY", "")
        if not app_id or not app_key:
            return []
        jobs: List[Job] = []
        for what, where in SEEDS:
            url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search/1"
            try:
                r = await client.get(url, params={
                    "app_id": app_id, "app_key": app_key,
                    "results_per_page": 20, "what": what, "where": where,
                    "sort_by": "date",
                }, timeout=30)
                r.raise_for_status()
                for j in r.json().get("results", []):
                    jid = j.get("id", "")
                    loc = (j.get("location") or {}).get("display_name", "")
                    jobs.append(Job(
                        id=f"adzuna:{jid}",
                        source="adzuna",
                        title=j.get("title", ""),
                        company=(j.get("company") or {}).get("display_name", ""),
                        url=j.get("redirect_url", ""),
                        location=loc,
                        remote="remote" in loc.lower() or "remote" in (j.get("title","").lower()),
                        created_at=str(j.get("created", "")),
                        description_snippet=(j.get("description", "") or "")[:300],
                    ))
            except Exception as e:
                print(f"[warn] adzuna '{what}' failed: {e}")
        return jobs
