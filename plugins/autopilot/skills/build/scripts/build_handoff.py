#!/usr/bin/env python3
"""
build-handoff.json 파일을 관리하여 세션/에이전트 간 구현 상태를 공유한다.
이슈별 독립 파일: .docs/tasks/{issue}/build-handoff.json
"""
import json, os, subprocess, sys, shutil, hashlib
from datetime import datetime
from pathlib import Path


def find_git_root():
    r = subprocess.run("git rev-parse --git-common-dir", shell=True, capture_output=True, text=True)
    common = r.stdout.strip()
    if common:
        return os.path.abspath(os.path.join(common, ".."))
    r2 = subprocess.run("git rev-parse --show-toplevel", shell=True, capture_output=True, text=True)
    return r2.stdout.strip() or None


def get_handoff_path(issue_doc_root, issue):
    d = Path(issue_doc_root) / ".docs" / "tasks" / issue
    d.mkdir(parents=True, exist_ok=True)
    return d / "build-handoff.json"


def get_archive_dir(issue_doc_root, issue):
    d = Path(issue_doc_root) / ".docs" / "tasks" / issue / "archive"
    d.mkdir(parents=True, exist_ok=True)
    return d


def calculate_fingerprint(branch, worktree_path, issue):
    data = f"{branch}:{worktree_path}:{issue}"
    return hashlib.sha256(data.encode()).hexdigest()


def load_handoff(path):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None


