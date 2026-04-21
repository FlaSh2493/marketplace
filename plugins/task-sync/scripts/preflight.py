#!/usr/bin/env python3
"""
스킬 실행 전 전제조건 검증. 모든 스킬의 STEP 0에서 호출.
Usage: python3 preflight.py {skill} [args...]
Exit 0: ok / Exit 1: error
"""
import json, os, sys
from common import find_git_root, get_branch, get_task_dir, get_state_dir, ok, error

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(PLUGIN_ROOT, "templates", "fe-task-template.md")
EXAMPLE_PATH = os.path.join(PLUGIN_ROOT, "templates", "fe-task-example.md")



def main():
    args = sys.argv[1:]
    if not args:
        error("MISSING_ARGS", "사용법: preflight.py {skill} [args...]")

    skill = args[0]
    rest = args[1:]

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    branch = get_branch()
    if not branch:
        error("BRANCH_NOT_FOUND", "현재 브랜치를 확인할 수 없습니다")

    task_dir = get_task_dir(root)
    state_dir = get_state_dir(root)

    if skill == "init":
        ok({"branch": branch, "task_dir": task_dir})

    elif skill == "get-template":
        if not os.path.exists(TEMPLATE_PATH):
            error("TEMPLATE_NOT_FOUND", f"템플릿 파일이 없습니다: {TEMPLATE_PATH}")
        data = {"template_path": TEMPLATE_PATH}
        if os.path.exists(EXAMPLE_PATH):
            data["example_path"] = EXAMPLE_PATH
        ok(data)

    elif skill == "fetch":
        ok({"branch": branch, "task_dir": task_dir, "state_dir": state_dir})

    elif skill == "write":
        if not rest:
            error("MISSING_ARGS", "write 스킬에는 이슈 키가 필요합니다. 예: preflight.py write PROJ-101")
        search_path = os.path.join(state_dir, "jira_search.json")
        if not os.path.exists(search_path):
            error("PRECONDITION_FAILED", "jira_search.json이 없습니다. /task-sync:fetch를 먼저 실행하세요.")
        with open(search_path, encoding="utf-8") as f:
            search_data = json.load(f)
        issue_keys = [i.get("key") for i in search_data.get("issues", [])]
        invalid = [k for k in rest if k not in issue_keys]
        if invalid:
            error("NOT_IN_SEARCH", f"조회되지 않은 이슈입니다: {', '.join(invalid)}. fetch에서 조회한 이슈만 처리 가능합니다.")
        ok({"branch": branch, "task_dir": task_dir, "state_dir": state_dir, "issues": rest})

    elif skill == "extract":
        if not os.path.exists(TEMPLATE_PATH):
            error("TEMPLATE_NOT_FOUND", f"템플릿 파일이 없습니다: {TEMPLATE_PATH}")
        ok({"branch": branch, "task_dir": task_dir, "state_dir": state_dir,
            "template_path": TEMPLATE_PATH, "example_path": EXAMPLE_PATH if os.path.exists(EXAMPLE_PATH) else None})

    elif skill == "publish":
        if not os.path.exists(task_dir):
            error("PRECONDITION_FAILED", f"작업 디렉토리가 없습니다: {task_dir}. /task-sync:init을 먼저 실행하세요.")
        unpublished = [
            d for d in os.listdir(task_dir)
            if os.path.isdir(os.path.join(task_dir, d))
            and not os.path.exists(os.path.join(task_dir, d, "published"))
            and os.path.exists(os.path.join(task_dir, d, f"{d}.md"))
        ]
        if not unpublished:
            error("PRECONDITION_FAILED", "게시할 이슈가 없습니다. write 또는 extract를 먼저 실행하세요.")
        ok({"branch": branch, "task_dir": task_dir, "state_dir": state_dir,
            "unpublished": unpublished})

    elif skill == "update":
        if not os.path.exists(task_dir):
            error("PRECONDITION_FAILED", f"작업 디렉토리가 없습니다: {task_dir}")
        # published 마커는 tasks/{issue}/published 에 위치
        import glob as _glob
        published = [
            os.path.basename(os.path.dirname(p))
            for p in _glob.glob(os.path.join(task_dir, "*", "published"))
            if os.path.isfile(p)
        ]
        if not published:
            error("PRECONDITION_FAILED", "PUBLISHED 상태인 이슈가 없습니다. publish를 먼저 실행하세요.")
        ok({"branch": branch, "task_dir": task_dir, "state_dir": state_dir, "published": published})

    else:
        error("UNKNOWN_SKILL", f"알 수 없는 스킬: {skill}")


if __name__ == "__main__":
    main()
