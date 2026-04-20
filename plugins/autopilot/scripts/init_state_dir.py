#!/usr/bin/env python3
"""
상태 디렉토리 초기화 및 스킬 마커 삭제.
Usage: python3 init_state_dir.py --clear skill1 skill2 ...
Exit 0: ok {"main_root": "...", "state_dir": "..."}
"""
import json, os, subprocess, sys
from pathlib import Path

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def find_main_root():
    out, _, rc = run("git worktree list --porcelain")
    if rc == 0:
        lines = out.splitlines()
        for line in lines:
            if line.startswith("worktree "):
                return line[9:].strip()
    out, _, rc = run("git rev-parse --show-toplevel")
    return out if rc == 0 else None

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", nargs="*", help="삭제할 스킬 마커 목록")
    args = parser.parse_args()

    root = find_main_root()
    if not root:
        print(json.dumps({"status": "error", "reason": "GIT_ROOT_NOT_FOUND"}))
        sys.exit(1)

    state_dir = Path(root) / "tasks" / ".state"
    state_dir.mkdir(parents=True, exist_ok=True)

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
            "main_root": str(root),
            "state_dir": str(state_dir),
            "cleared": cleared
        }
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
