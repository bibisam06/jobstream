from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .sources.common.base import CrawlRequest
from .sources.saramin.crawler import SaraminCrawler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect job postings with Playwright.")
    parser.add_argument("--source", choices=["saramin"], default="saramin")
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--headful", action="store_true", help="Run browser with UI for debugging.")
    parser.add_argument("--output", type=Path, help="Write collected postings as JSON Lines.")
    return parser


async def run(args: argparse.Namespace) -> int:
    crawler = SaraminCrawler()
    request = CrawlRequest(keyword=args.keyword, pages=args.pages, headless=not args.headful)
    postings = await crawler.crawl(request)

    lines = [json.dumps(posting.to_dict(), ensure_ascii=False) for posting in postings]
    payload = "\n".join(lines)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + ("\n" if payload else ""), encoding="utf-8")
    else:
        print(payload)

    print(f"collected={len(postings)}", file=sys.stderr)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run(build_parser().parse_args())))


if __name__ == "__main__":
    main()