def save_handoff(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def append_step_logic(data, issue, phase_idx, step_idx, text, actor):
    step_id = f"{issue}:{phase_idx}:{step_idx}"

    for entry in data.get("entries", []):
        if entry.get("type") == "step" and entry.get("step_id") == step_id:
            return False

    entry = {
        "ts": datetime.now().isoformat(),
        "type": "step",
        "actor": actor,
        "step_id": step_id,
        "issue": issue,
        "phase_idx": phase_idx,
        "step_idx": step_idx,
        "text": text,
    }
    data["entries"].append(entry)
    data["last_step_id"] = {
        "issue": issue,
        "phase_idx": phase_idx,
        "step_idx": step_idx,
        "text": text,
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
    p_init.add_argument("--issue", required=True)

    # validate
    p_validate = subparsers.add_parser("validate")
    p_validate.add_argument("--branch", required=True)
    p_validate.add_argument("--worktree", required=True)
    p_validate.add_argument("--issue", required=True)

    # append-step
    p_step = subparsers.add_parser("append-step")
    p_step.add_argument("--branch", required=True)
    p_step.add_argument("--issue", required=True)
    p_step.add_argument("--phase-idx", type=int, required=True)
    p_step.add_argument("--step-idx", type=int, required=True)
    p_step.add_argument("--text", required=True)
    p_step.add_argument("--actor", required=True)

    # pending-steps
    p_pending = subparsers.add_parser("pending-steps")
    p_pending.add_argument("--plan-json", required=True)
    p_pending.add_argument("--branch", required=True)
    p_pending.add_argument("--issue", required=True)

    # resume-summary
    p_resume = subparsers.add_parser("resume-summary")
    p_resume.add_argument("--branch", required=True)
    p_resume.add_argument("--worktree", required=True)
    p_resume.add_argument("--issue", required=True)

    # mark-phase-done
    p_phase = subparsers.add_parser("mark-phase-done")
    p_phase.add_argument("--issue", required=True)
    p_phase.add_argument("--name", required=True)

    # show
    p_show = subparsers.add_parser("show")
    p_show.add_argument("--issue", required=True)
    p_show.add_argument("--brief", action="store_true")

    # completed-step-ids
    p_completed = subparsers.add_parser("completed-step-ids")
    p_completed.add_argument("--issue", required=True)

    # clear
    p_clear = subparsers.add_parser("clear")
    p_clear.add_argument("--issue", required=True)

    args = parser.parse_args()

    root = find_git_root()
    if not root:
        print("error: git root를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    if args.command == "init":
        path = get_handoff_path(root, args.issue)
        data = load_handoff(path)
        if not data:
            data = {
                "branch": args.branch,
                "worktree_path": args.worktree,
                "issue": args.issue,
                "context_fingerprint": calculate_fingerprint(args.branch, args.worktree, args.issue),
                "status": "in_progress",
                "started_at": datetime.now().isoformat(),
                "last_step_id": None,
                "entries": [],
                "phases_done": [],
            }
            save_handoff(path, data)
            print(f"Handoff initialized: {path}")
        else:
            print(f"Handoff already exists: {path}")

    elif args.command == "validate":
        path = get_handoff_path(root, args.issue)
        data = load_handoff(path)
        if not data:
            print(json.dumps({"status": "not_found"}))
            return

        current_fp = calculate_fingerprint(args.branch, args.worktree, args.issue)
        if data.get("context_fingerprint") == current_fp:
            print(json.dumps({"status": "ok"}))
        else:
            reason = "context mismatch (branch/worktree/issue)"
            if data.get("branch") != args.branch:
                reason = f"branch mismatch (current: {args.branch}, handoff: {data.get('branch')})"
            print(json.dumps({"status": "stale", "reason": reason}))

    elif args.command == "append-step":
        path = get_handoff_path(root, args.issue)
        data = load_handoff(path)
        if not data:
            print("error: handoff file not found. run init first.", file=sys.stderr)
            sys.exit(1)

        if append_step_logic(data, args.issue, args.phase_idx, args.step_idx, args.text, args.actor):
            save_handoff(path, data)
            print(f"Step {args.issue}:{args.phase_idx}:{args.step_idx} appended.")
        else:
            print(f"Step {args.issue}:{args.phase_idx}:{args.step_idx} already exists.")

    elif args.command == "pending-steps":
        path = get_handoff_path(root, args.issue)
        data = load_handoff(path)
        completed_ids = set()
        if data:
            for entry in data.get("entries", []):
                if entry.get("type") == "step":
                    completed_ids.add(entry["step_id"])

        plan_data = json.loads(Path(args.plan_json).read_text())
        pending = []
        for plan in plan_data.get("data", {}).get("plans", []):
            if plan["issue"] != args.issue:
                continue
            for phase in plan.get("phases", []):
                p_idx = phase["idx"]
                for s_rel_idx, step in enumerate(phase.get("steps", [])):
                    s_idx = s_rel_idx + 1
                    step_id = f"{args.issue}:{p_idx}:{s_idx}"
                    if step_id not in completed_ids:
                        pending.append({
                            "issue": args.issue,
                            "phase_idx": p_idx,
                            "step_idx": s_idx,
                            "text": step["text"],
                        })
        print(json.dumps(pending, ensure_ascii=False))

    elif args.command == "resume-summary":
        path = get_handoff_path(root, args.issue)
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
        path = get_handoff_path(root, args.issue)
        data = load_handoff(path)
        if data:
            if args.name not in data.get("phases_done", []):
                data.setdefault("phases_done", []).append(args.name)
                save_handoff(path, data)
            print(f"Phase {args.name} marked as done.")

    elif args.command == "show":
        path = get_handoff_path(root, args.issue)
        data = load_handoff(path)
        if not data:
            print(json.dumps({"status": "empty"}, ensure_ascii=False))
        elif getattr(args, "brief", False):
            steps_done = [e for e in data.get("entries", []) if e.get("type") == "step"]
            last = data.get("last_step_id")
            last_str = ""
            if last:
                last_str = f" | 마지막: [{last['issue']}/Phase{last['phase_idx']}/Step{last['step_idx']}] \"{last['text']}\""
            ids = ", ".join(e["step_id"] for e in steps_done)
            print(f"완료된 step: {len(steps_done)}개{last_str}")
            if ids:
                print(f"완료된 IDs: {ids}")
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))

    elif args.command == "completed-step-ids":
        path = get_handoff_path(root, args.issue)
        data = load_handoff(path)
        completed = []
        if data:
            for entry in data.get("entries", []):
                if entry.get("type") == "step":
                    completed.append({
                        "issue": entry["issue"],
                        "phase_idx": entry["phase_idx"],
                        "step_idx": entry["step_idx"],
                    })
        print(json.dumps(completed, ensure_ascii=False))

    elif args.command == "clear":
        path = get_handoff_path(root, args.issue)
        data = load_handoff(path)
        if data:
            data["status"] = "completed"
            save_handoff(path, data)

            archive_dir = get_archive_dir(root, args.issue)
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
