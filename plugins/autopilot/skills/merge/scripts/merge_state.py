#!/usr/bin/env python3
"""
머지 진행 상태를 meta.json["merge"]에 기록하고 조회한다.
Usage:
  python3 merge_state.py write --phase {phase} --case {1|2} --target {target} --branch {branch} [--issue {issue}]
  python3 merge_state.py read [--issue {issue}]
  python3 merge_state.py clear [--issue {issue}]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
from state_paths import resolve_issue, read_meta, update_meta_key, clear_meta_keys


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd")

    write_p = subparsers.add_parser("write")
    write_p.add_argument("--phase", required=True)
    write_p.add_argument("--case", choices=["1", "2"], required=True)
    write_p.add_argument("--target", required=True)
    write_p.add_argument("--branch", required=True)
    write_p.add_argument("--issue")

    read_p = subparsers.add_parser("read")
    read_p.add_argument("--issue")

    clear_p = subparsers.add_parser("clear")
    clear_p.add_argument("--issue")

    args = parser.parse_args()

    issue = args.issue or resolve_issue(sys.argv)

    if args.cmd == "write":
        meta = read_meta(issue)
        existing = meta.get("merge", {})
        existing.update({
            "phase": args.phase,
            "case": args.case,
            "target": args.target,
            "branch": args.branch,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
        update_meta_key(issue, "merge", existing)
        print(json.dumps({"status": "ok", "data": existing}, ensure_ascii=False))

    elif args.cmd == "read":
        meta = read_meta(issue)
        state = meta.get("merge")
        if state:
            print(json.dumps({"status": "ok", "data": state}, ensure_ascii=False))
        else:
            print(json.dumps({"status": "not_found"}, ensure_ascii=False))

    elif args.cmd == "clear":
        clear_meta_keys(issue, ["merge"])
        print(json.dumps({"status": "ok"}, ensure_ascii=False))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
