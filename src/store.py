import sqlite3
from pathlib import Path

SCHEMA = "CREATE TABLE IF NOT EXISTS seen_jobs (job_id TEXT PRIMARY KEY, first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"

class SeenStore:
    def __init__(self, path: str = "seen.db"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def is_new(self, job_id: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM seen_jobs WHERE job_id=?", (job_id,))
        return cur.fetchone() is None

    def mark_seen(self, job_id: str):
        self.conn.execute("INSERT OR IGNORE INTO seen_jobs (job_id) VALUES (?)", (job_id,))
        self.conn.commit()

    def filter_new(self, ids: list[str]) -> list[str]:
        return [i for i in ids if self.is_new(i)]
