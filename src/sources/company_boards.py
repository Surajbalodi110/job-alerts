"""Direct company career pages — no keys, unlimited free, direct Apply links.
Greenhouse: https://boards-api.greenhouse.io/v1/boards/{board}/jobs
Lever: https://api.lever.co/v0/postings/{company}?mode=json
Override lists via env: GREENHOUSE_BOARDS, LEVER_COMPANIES (comma separated).
Unknown boards 404 and are skipped gracefully."""
import os
from typing import List
from ..models import Job

def _gh_boards() -> List[str]:
    raw = os.getenv("GREENHOUSE_BOARDS", "datadog,cloudflare")
    return [b.strip() for b in raw.split(",") if b.strip()]

def _lever_cos() -> List[str]:
    raw = os.getenv("LEVER_COMPANIES", "lever,paytm")
    return [c.strip() for c in raw.split(",") if c.strip()]

class GreenhouseSource:
    name = "greenhouse"

    async def fetch(self, client) -> List[Job]:
        jobs: List[Job] = []
        for board in _gh_boards():
            try:
                r = await client.get(
                    f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs",
                    timeout=30,
                )
                if r.status_code == 404:
                    print(f"[warn] greenhouse board '{board}' not found, skipped")
                    continue
                r.raise_for_status()
                for j in r.json().get("jobs", []):
                    loc = (j.get("location") or {}).get("name", "") if isinstance(j.get("location"), dict) else str(j.get("location", ""))
                    jobs.append(Job(
                        id=f"greenhouse:{board}:{j.get('id')}",
                        source="greenhouse",
                        title=j.get("title", ""),
                        company=board,
                        url=j.get("absolute_url", ""),
                        location=loc or "",
                        remote="remote" in loc.lower(),
                        created_at=str(j.get("updated_at", "")),
                        description_snippet="",
                    ))
            except Exception as e:
                print(f"[warn] greenhouse '{board}' failed: {e}")
        return jobs

class LeverSource:
    name = "lever"

    async def fetch(self, client) -> List[Job]:
        jobs: List[Job] = []
        for co in _lever_cos():
            try:
                r = await client.get(
                    f"https://api.lever.co/v0/postings/{co}?mode=json",
                    timeout=30,
                )
                if r.status_code == 404:
                    print(f"[warn] lever company '{co}' not found, skipped")
                    continue
                r.raise_for_status()
                data = r.json()
                items = data if isinstance(data, list) else data.get("data", [])
                for j in items:
                    cats = j.get("categories") or {}
                    loc = cats.get("location", "") or ""
                    jobs.append(Job(
                        id=f"lever:{co}:{j.get('id')}",
                        source="lever",
                        title=j.get("text", ""),
                        company=co,
                        url=j.get("hostedUrl", ""),
                        location=loc,
                        remote="remote" in loc.lower(),
                        created_at=str(j.get("createdAt", "")),
                        description_snippet=(j.get("descriptionPlain", "") or "")[:300],
                    ))
            except Exception as e:
                print(f"[warn] lever '{co}' failed: {e}")
        return jobs
