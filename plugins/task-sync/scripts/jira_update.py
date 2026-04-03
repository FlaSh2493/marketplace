#!/usr/bin/env python3
"""
Jira 이슈 업데이트 (summary + description).
ADF JSON은 stdin 또는 --adf-file로 전달한다.

Usage:
  python3 jira_update.py {issue_key} --summary "제목" --adf-file adf.json
  python3 jira_update.py {issue_key} --summary "제목" < adf.json

환경변수:
  JIRA_URL    예: https://yourcompany.atlassian.net
  JIRA_USERNAME  Jira 계정 이메일
  JIRA_API_TOKEN  Jira API 토큰

Exit 0: {"ok": true}
Exit 1: {"ok": false, "reason": "..."}
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error


def get_auth_header():
    email = os.environ.get("JIRA_USERNAME")
    token = os.environ.get("JIRA_API_TOKEN")
    if not email or not token:
        return None
    creds = base64.b64encode(f"{email}:{token}".encode()).decode()
    return f"Basic {creds}"


def update_issue(issue_key, summary, adf):
    jira_url = os.environ.get("JIRA_URL", "").rstrip("/")
    auth = get_auth_header()

    missing = []
    if not jira_url:
        missing.append("JIRA_URL")
    if not auth:
        missing.append("JIRA_USERNAME / JIRA_API_TOKEN")
    if missing:
        return {"ok": False, "reason": f"환경변수 누락: {', '.join(missing)}"}

    url = f"{jira_url}/rest/api/3/issue/{issue_key}"
    payload = {"fields": {}}
    if summary:
        payload["fields"]["summary"] = summary
    if adf:
        payload["fields"]["description"] = adf

    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": auth,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="PUT",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            # PUT /issue 성공 시 204 No Content
            return {"ok": True}
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            data = json.loads(body)
            reason = "; ".join(data.get("errorMessages", [])) or body
        except Exception:
            reason = body
        return {"ok": False, "reason": f"HTTP {e.code}: {reason}"}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Jira 이슈 업데이트")
    parser.add_argument("issue_key", help="이슈 키 (예: PROJ-101)")
    parser.add_argument("--summary", default=None, help="이슈 제목")
    parser.add_argument("--adf-file", default=None, help="ADF JSON 파일 경로 (없으면 stdin)")
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

    result = update_issue(args.issue_key, args.summary, adf)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
