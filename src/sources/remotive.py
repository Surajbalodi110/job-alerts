"""Remotive free API — no key required."""
from typing import List
from ..models import Job

API_URL = "https://remotive.com/api/remote-jobs"

class RemotiveSource:
    name = "remotive"

    async def fetch(self, client) -> List[Job]:
        r = await client.get(API_URL, timeout=30)
        r.raise_for_status()
        data = r.json().get("jobs", [])
        jobs = []
        for j in data:
            jobs.append(Job(
                id=f"remotive:{j.get('id')}",
                source="remotive",
                title=j.get("title", ""),
                company=j.get("company_name", ""),
                url=j.get("url", ""),
                location=j.get("candidate_required_location", ""),
                remote=True,
                created_at=str(j.get("publication_date", "")),
                description_snippet=(j.get("description", "") or "")[:300],
            ))
        return jobs
