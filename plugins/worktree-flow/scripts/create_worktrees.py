#!/usr/bin/env python3
"""
피처 브랜치에서 워크트리를 일괄 생성한다.
Usage: python3 create_worktrees.py {피처브랜치} {작업1} {작업2} ...
"""
import argparse, json, os, subprocess, sys, re

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def find_git_root():
    # git-common-dir를 통해 메인 저장소의 .git 경로를 찾고 그 상위 디렉토리를 반환
    common_dir, _, _ = run("git rev-parse --git-common-dir")
    if common_dir:
        return os.path.abspath(os.path.join(common_dir, ".."))
    out, _, _ = run("git rev-parse --show-toplevel")
    return out or None

def get_current_branch(root):
    out, _, _ = run("git rev-parse --abbrev-ref HEAD", cwd=root)
    return out

def get_tasks_from_md(root, feature):
    # 브랜치명의 '/'를 폴더 구조로 변환하여 탐색
    parts = feature.lower().split('/')
    sub_dirs = [p.strip().replace(' ', '-') for p in parts[:-1]]
    filename = f"{parts[-1].strip().replace(' ', '-')}.md"
    
    paths = [
        os.path.join(root, ".docs", "task", *sub_dirs, filename),
        os.path.join(root, "docs", "task", *sub_dirs, filename),
        # 기존 평면 구조 하위 호환성
        os.path.join(root, ".docs", "task", f"{feature.replace('/', '-')}.md"),
        os.path.join(root, "docs", "task", f"{feature.replace('/', '-')}.md")
    ]
    tasks = []
    for path in paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                # Jira 이슈 번호 패턴 (예: PLAT-123) 찾기
                matches = re.findall(r"([A-Z]+-[0-9]+)", content)
                for m in matches:
                    if m not in tasks: tasks.append(m)
    return tasks

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feature", nargs="?", default=".")
    parser.add_argument("tasks", nargs="*")
    parser.add_argument("--root", default=None)
    args = parser.parse_args()

    root = args.root or find_git_root()
    if not root:
        print(json.dumps({"error": "Git 루트를 찾을 수 없습니다"})); sys.exit(1)

    # 피처 브랜치 결정 ('.' 이면 현재 브랜치 사용)
    feature = args.feature
    if feature == ".":
        feature = get_current_branch(root)
    
    # 작업 목록 결정
    tasks = args.tasks
    if not tasks:
        tasks = get_tasks_from_md(root, feature)
        if not tasks:
            print(json.dumps({
                "error": f"'.docs/task/{feature}.md' 파일에서 이슈 번호를 찾을 수 없고, 인자로도 전달되지 않았습니다.",
                "feature": feature
            }, ensure_ascii=False))
            sys.exit(1)
        
        # 아직 선택되지 않은 경우 목록을 반환하여 에이전트가 선택하게 함
        print(json.dumps({
            "mode": "selection",
            "feature": feature,
            "tasks": tasks,
            "message": f"'{feature}' 관련 문서에서 발견된 이슈들입니다. 워크트리를 생성할 이슈를 선택해 주세요."
        }, ensure_ascii=False, indent=2))
        return

    # 피처 브랜치 확인/생성
    out, _, _ = run(f"git branch --list '{feature}'", cwd=root)
    if not out:
        run("git fetch upstream", cwd=root)
        base, _, _ = run("git rev-parse upstream/main 2>/dev/null || git rev-parse upstream/develop 2>/dev/null || git rev-parse origin/main", cwd=root)
        if not base:
            print(json.dumps({"error": "base 브랜치를 찾을 수 없습니다"})); sys.exit(1)
        run(f"git branch '{feature}' {base}", cwd=root)

    wt_base = os.path.join(root, ".worktrees")
    os.makedirs(wt_base, exist_ok=True)

    results, errors = [], []
    for task in tasks:
        branch = f"{feature}--wt-{task}"
        wt_path = os.path.join(wt_base, task)

        if os.path.exists(wt_path):
            errors.append({"name": task, "error": f"경로 존재: {wt_path}"})
            continue

        existing, _, _ = run(f"git branch --list '{branch}'", cwd=root)
        if existing:
            _, err, _ = run(f"git worktree add '{wt_path}' '{branch}'", cwd=root)
        else:
            _, err, _ = run(f"git worktree add -b '{branch}' '{wt_path}' '{feature}'", cwd=root)

        if err and "already" not in err.lower():
            errors.append({"name": task, "error": err})
        else:
            results.append({"name": task, "branch": branch, "path": wt_path})

    output = {"feature": feature, "root": root, "worktrees": results}
    if errors:
        output["errors"] = errors
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
