#!/usr/bin/env python3
"""
워크트리 작업을 시작하기 위해 기획 정보를 로드한다.
Usage: python3 start_worktree.py
"""
import argparse, json, os, subprocess, sys, re

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.returncode

def find_git_root():
    # git-common-dir를 통해 메인 저장소의 .git 경로를 찾고 그 상위 디렉토리를 반환
    common_dir, _ = run("git rev-parse --git-common-dir")
    if common_dir:
        return os.path.abspath(os.path.join(common_dir, ".."))
    out, _ = run("git rev-parse --show-toplevel")
    return out or None

def get_current_branch():
    out, _ = run("git rev-parse --abbrev-ref HEAD")
    return out

def parse_worktrees(root):
    out, _ = run("git worktree list --porcelain", cwd=root)
    worktrees, current = [], {}
    for line in out.split("\n"):
        if line.startswith("worktree "):
            if current: worktrees.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1].replace("refs/heads/", "")
    if current: worktrees.append(current)
    return worktrees

def extract_task_info(branch):
    # feat/{feature}--wt-{issue} 형식 파싱
    if "--wt-" in branch:
        parts = branch.split("--wt-")
        feature = parts[0].replace("feat/", "")
        issue = parts[1]
        return feature, issue
    return None, None

def find_description_in_md(root, feature, issue):
    # .docs/task/{feature}.md 또는 {feature}.md 탐색
    paths = [
        os.path.join(root, ".docs", "task", f"{feature}.md"),
        os.path.join(root, "docs", "task", f"{feature}.md"),
        os.path.join(root, ".docs", "task", f"{feature.replace('/', '-')}.md")
    ]
    
    for path in paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                # 이슈 번호(예: PLAT-123)가 포함된 섹션 찾기
                # ## [PLAT-123] 제목 또는 유사한 형식 탐색
                pattern = rf"(?i)(###?.*{re.escape(issue)}.*(?:\n|$).*?)(?=\n###?|$)"
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    return match.group(0).strip(), path
                
                # 섹션으로 못 찾으면 전체 파일에서 해당 이슈 번호 근처 텍스트라도 반환
                if issue in content:
                    return f"정확한 섹션을 찾지 못했지만, 파일 내에 {issue}가 언급되어 있습니다.\n파일 경로: {path}", path
                    
    return None, None

def main():
    root = find_git_root()
    if not root:
        print(json.dumps({"error": "Git 루트를 찾을 수 없습니다"})); sys.exit(1)

    current_branch = get_current_branch()
    feature, issue = extract_task_info(current_branch)

    # 워크트리 내부가 아니거나 정보가 부족한 경우 목록 표시 모드
    if not feature or not issue:
        worktrees = parse_worktrees(root)
        active_wts = [w for w in worktrees if "--wt-" in w.get("branch", "")]
        
        if not active_wts:
            print(json.dumps({"message": "활성화된 워크트리가 없습니다. 메인 브랜치에서 작업 중이거나 브랜치 형식이 다릅니다.", "branch": current_branch}))
            return

        # 선택 UI를 위한 목록 반환
        print(json.dumps({
            "mode": "selection",
            "worktrees": active_wts,
            "message": "작업할 워크트리를 선택해 주세요."
        }, ensure_ascii=False, indent=2))
        return

    # 정보 추출 시도
    desc, file_path = find_description_in_md(root, feature, issue)
    
    result = {
        "mode": "auto",
        "feature": feature,
        "issue": issue,
        "branch": current_branch,
        "description": desc,
        "file_path": file_path
    }

    if not desc:
        result["message"] = f"로컬 문서(.docs/task/{feature}.md)에서 {issue} 정보를 찾을 수 없습니다. Jira 조회가 필요합니다."
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
