"""JSearch (RapidAPI) — aggregates LinkedIn / Indeed / Glassdoor.
Free tier ~500 req/mo. Set RAPIDAPI_KEY to enable, else skips gracefully.
Signup: rapidapi.comletsdefend JSearch."""
import os
from typing import List
from ..models import Job

SEEDS = [
    "IT support Delhi NCR India",
    "help desk Noida India",
    "SOC analyst India",
]

class JSearchSource:
    name = "jsearch"

    async def fetch(self, client) -> List[Job]:
        key = os.getenv("RAPIDAPI_KEY", "")
        if not key:
            return []
        jobs: List[Job] = []
        headers = {
            "X-RapidAPI-Key": key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }
        for q in SEEDS:
            try:
                r = await client.get(
                    "https://jsearch.p.rapidapi.com/search",
                    headers=headers,
                    params={"query": q, "page": "1", "num_pages": "1", "country": "in", "date_posted": "week"},
                    timeout=30,
                )
                r.raise_for_status()
                for j in r.json().get("data", []):
                    jid = j.get("job_id", "") or j.get("job_apply_link", "")
                    jobs.append(Job(
                        id=f"jsearch:{jid}",
                        source="jsearch",
                        title=j.get("job_title", ""),
                        company=j.get("employer_name", ""),
                        url=j.get("job_apply_link", "") or j.get("job_google_link", ""),
                        location=f"{j.get('job_city','')} {j.get('job_country','')}".strip(),
                        remote=bool(j.get("job_is_remote", False)),
                        created_at=str(j.get("job_posted_at_datetime_utc", "")),
                        description_snippet=(j.get("job_description", "") or "")[:300],
                    ))
            except Exception as e:
                print(f"[warn] jsearch '{q}' failed: {e}")
        return jobs
