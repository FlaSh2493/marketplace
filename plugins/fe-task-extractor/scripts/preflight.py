#!/usr/bin/env python3
"""
스킬 실행 전 전제조건 검증. 모든 스킬의 STEP 0에서 호출.
Usage: python3 preflight.py {skill} [args...]
Exit 0: ok / Exit 1: error
"""
import json, os, sys, glob

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(PLUGIN_ROOT, "templates", "fe-task-template.md")
EXAMPLE_PATH = os.path.join(PLUGIN_ROOT, "templates", "fe-task-example.md")


def find_git_root():
    import subprocess
    r = subprocess.run("git rev-parse --git-common-dir", shell=True, capture_output=True, text=True)
    common = r.stdout.strip()
    if common:
        return os.path.abspath(os.path.join(common, ".."))
    r2 = subprocess.run("git rev-parse --show-toplevel", shell=True, capture_output=True, text=True)
    return r2.stdout.strip() or None


def get_branch():
    import subprocess
    r = subprocess.run("git rev-parse --abbrev-ref HEAD", shell=True, capture_output=True, text=True)
    return r.stdout.strip() or None


def get_task_dir(root, branch):
    return os.path.join(root, ".docs", "task", branch.replace("/", os.sep))


def get_state_dir(task_dir):
    return os.path.join(task_dir, ".state")


def get_pending_path(state_dir):
    return os.path.join(state_dir, "pending.json")


def load_pending(state_dir):
    path = get_pending_path(state_dir)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_state_files(state_dir, ext):
    if not os.path.exists(state_dir):
        return []
    return [
        os.path.splitext(os.path.basename(f))[0]
        for f in glob.glob(os.path.join(state_dir, f"*.{ext}"))
    ]


def ok(data=None):
    print(json.dumps({"status": "ok", "data": data or {}}, ensure_ascii=False))
    sys.exit(0)


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


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

    task_dir = get_task_dir(root, branch)
    state_dir = get_state_dir(task_dir)

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
        pending = load_pending(state_dir)
        if pending is None:
            error("PRECONDITION_FAILED", "pending.json이 없습니다. /fe-task-extractor:fetch를 먼저 실행하세요.")
        selected = pending.get("selected", [])
        invalid = [k for k in rest if k not in selected]
        if invalid:
            error("NOT_SELECTED", f"선택되지 않은 이슈입니다: {', '.join(invalid)}. fetch에서 선택한 이슈만 처리 가능합니다.")
        ok({"branch": branch, "task_dir": task_dir, "state_dir": state_dir, "issues": rest})

    elif skill == "extract":
        if not os.path.exists(TEMPLATE_PATH):
            error("TEMPLATE_NOT_FOUND", f"템플릿 파일이 없습니다: {TEMPLATE_PATH}")
        ok({"branch": branch, "task_dir": task_dir, "state_dir": state_dir,
            "template_path": TEMPLATE_PATH, "example_path": EXAMPLE_PATH if os.path.exists(EXAMPLE_PATH) else None})

    elif skill == "publish":
        if not os.path.exists(task_dir):
            error("PRECONDITION_FAILED", f"작업 디렉토리가 없습니다: {task_dir}. /fe-task-extractor:init을 먼저 실행하세요.")
        drafts = list_state_files(state_dir, "draft")
        if not drafts:
            error("PRECONDITION_FAILED", "DRAFT 상태인 이슈가 없습니다. extract 또는 fetch를 먼저 실행하세요.")
        ok({"branch": branch, "task_dir": task_dir, "state_dir": state_dir, "drafts": drafts})

    elif skill == "update":
        if not os.path.exists(task_dir):
            error("PRECONDITION_FAILED", f"작업 디렉토리가 없습니다: {task_dir}")
        published = list_state_files(state_dir, "published")
        if not published:
            error("PRECONDITION_FAILED", "PUBLISHED 상태인 이슈가 없습니다. publish를 먼저 실행하세요.")
        ok({"branch": branch, "task_dir": task_dir, "state_dir": state_dir, "published": published})

    else:
        error("UNKNOWN_SKILL", f"알 수 없는 스킬: {skill}")


if __name__ == "__main__":
    main()
