"""RemoteOK free API — no key, requires User-Agent."""
from typing import List
from ..models import Job

API_URL = "https://remoteok.com/api"

class RemoteOKSource:
    name = "remoteok"

    async def fetch(self, client) -> List[Job]:
        r = await client.get(API_URL, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            data = []
        jobs = []
        for j in data[1:]:  # first item is legal notice
            if not isinstance(j, dict) or "id" not in j:
                continue
            jobs.append(Job(
                id=f"remoteok:{j.get('id')}",
                source="remoteok",
                title=j.get("position", ""),
                company=j.get("company", ""),
                url=j.get("url", ""),
                location=" / ".join(j.get("location", []) if isinstance(j.get("location"), list) else [str(j.get("location", ""))]),
                remote=True,
                created_at=str(j.get("date", "")),
                description_snippet=(j.get("description", "") or "")[:300],
            ))
        return jobs
