#!/usr/bin/env python3
"""
cruise 설정 로더 — **단일 파일** `~/.config/cruise/config.json`.

설정과 토큰을 한 파일에서 관리한다:
- `credentials` 블록: email / jira_api_token (비밀)
- `settings` 블록(선택): 팀 공통값 오버라이드. 없으면 코드의 DEFAULTS 사용.

이 파일은 secrets를 담으므로 레포 밖(`~/.config/cruise`)에 두고 600 권한으로 저장하며
`.gitignore`로 제외한다. `setup_config.py`로 생성/수정/삭제한다.
"""
import copy
import json
import os
import sys
from pathlib import Path


def _state_dir() -> Path:
    """버전 무관 전용 상태 디렉토리.

    우선순위: `$CRUISE_HOME` > `$XDG_CONFIG_HOME/cruise` > `~/.config/cruise`.
    """
    override = os.getenv("CRUISE_HOME")
    if override:
        return Path(override).expanduser()
    xdg = os.getenv("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "cruise"


STATE_DIR = _state_dir()
CONFIG_PATH = STATE_DIR / "config.json"  # 단일 설정+토큰 파일

# 팀 공통값(비밀 아님). 다른 조직은 config.json의 settings 블록으로 필요한 키만 덮으면 된다.
DEFAULTS = {
    "base_url": "https://madup.atlassian.net",
    "default_project": None,  # plan 분기 C(신규 이슈 생성) 기본 프로젝트 키. 없으면 create 비활성.
    "tasks_root": "~/Documents/tasks",  # 산출물 저장 루트
}


def load_config_file() -> dict:
    """단일 config.json 로드. 없으면 빈 dict. 최상위가 객체가 아니면 무시(경고)."""
    if not CONFIG_PATH.is_file():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️ {CONFIG_PATH} 읽기 실패({e}) — 기본값으로 진행합니다.", file=sys.stderr)
        return {}
    if not isinstance(data, dict):
        print(f"⚠️ {CONFIG_PATH} 최상위가 JSON 객체가 아닙니다 — 무시하고 기본값 사용.", file=sys.stderr)
        return {}
    return data


def _deep_merge(base: dict, overrides: dict) -> dict:
    """overrides를 base 위에 재귀 병합(중첩 dict는 병합, 나머지는 truthy만 덮음)."""
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        elif value not in (None, "", [], {}):
            base[key] = value
    return base


def load_settings() -> dict:
    """DEFAULTS를 기본으로, config.json의 `settings` 블록을 재귀 병합."""
    settings = copy.deepcopy(DEFAULTS)
    override = load_config_file().get("settings")
    if isinstance(override, dict):
        _deep_merge(settings, override)
    return settings


def _credentials() -> dict:
    """config.json의 credentials 블록(딕셔너리 보장)."""
    creds = load_config_file().get("credentials")
    return creds if isinstance(creds, dict) else {}


def get_credentials() -> tuple[str, str]:
    """config.json의 credentials에서 (email, jira_api_token) 로드. 누락 시 명확한 에러로 종료."""
    creds = _credentials()
    email = (creds.get("email") or "").strip()
    token = (creds.get("jira_api_token") or "").strip()
    if not email or not token:
        print("❌ Jira 인증 정보가 없습니다.", file=sys.stderr)
        print(f"   설정 파일: {CONFIG_PATH}", file=sys.stderr)
        print("   터미널에서 다음을 실행해 설정하세요: python3 scripts/setup_config.py", file=sys.stderr)
        print("   토큰 발급: https://id.atlassian.com/manage-profile/security/api-tokens", file=sys.stderr)
        sys.exit(1)
    return email, token


def get_env() -> dict:
    """Jira 접속 정보 {base_url, email, token}. 기존 호출부 호환용 — config에서 조립."""
    email, token = get_credentials()
    return {
        "base_url": str(load_settings()["base_url"]).rstrip("/"),
        "email": email,
        "token": token,
    }


def default_project() -> str | None:
    """Optional default Jira project key for issue creation (cruise plan 분기 C).
    없으면 create 경로가 비활성화되고 cruise는 local cruise-inline task.md로 폴백한다."""
    p = load_settings().get("default_project")
    return (str(p).strip() or None) if p else None


def tasks_root() -> Path:
    """산출물 저장 루트. config.json settings.tasks_root(기본 ~/Documents/tasks)를 해석."""
    return Path(str(load_settings()["tasks_root"])).expanduser()


def issue_dir(key: str) -> Path:
    d = tasks_root() / key
    d.mkdir(parents=True, exist_ok=True)
    return d


def attachments_dir(key: str) -> Path:
    d = issue_dir(key) / "attachments"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_file(key: str) -> Path:
    return issue_dir(key) / ".log"


def check_deps():
    missing = []
    try:
        import requests  # noqa: F401
    except ImportError:
        missing.append("requests")
    try:
        import yaml  # noqa: F401
    except ImportError:
        missing.append("PyYAML")
    if missing:
        print(f"error: missing Python packages: {', '.join(missing)}", file=sys.stderr)
        print(f"  pip install {' '.join(missing)}", file=sys.stderr)
        sys.exit(1)
