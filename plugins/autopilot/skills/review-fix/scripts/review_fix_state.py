#!/usr/bin/env python3
"""
review-fix의 진행 상태(iteration, pushed_at, env cache 등)를 관리한다.
Usage:
  python3 review_fix_state.py load {worktree_path} {issue_key}
  python3 review_fix_state.py save {worktree_path} {issue_key} --iteration {n} --pushed-at {iso} --env-cache {json}
"""
import argparse, json, os, sys
from datetime import datetime

def get_state_path(worktree_path, issue_key):
    # .gemini/autopilot/states/{issue_key}/review-fix-state.json
    state_dir = os.path.join(worktree_path, ".gemini", "autopilot", "states", issue_key)
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, "review-fix-state.json")

def load_state(worktree_path, issue_key):
    path = get_state_path(worktree_path, issue_key)
    if not os.path.exists(path):
        return {
            "iteration_count": 1,
            "pushed_at": None,
            "env_cache": None,
            "max_iterations": 20
        }
    with open(path, "r") as f:
        return json.load(f)

def save_state(worktree_path, issue_key, data):
    path = get_state_path(worktree_path, issue_key)
    current = load_state(worktree_path, issue_key)
    current.update(data)
    with open(path, "w") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)
    return current

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    load_p = subparsers.add_parser("load")
    load_p.add_argument("worktree_path")
    load_p.add_argument("issue_key")

    save_p = subparsers.add_parser("save")
    save_p.add_argument("worktree_path")
    save_p.add_argument("issue_key")
    save_p.add_argument("--iteration", type=int)
    save_p.add_argument("--pushed-at")
    save_p.add_argument("--env-cache")

    args = parser.parse_args()

    if args.command == "load":
        state = load_state(args.worktree_path, args.issue_key)
        print(json.dumps(state, ensure_ascii=False))
    elif args.command == "save":
        data = {}
        if args.iteration is not None: data["iteration_count"] = args.iteration
        if args.pushed_at is not None: data["pushed_at"] = args.pushed_at
        if args.env_cache is not None: data["env_cache"] = json.loads(args.env_cache)
        state = save_state(args.worktree_path, args.issue_key, data)
        print(json.dumps(state, ensure_ascii=False))

if __name__ == "__main__":
    main()
