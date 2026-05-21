"""
jsync list — Jira 활성스프린트 이슈 목록 조회 (stdout only, 디스크 저장 없음).

Usage:
  list.py MKT                        # 활성스프린트 × 본인할당
  list.py MKT,ADX                    # 다중 프로젝트
  list.py MKT ADX                    # 다중 프로젝트 (공백)
  list.py MKT --all                  # 스프린트 전체 (할당 제약 해제)
  list.py MKT --jql "priority = High" # 추가 필터
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import check_deps
check_deps()

from jira_client import search_issues

ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+-\d+$")


def parse_args(argv: list[str]) -> tuple[list[str], bool, str]:
    all_flag = False
    extra_jql = ""
    tokens = []
    i = 0
    while i < len(argv):
        if argv[i] == "--all":
            all_flag = True
            i += 1
        elif argv[i] == "--jql" and i + 1 < len(argv):
            extra_jql = argv[i + 1]
            i += 2
        else:
            for t in argv[i].split(","):
                t = t.strip()
                if t:
                    tokens.append(t)
            i += 1

    if not tokens:
        print("error: no project key given", file=sys.stderr)
        print("  usage: list.py MKT   or   list.py MKT,ADX", file=sys.stderr)
        sys.exit(1)

    issue_keys = [t for t in tokens if ISSUE_KEY_RE.match(t)]
    if issue_keys:
        print("error: list only accepts project keys, not issue keys", file=sys.stderr)
        print("  use: fetch.py <KEY> to fetch a specific issue", file=sys.stderr)
        sys.exit(1)

    return tokens, all_flag, extra_jql


def build_jql(project_keys: list[str], all_flag: bool, extra_jql: str) -> str:
    proj = ", ".join(project_keys)
    jql = f"project in ({proj}) AND sprint in openSprints()"
    if not all_flag:
        jql += " AND assignee = currentUser()"
    if extra_jql:
        jql += f" AND ({extra_jql})"
    return jql


def main():
    argv = sys.argv[1:]
    project_keys, all_flag, extra_jql = parse_args(argv)
    jql = build_jql(project_keys, all_flag, extra_jql)

    issues = search_issues(jql, fields="summary,status,assignee")

    if not issues:
        scope = "active sprint" + ("" if all_flag else ", assigned to you")
        print(f"no issues found in {','.join(project_keys)} ({scope})")
        return

    # Column widths
    max_key = max(len(i["key"]) for i in issues)
    max_status = max(len((i["fields"].get("status") or {}).get("name", "") or "") for i in issues)

    for issue in issues:
        key = issue["key"].ljust(max_key)
        status = (issue["fields"].get("status") or {}).get("name", "")
        status_col = f"[{status}]".ljust(max_status + 2)
        summary = issue["fields"].get("summary", "")
        assignee = (issue["fields"].get("assignee") or {}).get("emailAddress", "")
        assignee_col = f"  ({assignee})" if all_flag and assignee else ""
        print(f"{key}  {status_col}  {summary}{assignee_col}")


if __name__ == "__main__":
    main()
