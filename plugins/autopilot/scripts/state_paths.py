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

    if args:
        if "--issue" in args:
            idx = args.index("--issue")
            if idx + 1 < len(args):
                issue = args[idx + 1]

    if not issue:
        out, _, rc = run("git rev-parse --show-toplevel")
        if rc == 0:
            meta = read_autopilot_meta(out)
            issue = meta.get("issue")

    if not issue:
        print(
            "error: 이슈 키를 찾을 수 없습니다. --issue 인자를 제공하거나 .autopilot 파일이 있는 워크트리에서 실행하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    return issue


def get_autopilot_home() -> Path:
    """~/Documents/autopilot/ 디렉토리를 반환한다."""
    return Path.home() / "Documents" / "autopilot"


def get_issue_dir(issue: str) -> Path:
    """~/Documents/autopilot/{issue}/ 디렉토리를 반환한다."""
    d = get_autopilot_home() / issue
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_meta_path(issue: str) -> Path:
    """~/Documents/autopilot/{issue}/meta.json 경로를 반환한다."""
    return get_issue_dir(issue) / "meta.json"


def get_sessions_dir() -> Path:
    """~/Documents/autopilot/sessions/ 디렉토리를 반환한다."""
    d = get_autopilot_home() / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_meta(issue: str) -> dict:
    """meta.json을 읽어 dict로 반환한다. 없으면 빈 dict."""
    path = get_meta_path(issue)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def write_meta(issue: str, data: dict):
    """meta.json에 data를 저장한다."""
    path = get_meta_path(issue)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def update_meta_key(issue: str, key: str, value: dict):
    """meta.json의 특정 키만 업데이트한다."""
    meta = read_meta(issue)
    meta[key] = value
    write_meta(issue, meta)


def clear_meta_keys(issue: str, keys: list):
    """meta.json에서 지정된 키들을 삭제한다."""
    meta = read_meta(issue)
    for key in keys:
        meta.pop(key, None)
    write_meta(issue, meta)


# Backward compatibility alias
def get_issue_state_dir(issue: str) -> Path:
    return get_issue_dir(issue)
