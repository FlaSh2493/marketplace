#!/usr/bin/env python3
"""
머지 진행 상태를 기록하고 조회한다.
Usage:
  python3 merge_state.py write --phase {phase} --case {1|2} --target {target} --branch {branch} [--issue {issue}]
  python3 merge_state.py read [--issue {issue}]
  python3 merge_state.py clear [--issue {issue}]
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

# state_paths 가 같은 디렉토리에 있다고 가정
sys.path.append(os.path.dirname(__file__))
try:
    import state_paths
except ImportError:
    state_paths = None

def get_state_file(issue=None):
    if state_paths and issue:
        state_dir = state_paths.get_issue_state_dir(issue)
        return state_dir / "merge_progress.json"
    
    # Fallback to a temp file if issue is not provided or state_paths is missing
    return Path("/tmp/autopilot_merge_state.json")

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

    state_file = get_state_file(args.issue)

    if args.cmd == "write":
        state = {
            "phase": args.phase,
            "case": args.case,
            "target": args.target,
            "branch": args.branch,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        # 기존 파일이 있으면 병합
        if state_file.exists():
            try:
                old_state = json.loads(state_file.read_text())
                if isinstance(old_state, dict):
                    old_state.update(state)
                    state = old_state
            except:
                pass
        
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        print(json.dumps({"status": "ok", "data": state}, ensure_ascii=False))

    elif args.cmd == "read":
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
                print(json.dumps({"status": "ok", "data": state}, ensure_ascii=False))
            except Exception as e:
                print(json.dumps({"status": "error", "reason": f"READ_FAILED: {str(e)}"}, ensure_ascii=False))
        else:
            print(json.dumps({"status": "not_found"}, ensure_ascii=False))

    elif args.cmd == "clear":
        if state_file.exists():
            state_file.unlink()
        print(json.dumps({"status": "ok"}, ensure_ascii=False))
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
