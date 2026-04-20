#!/usr/bin/env python3
"""
autopilot:build 실행 전 컨텍스트를 도출한다.
1. 브랜치/워크트리 가용성 확인 (ensure_worktree.py 활용)
2. stale handoff 감지 및 resume 모드 판정
3. 비-resume 모드인 경우에만 상태 초기화 (state_manager.py reset build)
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
        except Exception:
            print(json.dumps({"status": "error", "reason": err or out}, ensure_ascii=False))
        sys.exit(1)

    data = json.loads(out)["data"]

    # 3. handoff 검증
    handoff_script = os.path.join(script_dir, "build_handoff.py")
    issue = data["issue"]
    validate_cmd = (
        f"python3 {handoff_script} validate "
        f"--branch {data['branch']} --worktree {data['worktree_path']} --issue {issue}"
    )
    v_out, v_err, v_rc = run_command(validate_cmd)

    resume = False
    resume_stale = False
    stale_reason = ""

    if v_rc == 0:
        try:
            v_res = json.loads(v_out)
            if v_res["status"] == "ok":
                resume = True
            elif v_res["status"] == "stale":
                resume_stale = True
                stale_reason = v_res.get("reason", "unknown mismatch")
        except Exception:
            pass

    data["resume"] = resume
    data["resume_stale"] = resume_stale
    data["stale_reason"] = stale_reason

    # 4. 상태 초기화 (Resume 모드가 아닐 때만 reset build 수행)
    if not resume:
        state_script = os.path.join(script_dir, "state_manager.py")
        run_command(f"python3 {state_script} reset build --issue {issue}")

    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))

if __name__ == "__main__":
    main()
