import argparse, asyncio, os
from dotenv import load_dotenv

async def run_once(args):
    from src.watcher import check_once
    n = await check_once(args.config, args.db, notify=not args.no_notify)
    print(f"sent {n} alerts")

def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--db", default="seen.db")
    ap.add_argument("--no-notify", action="store_true", help="print only, don't send telegram")
    ap.add_argument("--mode", choices=["once", "watch", "api"], default="once")
    args = ap.parse_args()

    if args.mode == "once":
        asyncio.run(run_once(args))
    elif args.mode == "watch":
        from apscheduler.schedulers.blocking import BlockingScheduler
        import asyncio as aio
        secs = int(os.getenv("POLL_SECONDS", "600"))
        print(f"watching every {secs}s ...")
        # run immediately then schedule
        aio.run(run_once(args))
        sched = BlockingScheduler()
        sched.add_job(lambda: aio.run(run_once(args)), "interval", seconds=secs)
        sched.start()
    else:
        import uvicorn
        uvicorn.run("src.api:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

if __name__ == "__main__":
    main()
