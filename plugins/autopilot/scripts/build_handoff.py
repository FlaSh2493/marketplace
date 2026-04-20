#!/usr/bin/env python3
"""
build-handoff.json 파일을 관리하여 세션/에이전트 간 구현 상태를 공유한다.
"""
import json, os, sys, shutil
from datetime import datetime
from pathlib import Path

def get_handoff_path(issue_doc_root=None):
    if not issue_doc_root:
        # 현재 위치 또는 상위에서 .git을 찾아 root 확보
        curr = Path.cwd()
        root = None
        for p in [curr] + list(curr.parents):
            if (p / ".git").exists():
                root = p
                break
        if not root:
             print("error: git root를 찾을 수 없습니다.", file=sys.stderr)
             sys.exit(1)
        issue_doc_root = root
        
    d = Path(issue_doc_root) / "tasks" / ".state"
    d.mkdir(parents=True, exist_ok=True)
    return d / "build-handoff.json"

def load_handoff(path):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except:
            return None
    return None

def save_handoff(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def main():
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    
    # init
    p_init = subparsers.add_parser("init")
    p_init.add_argument("--branch", required=True)
    p_init.add_argument("--worktree", required=True)
    p_init.add_argument("--issues", nargs="+", required=True)
    
    # append-entry
    p_append = subparsers.add_parser("append-entry")
    p_append.add_argument("--actor", required=True)
    p_append.add_argument("--chunk-idx", type=int, default=0)
    p_append.add_argument("--steps-json", required=True) # JSON string of [{issue, idx, text}]
    p_append.add_argument("--summary", required=True)
    
    # mark-phase-done
    p_phase = subparsers.add_parser("mark-phase-done")
    p_phase.add_argument("--name", required=True)
    
    # show
    subparsers.add_parser("show")
    
    # completed-step-ids
    subparsers.add_parser("completed-step-ids")
    
    # clear
    subparsers.add_parser("clear")
    
    args = parser.parse_args()
    
    path = get_handoff_path()
    
    if args.command == "init":
        # 이미 있으면 유지, 없으면 생성
        data = load_handoff(path)
        if not data:
            data = {
                "branch": args.branch,
                "worktree_path": args.worktree,
                "issues": args.issues,
                "started_at": datetime.now().isoformat(),
                "entries": [],
                "phases_done": []
            }
            save_handoff(path, data)
            print(f"Handoff initialized: {path}")
        else:
            print(f"Handoff already exists: {path}")

    elif args.command == "append-entry":
        data = load_handoff(path)
        if not data:
            print("error: handoff file not found. run init first.", file=sys.stderr)
            sys.exit(1)
            
        entry = {
            "ts": datetime.now().isoformat(),
            "actor": args.actor,
            "chunk_idx": args.chunk_idx,
            "completed_steps": json.loads(args.steps_json),
            "summary": args.summary
        }
        data["entries"].append(entry)
        save_handoff(path, data)
        print("Entry appended.")

    elif args.command == "mark-phase-done":
        data = load_handoff(path)
        if data:
            if args.name not in data["phases_done"]:
                data["phases_done"].append(args.name)
                save_handoff(path, data)
            print(f"Phase {args.name} marked as done.")

    elif args.command == "show":
        data = load_handoff(path)
        if data:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"status": "empty"}, ensure_ascii=False))

    elif args.command == "completed-step-ids":
        data = load_handoff(path)
        completed = []
        if data:
            for entry in data["entries"]:
                for step in entry.get("completed_steps", []):
                    completed.append({"issue": step["issue"], "idx": step["idx"]})
        print(json.dumps(completed, ensure_ascii=False))

    elif args.command == "clear":
        if path.exists():
            archive_dir = path.parent / "archive"
            archive_dir.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = archive_dir / f"build-handoff-{ts}.json"
            shutil.move(str(path), str(archive_path))
            print(f"Handoff archived to {archive_path}")
        else:
            print("Handoff file not found.")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
