import asyncio
import httpx

async def main():
    async with httpx.AsyncClient(headers={"User-Agent": "job-alerts/1.0"}, follow_redirects=True) as c:
        r = await c.get("https://api.lever.co/v0/postings/paytm?mode=json", timeout=30)
        print("status:", r.status_code)
        data = r.json()
        items = data if isinstance(data, list) else []
        print("count:", len(items))
        for j in items[:5]:
            cats = j.get("categories") or {}
            print("-", j.get("text", "")[:60], "|", cats.get("location", ""), "|", j.get("hostedUrl", "")[:80])

asyncio.run(main())
