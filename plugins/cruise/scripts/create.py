"""
cruise create — Jira에 새 이슈를 생성. (cruise plan 분기 C에서 호출)

Usage:
  create.py --project MKT --type Task --summary "요약"          # description 없음
  echo "설명 마크다운" | create.py --project MKT --summary "요약" # stdin = description
  create.py --summary "요약"    # --project 생략 시 JIRA_DEFAULT_PROJECT 사용

Output (stdout, 성공 시 1줄):
  MKT-500

--type 기본값은 Task. description은 stdin(비어있으면 생략).
필수 커스텀필드(스프린트·에픽 등) 때문에 400이 나면 Jira 에러 필드를 그대로 노출한다.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import check_deps, default_project
check_deps()

from jira_client import create_issue
from md_adf import md_to_adf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None, help="Jira 프로젝트 키 (생략 시 JIRA_DEFAULT_PROJECT)")
    ap.add_argument("--type", default="Task", help="이슈 타입 (기본 Task)")
    ap.add_argument("--summary", required=True, help="이슈 요약(제목)")
    args = ap.parse_args()

    project = args.project or default_project()
    if not project:
        print("error: no project key. pass --project or set JIRA_DEFAULT_PROJECT", file=sys.stderr)
        sys.exit(1)

    # description: stdin (파이프로 들어온 경우만)
    description_adf = None
    if not sys.stdin.isatty():
        md = sys.stdin.read().strip()
        if md:
            description_adf = md_to_adf(md)

    issue = create_issue(project, args.type, args.summary, description_adf)
    print(issue["key"])


if __name__ == "__main__":
    main()
