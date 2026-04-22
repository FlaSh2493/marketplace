#!/usr/bin/env python3
"""
Jira 이슈 조회 전용. jira.json 저장만 수행.
Usage:
  python3 fetch.py [이슈키...] --task-dir tasks/
  인수 없으면: 내 할당 미완료 이슈 조회 후 jira.json 저장
  인수 있으면: 지정된 이슈키를 jira.json에서 필터링
Exit 0: 성공
Exit 1: 실패
"""

import argparse
import json
import os
import sys

from common import find_git_root, get_task_dir, load_claude_env
from jira_fetch import search_issues

load_claude_env()


def main():
    parser = argparse.ArgumentParser(description="Jira 이슈 조회 전용")
    parser.add_argument("issue_keys", nargs="*", help="필터할 이슈키 (생략 시 전체)")
    parser.add_argument("--task-dir", help="tasks 디렉토리 (기본: git root/tasks)")
    args = parser.parse_args()

    root = None
    if not args.task_dir:
        import subprocess
        r = subprocess.run("git rev-parse --show-toplevel", shell=True,
                           capture_output=True, text=True)
        root = r.stdout.strip()

    task_dir = args.task_dir or os.path.join(root, "tasks")
    jira_json_path = os.path.join(task_dir, "jira.json")

    # Jira 검색
    search = search_issues()
    if not search["ok"]:
        print(f"❌ Jira 조회 실패: {search['reason']}", file=sys.stderr)
        sys.exit(1)

    issues = search["data"].get("issues", [])
    if not issues:
        print("조회된 이슈가 없습니다.")
        sys.exit(0)

    # 이슈키 필터링 (지정된 경우)
    if args.issue_keys:
        all_keys = [i.get("key") for i in issues]
        filtered = [i for i in issues if i.get("key") in args.issue_keys]
        if not filtered:
            print(f"⚠ 필터링 결과: 매칭된 이슈 없음", file=sys.stderr)
            sys.exit(1)
        issues = filtered

    # jira.json 저장
    os.makedirs(task_dir, exist_ok=True)
    with open(jira_json_path, "w", encoding="utf-8") as f:
        json.dump({"issues": issues}, f, indent=2, ensure_ascii=False)

    # 테이블 출력
    print("\n| 번호 | Jira Key | 제목 | 상태 |")
    print("|-----|----------|------|------|")
    for idx, issue in enumerate(issues, 1):
        key = issue.get("key", "")
        summary = issue.get("fields", {}).get("summary", "")
        status = issue.get("fields", {}).get("status", {}).get("name", "")
        print(f"| {idx} | {key} | {summary} | {status} |")
    print()

    print(f"✓ {len(issues)}개 이슈 조회 완료 → {jira_json_path} 저장")


if __name__ == "__main__":
    main()
