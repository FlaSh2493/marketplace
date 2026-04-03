#!/usr/bin/env python3
"""
템플릿 기반 이슈 파일 생성. Claude 직접 파일 작성 금지 — 이 스크립트만 파일을 생성한다.
Usage:
  python3 create_task_file.py {branch} {issue_key} {title} \
    [--status {status}] [--assignee {assignee}] [--source {source}] \
    [--created-at {datetime}] [--deps {deps}] [--api {api}] [--states {states}]

설명(description)은 stdin으로 전달한다 (길이 제한 없음):
  echo "{설명 내용}" | python3 create_task_file.py {branch} {issue_key} {title}

Exit 0: ok (data.file_path) / Exit 1: error
"""
import argparse, json, os, sys
from datetime import datetime


def find_git_root():
    import subprocess
    r = subprocess.run("git rev-parse --git-common-dir", shell=True, capture_output=True, text=True)
    common = r.stdout.strip()
    if common:
        return os.path.abspath(os.path.join(common, ".."))
    r2 = subprocess.run("git rev-parse --show-toplevel", shell=True, capture_output=True, text=True)
    return r2.stdout.strip() or None


def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def build_content(issue_key, title, status, assignee, created_at, source,
                  description, deps, api, states):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    jira_val = issue_key if not issue_key.startswith("FE-") else "미생성"

    dep_line = f"- {deps}" if deps and deps != "없음" else "- SPT-XXXX (없으면 생략)"

    lines = [
        f"# {issue_key}: {title}",
        "",
        f"- jira: {jira_val}",
        f"- 상태: {status}",
        f"- 담당자: {assignee}",
        f"- 생성일: {created_at}",
        f"- 최근 업데이트: {now}",
        f"- 출처: {source}",
        "",
        "---",
        "",
        "## 목적",
        "",
        description.strip() if description else "(왜 이 작업이 필요한가. 1~2줄)",
        "",
        "---",
        "",
        "## 요구사항",
        "",
        "- [ ] 요건 1",
        "- [ ] 요건 2",
        "",
        "---",
        "",
        "## 완료 기준",
        "",
        "- [ ] 사용자가 X를 하면 Y가 된다",
        "",
        "---",
        "",
        "## 선행 이슈",
        "",
        dep_line,
        "",
        "---",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("branch")
    parser.add_argument("issue_key")
    parser.add_argument("title")
    parser.add_argument("--status", default="신규")
    parser.add_argument("--assignee", default="@본인")
    parser.add_argument("--source", default="extract")
    parser.add_argument("--created-at", default=None)
    parser.add_argument("--deps", default="없음")
    parser.add_argument("--api", default="없음")
    parser.add_argument("--states", default="없음")
    args = parser.parse_args()

    # 설명은 stdin으로 수신 (길이 제한 없이 원본 보존)
    description = sys.stdin.read() if not sys.stdin.isatty() else ""

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    task_dir = os.path.join(root, ".docs", "task", args.branch.replace("/", os.sep))
    issue_dir = os.path.join(task_dir, args.issue_key)
    os.makedirs(issue_dir, exist_ok=True)
    os.makedirs(os.path.join(issue_dir, "assets"), exist_ok=True)
    os.makedirs(os.path.join(task_dir, ".state"), exist_ok=True)

    file_path = os.path.join(issue_dir, f"{args.issue_key}.md")
    created_at = args.created_at or datetime.now().strftime("%Y-%m-%d %H:%M")

    content = build_content(
        issue_key=args.issue_key,
        title=args.title,
        status=args.status,
        assignee=args.assignee,
        created_at=created_at,
        source=args.source,
        description=description,
        deps=args.deps,
        api=args.api,
        states=args.states,
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    ok({"file_path": file_path, "issue_key": args.issue_key})


if __name__ == "__main__":
    main()
