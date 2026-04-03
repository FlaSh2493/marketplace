#!/usr/bin/env python3
"""
Jira API 직접 호출을 통한 이슈 데이터 조회 및 파일 저장
환경변수 기반 인증 (JIRA_URL, JIRA_EMAIL, JIRA_TOKEN)
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any


def _load_claude_env():
    """
    .claude/settings.local.json → .claude/settings.json 순서로 env 필드를 읽어
    os.environ에 없는 키만 주입한다.
    """
    import subprocess
    result = subprocess.run(
        "git rev-parse --show-toplevel",
        shell=True, capture_output=True, text=True
    )
    git_root = result.stdout.strip()
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

_load_claude_env()


def get_auth_header() -> Optional[str]:
    """Basic Auth 헤더 생성"""
    email = os.environ.get('JIRA_EMAIL')
    token = os.environ.get('JIRA_TOKEN')

    if not email or not token:
        return None

    creds = f"{email}:{token}"
    encoded = base64.b64encode(creds.encode()).decode()
    return f"Basic {encoded}"

def fetch_issue(issue_key: str) -> Dict[str, Any]:
    """
    Jira 이슈 상세 정보 조회

    Returns:
        {"ok": True, "data": {...}} 또는 {"ok": False, "reason": "..."}
    """
    jira_url = os.environ.get('JIRA_URL')
    auth = get_auth_header()

    if not jira_url or not auth:
        return {
            "ok": False,
            "reason": "JIRA_URL, JIRA_EMAIL, JIRA_TOKEN 환경변수가 필요합니다"
        }

    url = (
        f"{jira_url.rstrip('/')}/rest/api/3/issue/{issue_key}"
        "?fields=summary,description,status,assignee,created,attachment,comment"
    )

    try:
        req = urllib.request.Request(url)
        req.add_header("Authorization", auth)
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return {"ok": True, "data": data}

    except urllib.error.HTTPError as e:
        error_msg = e.read().decode() if e.fp else str(e)
        try:
            error_data = json.loads(error_msg)
            reason = error_data.get('errorMessages', [str(e)])[0]
        except:
            reason = str(e)
        return {"ok": False, "reason": reason}
    except Exception as e:
        return {"ok": False, "reason": str(e)}

def search_issues(jql: str = None) -> Dict[str, Any]:
    """
    Jira JQL 검색
    jql이 없으면 기본값: assignee=currentUser() AND statusCategory!=Done

    Returns:
        {"ok": True, "data": {...}} 또는 {"ok": False, "reason": "..."}
    """
    jira_url = os.environ.get('JIRA_URL')
    auth = get_auth_header()
    email = os.environ.get('JIRA_EMAIL')

    if not jira_url or not auth:
        return {
            "ok": False,
            "reason": "JIRA_URL, JIRA_EMAIL, JIRA_TOKEN 환경변수가 필요합니다"
        }

    if jql is None:
        # 기본값: 현재 사용자에게 할당되고 Done이 아닌 이슈
        jql = f'assignee = "{email}" AND statusCategory != Done'

    url = (
        f"{jira_url.rstrip('/')}/rest/api/3/search"
        f"?jql={urllib.parse.quote(jql)}"
        f"&fields=summary,status,assignee"
        f"&maxResults=50"
    )

    try:
        req = urllib.request.Request(url)
        req.add_header("Authorization", auth)
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return {"ok": True, "data": data}

    except urllib.error.HTTPError as e:
        error_msg = e.read().decode() if e.fp else str(e)
        try:
            error_data = json.loads(error_msg)
            reason = error_data.get('errorMessages', [str(e)])[0]
        except:
            reason = str(e)
        return {"ok": False, "reason": reason}
    except Exception as e:
        return {"ok": False, "reason": str(e)}

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Jira API 조회 및 파일 저장")
    parser.add_argument('issue_key', nargs='?', help="이슈 키 (예: PROJ-101)")
    parser.add_argument('--search', action='store_true', help="JQL 검색 모드")
    parser.add_argument('--jql', default=None, help="JQL 쿼리 (--search와 함께 사용)")
    parser.add_argument('--out-dir', default='.', help="출력 디렉토리 (기본값: 현재 디렉토리)")

    args = parser.parse_args()

    # 출력 디렉토리 확인/생성
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.search:
        # 검색 모드
        result = search_issues(args.jql)
        out_file = out_dir / "jira_search.json"
    else:
        # 이슈 조회 모드
        if not args.issue_key:
            print(json.dumps({"ok": False, "reason": "이슈 키를 지정하세요"}))
            sys.exit(1)

        result = fetch_issue(args.issue_key)
        out_file = out_dir / f"{args.issue_key}_raw.json"

    # 결과 저장
    if result["ok"]:
        with open(out_file, 'w') as f:
            json.dump(result["data"], f, indent=2, ensure_ascii=False)
        print(json.dumps({"ok": True, "file": str(out_file)}))
        sys.exit(0)
    else:
        print(json.dumps({"ok": False, "reason": result["reason"]}))
        sys.exit(1)

if __name__ == '__main__':
    main()
