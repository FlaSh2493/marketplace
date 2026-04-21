#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def find_main_root():
    """어느 워크트리에서 실행해도 메인 워크트리 루트를 반환한다."""
    out, _, rc = run("git worktree list --porcelain")
    if rc == 0:
        lines = out.splitlines()
        for line in lines:
            if line.startswith("worktree "):
                return line[9:].strip()
    
    out, _, rc = run("git rev-parse --show-toplevel")
    return out if rc == 0 else None

def read_autopilot_meta(worktree_path):
    meta_path = Path(worktree_path) / ".autopilot"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            if "issues" in meta and "issue" not in meta:
                issues_list = meta.get("issues", [])
                meta["issue"] = issues_list[0] if issues_list else ""
            return meta
        except Exception:
            pass
    return {}

def resolve_issue(args=None):
    """
    이슈 키를 결정한다.
    1. --issue 인자 존재 시 사용
    2. CWD에서 .autopilot을 찾아 issue 필드 읽기
    3. 실패 시 에러 출력 후 exit 1
    """
    issue = None
    
    # 1. args에서 찾기
    if args:
        if "--issue" in args:
            idx = args.index("--issue")
            if idx + 1 < len(args):
                issue = args[idx + 1]
    
    # 2. CWD에서 찾기
    if not issue:
        out, _, rc = run("git rev-parse --show-toplevel")
        if rc == 0:
            meta = read_autopilot_meta(out)
            issue = meta.get("issue")
            
    if not issue:
        print("error: 이슈 키를 찾을 수 없습니다. --issue 인자를 제공하거나 .autopilot 파일이 있는 워크트리에서 실행하세요.", file=sys.stderr)
        sys.exit(1)
        
    return issue

def get_issue_state_dir(issue):
    root = find_main_root()
    if not root:
        print("error: git 루트를 찾을 수 없습니다", file=sys.stderr)
        sys.exit(1)
    
    d = Path(root) / "tasks" / issue / "checkpoints"
    d.mkdir(parents=True, exist_ok=True)
    return d
