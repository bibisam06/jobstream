# store_to_db.pu

from __future__ import annotations

import argparse
import json

from processor.storage import get_connection, save_posting


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="crawler가 저장한 JSONL 파일 경로")
    args = parser.parse_args()

    conn = get_connection()
    total = 0
    all_unmatched: set[str] = set()

    with open(args.input, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            posting = json.loads(line)
            unmatched = save_posting(conn, posting)
            all_unmatched.update(unmatched)
            total += 1

    conn.close()
    print(f"저장 완료: {total}건")
    if all_unmatched:
        print(f"매칭 안 된 기술스택({len(all_unmatched)}개): {sorted(all_unmatched)}")


if __name__ == "__main__":
    main()