#!/usr/bin/env python3
"""
autopilot:build 실행 전 컨텍스트를 도출한다.
1. 브랜치/워크트리 가용성 확인 (ensure_worktree.py 활용)
2. 상태 초기화 (state_manager.py reset build)
3. handoff 파일 존재 여부로 resume 모드 판정
"""
import json, os, subprocess, sys
from pathlib import Path

def run_command(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def main():
    args = sys.argv[1:]
    branch = args[0] if args else None
    
    # 1. 브랜치 확보
    if not branch:
        branch, _, rc = run_command("git branch --show-current")
        if rc != 0 or not branch:
            # fallback to git rev-parse for detached HEAD
            branch, _, rc = run_command("git rev-parse --abbrev-ref HEAD")
    
    if not branch or branch == "HEAD":
        print(json.dumps({"status": "error", "reason": "브랜치를 식별할 수 없습니다. /autopilot:build {브랜치} 를 명시하세요."}, ensure_ascii=False))
        sys.exit(1)

    # 2. ensure_worktree.py 호출
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ensure_script = os.path.join(script_dir, "ensure_worktree.py")
    
    cmd = f"python3 {ensure_script} {branch}"
    out, err, rc = run_command(cmd)
    
    if rc != 0:
        try:
            res = json.loads(out)
            print(json.dumps(res, ensure_ascii=False))
        except:
            print(json.dumps({"status": "error", "reason": err or out}, ensure_ascii=False))
        sys.exit(1)
    
    data = json.loads(out)["data"]
    
    # 3. 상태 초기화 (최초 실행/재시작 상관없이 reset build만 수행 - build.* 마커 제거)
    state_script = os.path.join(script_dir, "state_manager.py")
    run_command(f"python3 {state_script} reset build")
    
    # 4. handoff 파일 존재 확인으로 resume 판정
    handoff_path = Path(data["issue_doc_root"]) / "tasks" / ".state" / "build-handoff.json"
    data["resume"] = handoff_path.exists()
    
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))

if __name__ == "__main__":
    main()
