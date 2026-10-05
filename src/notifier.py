import html
import os

class TelegramNotifier:
    def __init__(self, client=None):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.client = client

    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    async def send(self, text: str) -> bool:
        if not self.configured():
            print("[telegram] not configured, skipping:\n", text[:500])
            return False
        assert self.client is not None
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        r = await self.client.post(url, json={
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=30)
        r.raise_for_status()
        return True

def format_job(query_name: str, job) -> str:
    title = html.escape(job.title or "", quote=False)
    company = html.escape(job.company or "", quote=False)
    loc = html.escape(job.location or "", quote=False)
    source = html.escape(job.source or "", quote=False)
    q = html.escape(query_name or "", quote=False)
    loc_part = f" | {loc}" if loc else ""
    return (
        f"<b>[{q}] {title}</b>\n"
        f"{company}{loc_part}\n"
        f"Source: {source}\n"
        f"Apply: {job.url}"
    )
