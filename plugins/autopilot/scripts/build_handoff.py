#!/usr/bin/env python3
"""
build-handoff.json 파일을 관리하여 세션/에이전트 간 구현 상태를 공유한다.
"""
import json, os, sys, shutil, hashlib
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

def calculate_fingerprint(branch, worktree_path, issues):
    sorted_issues = sorted(issues)
    data = f"{branch}:{worktree_path}:{','.join(sorted_issues)}"
    return hashlib.sha256(data.encode()).hexdigest()

def load_handoff(path):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except:
            return None
    return None

def save_handoff(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def append_step_logic(data, issue, phase_idx, step_idx, text, actor):
    step_id = f"{issue}:{phase_idx}:{step_idx}"
    
    # 중복 체크
    for entry in data.get("entries", []):
        if entry.get("type") == "step" and entry.get("step_id") == step_id:
            return False # 이미 존재
            
    entry = {
        "ts": datetime.now().isoformat(),
        "type": "step",
        "actor": actor,
        "step_id": step_id,
        "issue": issue,
        "phase_idx": phase_idx,
        "step_idx": step_idx,
        "text": text
    }
    data["entries"].append(entry)
    data["last_step_id"] = {
        "issue": issue,
        "phase_idx": phase_idx,
        "step_idx": step_idx,
        "text": text
    }
    return True

def main():
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    
    # init
    p_init = subparsers.add_parser("init")
    p_init.add_argument("--branch", required=True)
    p_init.add_argument("--worktree", required=True)
    p_init.add_argument("--issues", nargs="+", required=True)
    
    # validate
    p_validate = subparsers.add_parser("validate")
    p_validate.add_argument("--branch", required=True)
    p_validate.add_argument("--worktree", required=True)
    p_validate.add_argument("--issues", nargs="+", required=True)

    # append-step
    p_step = subparsers.add_parser("append-step")
    p_step.add_argument("--issue", required=True)
    p_step.add_argument("--phase-idx", type=int, required=True)
    p_step.add_argument("--step-idx", type=int, required=True)
    p_step.add_argument("--text", required=True)
    p_step.add_argument("--actor", required=True)

    # pending-steps
    p_pending = subparsers.add_parser("pending-steps")
    p_pending.add_argument("--plan-json", required=True)

    # resume-summary
    subparsers.add_parser("resume-summary")

    # append-entry (backwards compatibility / chunk summary)
    p_append = subparsers.add_parser("append-entry")
    p_append.add_argument("--actor", required=True)
    p_append.add_argument("--chunk-idx", type=int, default=0)
    p_append.add_argument("--steps-json", required=True) # JSON string of [{issue, phase_idx, step_idx, text}]
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
        data = load_handoff(path)
        if not data:
            data = {
                "branch": args.branch,
                "worktree_path": args.worktree,
                "issues": args.issues,
                "context_fingerprint": calculate_fingerprint(args.branch, args.worktree, args.issues),
                "status": "in_progress",
                "started_at": datetime.now().isoformat(),
                "last_step_id": None,
                "entries": [],
                "phases_done": []
            }
            save_handoff(path, data)
            print(f"Handoff initialized: {path}")
        else:
            print(f"Handoff already exists: {path}")

    elif args.command == "validate":
        data = load_handoff(path)
        if not data:
            print(json.dumps({"status": "not_found"}))
            return
            
        current_fp = calculate_fingerprint(args.branch, args.worktree, args.issues)
        if data.get("context_fingerprint") == current_fp:
            print(json.dumps({"status": "ok"}))
        else:
            reason = "context mismatch (branch/worktree/issues)"
            if data.get("branch") != args.branch:
                reason = f"branch mismatch (current: {args.branch}, handoff: {data.get('branch')})"
            elif data.get("issues") != args.issues:
                reason = f"issues mismatch (current: {args.issues}, handoff: {data.get('issues')})"
            print(json.dumps({"status": "stale", "reason": reason}))

    elif args.command == "append-step":
        data = load_handoff(path)
        if not data:
            print("error: handoff file not found. run init first.", file=sys.stderr)
            sys.exit(1)
            
        if append_step_logic(data, args.issue, args.phase_idx, args.step_idx, args.text, args.actor):
            save_handoff(path, data)
            print(f"Step {args.issue}:{args.phase_idx}:{args.step_idx} appended.")
        else:
            print(f"Step {args.issue}:{args.phase_idx}:{args.step_idx} already exists.")

    elif args.command == "append-entry":
        data = load_handoff(path)
        if not data:
            print("error: handoff file not found. run init first.", file=sys.stderr)
            sys.exit(1)
            
        steps = json.loads(args.steps_json)
        for s in steps:
            # legacy format might have 'idx' instead of 'step_idx'
            s_idx = s.get("step_idx") or s.get("idx")
            append_step_logic(data, s["issue"], s.get("phase_idx", 1), s_idx, s["text"], args.actor)
            
        entry = {
            "ts": datetime.now().isoformat(),
            "type": "summary",
            "actor": args.actor,
            "chunk_idx": args.chunk_idx,
            "summary": args.summary
        }
        data["entries"].append(entry)
        save_handoff(path, data)
        print("Summary entry appended.")

    elif args.command == "pending-steps":
        data = load_handoff(path)
        completed_ids = set()
        if data:
            for entry in data.get("entries", []):
                if entry.get("type") == "step":
                    completed_ids.add(entry["step_id"])
                elif "completed_steps" in entry: # Legacy support
                    for s in entry["completed_steps"]:
                        s_idx = s.get("step_idx") or s.get("idx")
                        completed_ids.add(f"{s['issue']}:{s.get('phase_idx', 1)}:{s_idx}")

        plan_data = json.loads(Path(args.plan_json).read_text())
        pending = []
        for plan in plan_data.get("data", {}).get("plans", []):
            issue = plan["issue"]
            for phase in plan.get("phases", []):
                p_idx = phase["idx"]
                for s_rel_idx, step in enumerate(phase.get("steps", [])):
                    s_idx = s_rel_idx + 1
                    step_id = f"{issue}:{p_idx}:{s_idx}"
                    if step_id not in completed_ids:
                        pending.append({
                            "issue": issue,
                            "phase_idx": p_idx,
                            "step_idx": s_idx,
                            "text": step["text"]
                        })
        print(json.dumps(pending, ensure_ascii=False))

    elif args.command == "resume-summary":
        data = load_handoff(path)
        if not data:
            print("No handoff found.")
            return
            
        steps_done = [e for e in data.get("entries", []) if e.get("type") == "step"]
        last = data.get("last_step_id")
        
        summary = f"{len(steps_done)} steps 완료"
        if last:
            summary += f", 마지막: [{last['issue']}/Phase{last['phase_idx']}/Step{last['step_idx']}] {last['text']}"
        print(summary)

    elif args.command == "mark-phase-done":
        data = load_handoff(path)
        if data:
            if args.name not in data.get("phases_done", []):
                data.setdefault("phases_done", []).append(args.name)
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
            for entry in data.get("entries", []):
                if entry.get("type") == "step":
                    completed.append({"issue": entry["issue"], "phase_idx": entry["phase_idx"], "step_idx": entry["step_idx"]})
                elif "completed_steps" in entry: # Legacy support
                    for s in entry["completed_steps"]:
                        s_idx = s.get("step_idx") or s.get("idx")
                        completed.append({"issue": s["issue"], "phase_idx": s.get("phase_idx", 1), "step_idx": s_idx})
        print(json.dumps(completed, ensure_ascii=False))

    elif args.command == "clear":
        data = load_handoff(path)
        if data:
            data["status"] = "completed"
            save_handoff(path, data)
            
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

