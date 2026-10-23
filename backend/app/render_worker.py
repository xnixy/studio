from __future__ import annotations

import argparse
import asyncio

from app.config import get_settings
from app.database import SessionLocal
from app.render_pipeline import next_queued_render, process_render_pipeline


async def process_once() -> bool:
    settings = get_settings()
    async with SessionLocal() as session:
        render = await next_queued_render(session)
        if render is None:
            print("No queued renders.")
            return False
        print(f"Processing render {render.id}...")
        try:
            await process_render_pipeline(render=render, session=session, settings=settings, actor_id=None)
        except Exception as exc:
            await session.rollback()
            print(f"Render {render.id} failed: {exc}")
            return True
        print(f"Render {render.id} complete: {render.output_url}")
        return True


async def run(limit: int, poll_seconds: float) -> None:
    processed = 0
    while limit <= 0 or processed < limit:
        did_work = await process_once()
        if did_work:
            processed += 1
            if limit == 1:
                break
            continue
        if poll_seconds <= 0:
            break
        await asyncio.sleep(poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process queued Studio video renders.")
    parser.add_argument("--once", action="store_true", help="Process at most one queued render.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum renders to process; 0 means run until idle unless polling.")
    parser.add_argument("--poll-seconds", type=float, default=0, help="Poll interval when no render is queued; 0 exits when idle.")
    args = parser.parse_args()
    limit = 1 if args.once else args.limit
    asyncio.run(run(limit=limit, poll_seconds=args.poll_seconds))


if __name__ == "__main__":
    main()
