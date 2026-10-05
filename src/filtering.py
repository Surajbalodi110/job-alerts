from typing import List, Union
from .models import Job

def matches(job: Job, keywords: List[str], location: Union[str, List[str]], remote_only: bool, exclude: List[str], company: str = "") -> bool:
    hay = f"{job.title} {job.company} {job.description_snippet}".lower()
    loc_field = (job.location or "").lower()
    if company and company.lower() not in (job.company or "").lower():
        return False
    if exclude and any(e.lower() in hay for e in exclude if e):
        return False
    if remote_only and not job.remote:
        # also accept location mentioning remote
        if "remote" not in loc_field and "remote" not in hay:
            return False
    if location:
        locs = location if isinstance(location, list) else [location]
        locs = [str(x).lower() for x in locs if str(x).strip()]
        # strict: must match job.location field only, not company/description
        # prevents "Providence India" matching "India" or Hyderabad matching via description
        if locs and not any(L in loc_field for L in locs):
            return False
    if not keywords:
        return True
    return any(k.lower() in hay for k in keywords if k)
