#!/usr/bin/env python3
"""
상태 디렉토리 초기화 및 스킬 마커 삭제.
Usage: python3 init_state_dir.py --issue <ISSUE> --clear skill1 skill2 ...
Exit 0: ok {"main_root": "...", "state_dir": "..."}
"""
import json
import sys
import argparse
from state_paths import find_main_root, resolve_issue, get_issue_state_dir

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", help="issue key")
    parser.add_argument("--clear", nargs="*", help="삭제할 스킬 마커 목록")
    args = parser.parse_args()

    root = find_main_root()
    if not root:
        print(json.dumps({"status": "error", "reason": "GIT_ROOT_NOT_FOUND"}))
        sys.exit(1)

    issue = resolve_issue(sys.argv)
    state_dir = get_issue_state_dir(issue)

    cleared = []
    if args.clear:
        for skill in args.clear:
            marker = state_dir / skill
            if marker.exists():
                marker.unlink()
                cleared.append(skill)
            # phase markers (e.g. build.setup)
            for p in state_dir.glob(f"{skill}.*"):
                p.unlink()

    print(json.dumps({
        "status": "ok",
        "data": {
            "issue": issue,
            "main_root": str(root),
            "state_dir": str(state_dir),
            "cleared": cleared
        }
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
