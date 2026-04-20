#!/usr/bin/env python3
"""
autopilot 스킬 상태 마커를 관리한다.
Usage:
  python3 state_manager.py reset <skill> --issue <ISSUE>
  python3 state_manager.py mark  <skill> --issue <ISSUE>
  python3 state_manager.py check <skill> --issue <ISSUE>
Exit 0: ok  Exit 1: error or check-miss
"""
import sys
import argparse
from state_paths import resolve_issue, get_issue_state_dir

LIFECYCLE = [
    "plan",
    "build",
    "check",
    "check-all",
    "merge",
    "merge-all",
    "pr",
    "review-fix",
]

def skills_from(skill):
    """skill 이후(포함) 스킬 목록 반환."""
    try:
        idx = LIFECYCLE.index(skill)
        return LIFECYCLE[idx:]
    except ValueError:
        return []

def main():
    parser = argparse.ArgumentParser(description="autopilot skill state manager")
    parser.add_argument("cmd", choices=["reset", "mark", "check"], help="command to execute")
    parser.add_argument("skill", help="skill name")
    parser.add_argument("--issue", help="issue key")
    parser.add_argument("--phase", help="phase name (optional)")
    
    args = parser.parse_args()
    
    # 세션 마커 등 특수한 경우는 state_paths를 타지 않을 수도 있으나,
    # 여기서는 스킬 마커만 다루므로 항상 resolve_issue를 수행한다.
    issue = resolve_issue(sys.argv)
    d = get_issue_state_dir(issue)

    if args.cmd == "reset":
        to_reset = skills_from(args.skill)
        for s in to_reset:
            # 기본 스킬 마커 삭제
            marker = d / s
            if marker.exists():
                marker.unlink()
            # 해당 스킬의 모든 phase 마커 삭제 (build.setup 등)
            for p in d.glob(f"{s}.*"):
                p.unlink()
        print(f"[{issue}] reset: {', '.join(to_reset)}")

    elif args.cmd == "mark":
        name = f"{args.skill}.{args.phase}" if args.phase else args.skill
        marker = d / name
        marker.touch()
        print(f"[{issue}] marked: {marker}")

    elif args.cmd == "check":
        name = f"{args.skill}.{args.phase}" if args.phase else args.skill
        marker = d / name
        if marker.exists():
            print(f"[{issue}] ok: {marker}")
            sys.exit(0)
        else:
            print(f"[{issue}] missing: {marker}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
