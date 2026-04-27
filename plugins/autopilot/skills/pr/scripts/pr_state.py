#!/usr/bin/env python3
"""
PR 생성 진행 상태를 관리한다.
Usage:
  python3 pr_state.py write --issue <ISSUE> --phase <PHASE> [--branch <BRANCH>] [--push-done <BOOL>]
  python3 pr_state.py read --issue <ISSUE>
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from state_paths import get_issue_state_dir

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["write", "read"])
    parser.add_argument("--issue", required=True)
    parser.add_argument("--phase")
    parser.add_argument("--branch")
    parser.add_argument("--push-done", choices=["true", "false"])
    args = parser.parse_args()

    state_dir = get_issue_state_dir(args.issue)
    state_file = state_dir / "pr_state.json"

    if args.cmd == "write":
        state = {}
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    state = json.load(f)
            except:
                pass
        
        if args.phase: state["phase"] = args.phase
        if args.branch: state["branch"] = args.branch
        if args.push_done: state["push_done"] = (args.push_done == "true")
        state["updated_at"] = datetime.now().isoformat()
        if "started_at" not in state:
            state["started_at"] = state["updated_at"]

        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        print(f"PR state updated: {args.phase}")

    elif args.cmd == "read":
        if not state_file.exists():
            print(json.dumps({"status": "none"}))
            return
        
        with open(state_file, "r") as f:
            state = json.load(f)
            state["status"] = "ok"
            print(json.dumps(state, indent=2))

if __name__ == "__main__":
    main()
