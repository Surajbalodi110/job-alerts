from dataclasses import dataclass

@dataclass
class Job:
    id: str          # stable unique id, e.g. "arbeitnow:12345"
    source: str
    title: str
    company: str
    url: str
    location: str = ""
    remote: bool = False
    created_at: str = ""
    description_snippet: str = ""
