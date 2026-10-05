"""SerpAPI Google Jobs — covers Naukri/Indeed/LinkedIn listings via Google.
Free 100 searches/mo (serpapi.com). NOT for 10-min auto-poll (would exhaust quota
in hours). Included in manual UI /search; watcher only uses it if SERPAPI_AUTO=1.
Set SERPAPI_KEY to enable, else skips gracefully."""
import os
from typing import List
from ..models import Job

SEEDS = [
    ("IT support jobs Delhi NCR", "Delhi, India"),
    ("help desk jobs Noida", "Noida, Uttar Pradesh, India"),
    ("SOC analyst jobs Gurgaon", "Gurgaon, Haryana, India"),
]

class SerpAPIJobsSource:
    name = "serpapi"

    async def fetch(self, client) -> List[Job]:
        key = os.getenv("SERPAPI_KEY", "")
        if not key:
            return []
        jobs: List[Job] = []
        for q, loc in SEEDS:
            try:
                r = await client.get("https://serpapi.com/search.json", params={
                    "engine": "google_jobs", "q": q, "location": loc,
                    "hl": "en", "gl": "in", "api_key": key,
                }, timeout=30)
                r.raise_for_status()
                for j in r.json().get("jobs_results", []):
                    jid = j.get("job_id", "") or j.get("title", "")
                    apply = ""
                    for opt in j.get("apply_options", []) or []:
                        if opt.get("link"):
                            apply = opt["link"]
                            break
                    jobs.append(Job(
                        id=f"serpapi:{jid}",
                        source="serpapi",
                        title=j.get("title", ""),
                        company=j.get("company_name", ""),
                        url=apply,
                        location=j.get("location", ""),
                        remote="remote" in (j.get("location", "") or "").lower(),
                        created_at=str((j.get("detected_extensions") or {}).get("posted_at", "")),
                        description_snippet=(j.get("description", "") or "")[:300],
                    ))
            except Exception as e:
                print(f"[warn] serpapi '{q}' failed: {e}")
        return jobs
