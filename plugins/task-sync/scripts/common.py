#!/usr/bin/env python3
"""
task-sync 스크립트 공통 유틸리티.
git root 탐색, 환경변수 로드, JSON 출력 헬퍼.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def find_git_root() -> str | None:
    """git common-dir → 상위 디렉토리, 없으면 show-toplevel 사용."""
    r = subprocess.run(
        "git rev-parse --git-common-dir",
        shell=True, capture_output=True, text=True,
    )
    common = r.stdout.strip()
    if common:
        return os.path.abspath(os.path.join(common, ".."))
    r2 = subprocess.run(
        "git rev-parse --show-toplevel",
        shell=True, capture_output=True, text=True,
    )
    return r2.stdout.strip() or None


def get_branch() -> str | None:
    """현재 브랜치명 반환."""
    r = subprocess.run(
        "git rev-parse --abbrev-ref HEAD",
        shell=True, capture_output=True, text=True,
    )
    return r.stdout.strip() or None


def load_claude_env():
    """
    .claude/settings.local.json → .claude/settings.json 순서로
    env 필드를 읽어 os.environ에 없는 키만 주입.
    """
    git_root = find_git_root()
    if not git_root:
        return

    for fname in ("settings.local.json", "settings.json"):
        settings_path = Path(git_root) / ".claude" / fname
        if not settings_path.exists():
            continue
        try:
            with open(settings_path, encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.get("env", {}).items():
                if k not in os.environ:
                    os.environ[k] = v
        except Exception:
            pass


def get_task_dir(root: str) -> str:
    return os.path.join(root, ".docs", "tasks")


def get_state_dir(root: str) -> str:
    return os.path.join(root, ".docs", "tasks", ".state")


def ok(data=None):
    """성공 JSON 출력 후 exit 0."""
    print(json.dumps({"status": "ok", "data": data or {}}, ensure_ascii=False))
    sys.exit(0)


def error(code: str, reason: str):
    """에러 JSON 출력 후 exit 1."""
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)
