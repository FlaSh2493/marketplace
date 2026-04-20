#!/usr/bin/env python3
"""
autopilot 스킬 상태 마커를 관리한다.
Usage:
  python3 state_manager.py reset <skill>   # 해당 스킬 이후 마커 모두 삭제
  python3 state_manager.py mark  <skill>   # 완료 마커 기록
  python3 state_manager.py check <skill>   # 존재 시 exit 0, 없으면 exit 1
Exit 0: ok  Exit 1: error or check-miss
"""
import os, subprocess, sys
from pathlib import Path


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


def find_main_root():
    """어느 워크트리에서 실행해도 메인 워크트리 루트를 반환한다."""
    r = subprocess.run(
        "git worktree list --porcelain",
        shell=True, capture_output=True, text=True,
    )
    for line in r.stdout.splitlines():
        if line.startswith("worktree "):
            return line[9:].strip()
    # fallback
    r2 = subprocess.run(
        "git rev-parse --show-toplevel",
        shell=True, capture_output=True, text=True,
    )
    return r2.stdout.strip() if r2.returncode == 0 else None


def state_dir():
    root = find_main_root()
    if not root:
        print("error: git 루트를 찾을 수 없습니다", file=sys.stderr)
        sys.exit(1)
    d = Path(root) / "tasks" / ".state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def skills_from(skill):
    """skill 이후(포함) 스킬 목록 반환. 알 수 없는 스킬이면 전체 반환."""
    try:
        idx = LIFECYCLE.index(skill)
        return LIFECYCLE[idx:]
    except ValueError:
        return LIFECYCLE


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print("usage: state_manager.py <reset|mark|check> <skill>", file=sys.stderr)
        sys.exit(1)

    cmd, skill = args[0], args[1]
    d = state_dir()

    if cmd == "reset":
        for s in skills_from(skill):
            marker = d / s
            if marker.exists():
                marker.unlink()
        print(f"reset: {', '.join(skills_from(skill))}")

    elif cmd == "mark":
        marker = d / skill
        marker.touch()
        print(f"marked: {marker}")

    elif cmd == "check":
        marker = d / skill
        if marker.exists():
            print(f"ok: {marker}")
            sys.exit(0)
        else:
            print(f"missing: {marker}", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
