from typing import Protocol, List
from .models import Job

class JobSource(Protocol):
    name: str
    async def fetch(self, client) -> List[Job]: ...
