#!/usr/bin/env python3
"""
Jira Story 생성.
ADF JSON은 stdin 또는 --adf-file로 전달한다.

Usage:
  python3 jira_create.py --project PROJ --summary "제목" --adf-file adf.json
  python3 jira_create.py --project PROJ --summary "제목" [--epic PROJ-10] [--sprint 42] < adf.json

환경변수:
  JIRA_URL    예: https://yourcompany.atlassian.net
  JIRA_EMAIL  Jira 계정 이메일
  JIRA_TOKEN  Jira API 토큰

Exit 0: {"ok": true, "key": "PROJ-101"}
Exit 1: {"ok": false, "reason": "..."}
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error


def get_auth_header():
    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_TOKEN")
    if not email or not token:
        return None
    creds = base64.b64encode(f"{email}:{token}".encode()).decode()
    return f"Basic {creds}"


def get_current_user(jira_url, auth):
    """현재 로그인 사용자의 accountId 조회"""
    url = f"{jira_url}/rest/api/3/myself"
    req = urllib.request.Request(url, headers={
        "Authorization": auth,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data.get("accountId")
    except Exception:
        return None


def create_issue(project_key, summary, adf, epic=None, sprint=None):
    jira_url = os.environ.get("JIRA_URL", "").rstrip("/")
    auth = get_auth_header()

    missing = []
    if not jira_url:
        missing.append("JIRA_URL")
    if not auth:
        missing.append("JIRA_EMAIL / JIRA_TOKEN")
    if missing:
        return {"ok": False, "reason": f"환경변수 누락: {', '.join(missing)}"}

    account_id = get_current_user(jira_url, auth)

    fields = {
        "project": {"key": project_key},
        "issuetype": {"name": "Story"},
        "summary": summary,
    }

    if adf:
        fields["description"] = adf

    if account_id:
        fields["assignee"] = {"accountId": account_id}

    if epic:
        # Jira Cloud: customfield_10014 (Epic Link)
        fields["customfield_10014"] = epic

    if sprint:
        # Jira Cloud: customfield_10020 (Sprint)
        try:
            fields["customfield_10020"] = {"id": int(sprint)}
        except (ValueError, TypeError):
            fields["customfield_10020"] = {"name": str(sprint)}

    url = f"{jira_url}/rest/api/3/issue"
    data = json.dumps({"fields": fields}, ensure_ascii=False).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": auth,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
            return {"ok": True, "key": result.get("key")}
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            err_data = json.loads(body)
            msgs = err_data.get("errorMessages", [])
            errs = list(err_data.get("errors", {}).values())
            reason = "; ".join(msgs + errs) or body
        except Exception:
            reason = body
        return {"ok": False, "reason": f"HTTP {e.code}: {reason}"}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Jira Story 생성")
    parser.add_argument("--project", required=True, help="Jira 프로젝트 키 (예: PROJ)")
    parser.add_argument("--summary", required=True, help="이슈 제목")
    parser.add_argument("--adf-file", default=None, help="ADF JSON 파일 경로 (없으면 stdin)")
    parser.add_argument("--epic", default=None, help="Epic 키 (선택, 예: PROJ-10)")
    parser.add_argument("--sprint", default=None, help="Sprint ID 또는 이름 (선택)")
    args = parser.parse_args()

    # ADF 로드
    adf = None
    if args.adf_file:
        if not os.path.exists(args.adf_file):
            print(json.dumps({"ok": False, "reason": f"파일 없음: {args.adf_file}"}))
            sys.exit(1)
        with open(args.adf_file, encoding="utf-8") as f:
            adf = json.load(f)
    elif not sys.stdin.isatty():
        adf = json.load(sys.stdin)

    result = create_issue(args.project, args.summary, adf, args.epic, args.sprint)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
