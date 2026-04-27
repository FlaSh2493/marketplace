#!/usr/bin/env python3
"""
단순한 변경사항을 자동으로 커밋하여 토큰 비용을 절감한다.
Usage: python3 auto_commit.py --worktree {path} --scope {scope}
"""
import argparse
import json
import os
import subprocess
import sys

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--scope", required=True)
    args = parser.parse_args()

    wt = args.worktree
    scope = args.scope

    # 1. 변경 파일 목록 및 상태 확인
    # porcelain v1: XY PATH 또는 XY "PATH"
    out, _, _ = run("git status --porcelain", cwd=wt)
    if not out:
        print(json.dumps({"status": "empty"}, ensure_ascii=False))
        return

    lines = out.splitlines()
    files = []
    for line in lines:
        if len(line) < 4: continue
        # XY PATH -> PATH는 3번 인덱스부터 시작
        f = line[3:].strip()
        if f.startswith('"') and f.endswith('"'):
            # TODO: handle escaped quotes if necessary, but strip simple ones
            f = f[1:-1]
        files.append(f)
    
    # 2. 자동 커밋 제약 조건 검사
    if len(files) > 5:
        print(json.dumps({"status": "needs_manual", "reason": "TOO_MANY_FILES", "count": len(files)}, ensure_ascii=False))
        return

    # 3. 변경 패턴 분석 (단일 디렉토리 여부 등)
    dirs = set()
    for f in files:
        d = os.path.dirname(f)
        if not d: d = "."
        # 최상위 디렉토리만 추출
        top_dir = d.split("/")[0]
        dirs.add(top_dir)

    # 4. 타입 및 요약 결정
    ctype = "feat" # 기본값
    if all(f.endswith((".md", ".txt", ".json", ".yaml", ".yml")) for f in files):
        ctype = "docs"
    elif any(f.startswith("tests/") or f.endswith(("_test.py", ".test.ts")) for f in files):
        ctype = "test"
    
    if len(dirs) == 1:
        dir_name = list(dirs)[0]
        summary = f"updates in {dir_name}" if dir_name != "." else "minor updates"
    else:
        summary = f"updates in {', '.join(files)}" if len(files) <= 2 else f"updates across {len(dirs)} modules"

    # 5. 커밋 메시지 생성 및 실행
    subject = f"{ctype}({scope}): {summary}"
    body = "Auto-committed by autopilot (simple changes detection)."
    
    # Template 기반 형식 맞추기
    full_msg = f"{subject}\n\n{body}\n\n---\n- Requirements: Auto-sync/commit simple changes\n- Changes: {', '.join(files)}\n- Notes: none"
    
    # 신규 파일 포함을 위해 먼저 add
    run("git add -A", cwd=wt)

    # 커밋 실행
    process = subprocess.Popen(
        ["git", "commit", "-F", "-"],
        cwd=wt,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(input=full_msg)
    
    if process.returncode == 0:
        print(json.dumps({"status": "committed", "data": {"subject": subject, "files": files}}, ensure_ascii=False, indent=2))
    else:
        # 이미 스테이징된게 없는 경우 등
        if "nothing to commit" in stdout or "nothing to commit" in stderr:
             print(json.dumps({"status": "empty"}, ensure_ascii=False))
        else:
             print(json.dumps({"status": "error", "reason": f"COMMIT_FAILED: {stderr.strip() or stdout.strip()}"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
