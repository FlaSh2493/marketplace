#!/usr/bin/env python3
"""
상태 디렉토리 초기화 및 스킬 상태 삭제.
Usage: python3 init_state_dir.py --issue <ISSUE> --clear skill1 skill2 ...
Exit 0: ok {"main_root": "...", "issue_dir": "..."}

--clear 옵션: meta.json에서 해당 키를 삭제한다.
  예: --clear pr review-fix  → meta.json의 "pr", "review_fix" 키 삭제
"""
import json
import sys
import argparse
from state_paths import find_main_root, resolve_issue, get_issue_dir, clear_meta_keys

# 스킬 이름 → meta.json 키 매핑
SKILL_META_KEY = {
    "plan": "plan",
    "build": "build",
    "check": "check",
    "merge": "merge",
    "pr": "pr",
    "review-fix": "review_fix",
    "review_fix": "review_fix",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", help="issue key")
    parser.add_argument("--clear", nargs="*", help="삭제할 스킬 상태 목록")
    args = parser.parse_args()

    root = find_main_root()
    if not root:
        print(json.dumps({"status": "error", "reason": "GIT_ROOT_NOT_FOUND"}))
        sys.exit(1)

    issue = resolve_issue(sys.argv)
    issue_dir = get_issue_dir(issue)

    cleared = []
    if args.clear:
        meta_keys = [SKILL_META_KEY.get(s, s) for s in args.clear]
        clear_meta_keys(issue, meta_keys)
        cleared = args.clear

    print(json.dumps({
        "status": "ok",
        "data": {
            "issue": issue,
            "main_root": str(root),
            "issue_dir": str(issue_dir),
            "cleared": cleared
        }
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
