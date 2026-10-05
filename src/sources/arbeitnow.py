"""Arbeitnow free API — no key required. Docs: arbeitnow.com/api/job-board-api"""
from typing import List
from ..models import Job

API_URL = "https://www.arbeitnow.com/api/job-board-api"

class ArbeitnowSource:
    name = "arbeitnow"

    async def fetch(self, client) -> List[Job]:
        r = await client.get(API_URL, timeout=30)
        r.raise_for_status()
        data = r.json().get("data", [])
        jobs = []
        for j in data:
            slug = j.get("slug", "")
            url = j.get("url", "")
            jobs.append(Job(
                id=f"arbeitnow:{slug or url}",
                source="arbeitnow",
                title=j.get("title", ""),
                company=j.get("company_name", ""),
                url=url,
                location=j.get("location", ""),
                remote="remote" in (j.get("job_types", []) or [s.lower() for s in [j.get("location","")]]) or "remote" in j.get("location", "").lower(),
                created_at=str(j.get("created_at", "")),
                description_snippet="",
            ))
        return jobs
