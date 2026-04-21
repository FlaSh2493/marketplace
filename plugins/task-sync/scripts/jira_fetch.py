#!/usr/bin/env python3
"""
Jira API 직접 호출을 통한 이슈 데이터 조회 및 파일 저장
환경변수 기반 인증 (JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN)
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
from common import load_claude_env

load_claude_env()


def get_auth_header() -> Optional[str]:
    """Basic Auth 헤더 생성"""
    email = os.environ.get('JIRA_USERNAME')
    token = os.environ.get('JIRA_API_TOKEN')

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
            "reason": "JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN 환경변수가 필요합니다"
        }

    url = (
        f"{jira_url.rstrip('/')}/rest/api/3/issue/{issue_key}"
        "?fields=summary,description,status,assignee,created,attachment,comment"
        "&expand=renderedFields"
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
    email = os.environ.get('JIRA_USERNAME')

    if not jira_url or not auth:
        return {
            "ok": False,
            "reason": "JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN 환경변수가 필요합니다"
        }

    if jql is None:
        # 기본값: 현재 사용자에게 할당되고 Done이 아닌 이슈
        jql = f'assignee = "{email}" AND statusCategory != Done'

    url = (
        f"{jira_url.rstrip('/')}/rest/api/3/search/jql"
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
    parser.add_argument('--format', default='json', choices=['json', 'table'],
                        help="출력 형식: json(기본) 또는 table(번호 테이블+매핑)")

    args = parser.parse_args()

    # 출력 디렉토리 확인/생성
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.search:
        # 검색 모드
        result = search_issues(args.jql)
        if not result["ok"]:
            guide = (
                "\n\n⚠️  자동 조회에 실패했습니다.\n\n"
                "다음 중 하나를 선택하세요:\n\n"
                "1  이슈 키 직접 입력:\n"
                "    /task-sync:fetch PROJ-101 PROJ-102\n\n"
                "2  Jira 웹사이트에서 확인:\n"
                "    https://madup.atlassian.net/jira/your-work\n\n"
                "3  나중에 다시 시도:\n"
                "    /task-sync:fetch"
            )
            result["reason"] = result["reason"] + guide
            print(json.dumps({"ok": False, "reason": result["reason"]}, ensure_ascii=False))
            sys.exit(1)
        out_file = out_dir / "jira.json"
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

        if args.search and args.format == 'table':
            # 테이블 + 번호→이슈키 매핑 출력
            issues = result["data"].get("issues", [])
            mapping = {}
            table_lines = ["| 번호 | Jira Key | 제목 | 상태 |",
                           "|-----|----------|------|------|"]
            for idx, issue in enumerate(issues, 1):
                key = issue.get("key", "")
                summary = issue.get("fields", {}).get("summary", "")
                status = issue.get("fields", {}).get("status", {}).get("name", "")
                table_lines.append(f"| {idx} | {key} | {summary} | {status} |")
                mapping[str(idx)] = key
            table_str = "\n".join(table_lines)
            print(json.dumps({
                "ok": True,
                "file": str(out_file),
                "table": table_str,
                "mapping": mapping,
                "count": len(issues),
            }, ensure_ascii=False))
        else:
            print(json.dumps({"ok": True, "file": str(out_file)}))
        sys.exit(0)
    else:
        print(json.dumps({"ok": False, "reason": result["reason"]}))
        sys.exit(1)

if __name__ == '__main__':
    main()
