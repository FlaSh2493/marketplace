#!/usr/bin/env python3
"""
autopilot 커스텀 지침 로더
프로젝트 루트의 .autopilot-instructions/ 디렉토리에서 지침을 읽어 안정적으로 제공한다.
"""
import os, subprocess, sys
from pathlib import Path

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def find_main_root():
    """워크트리 내에서도 메인 레포지토리 루트를 반환한다."""
    out, _, rc = run("git rev-parse --path-format=absolute --git-common-dir")
    if rc == 0 and out:
        # --git-common-dir는 보통 .git 디렉토리를 가리키므로 부모인 프로젝트 루트 반환
        p = Path(out)
        if p.name == ".git":
            return str(p.parent)
        return str(p)
    # fallback
    out, _, rc = run("git rev-parse --show-toplevel")
    return out if rc == 0 else None

def main():
    if len(sys.argv) < 2:
        print("Usage: load_custom_instructions.py <skill_name|--all>")
        sys.exit(1)

    target = sys.argv[1]
    root = find_main_root()
    if not root:
        # Git 외부인 경우 현재 디렉토리 기준 탐색
        root = os.getcwd()

    instr_dir = Path(root) / ".autopilot-instructions"
    if not instr_dir.exists():
        # 지침 폴더가 없으면 조용히 종료
        sys.exit(0)

    found_any = False
    
    # 1. 공통 지침 (common.md) 로드
    common_file = instr_dir / "common.md"
    if common_file.exists():
        print(f"\n[COMMON PROJECT INSTRUCTIONS]")
        print(common_file.read_text())
        found_any = True

    # 2. 특정 스킬 지침 로드
    skills_to_load = []
    if target == "--all":
        # 모든 마크다운 파일 로드 (common.md 제외)
        skills_to_load = [f.stem for f in instr_dir.glob("*.md") if f.stem != "common"]
    else:
        skills_to_load = [target]

    for skill in skills_to_load:
        skill_file = instr_dir / f"{skill}.md"
        if skill_file.exists():
            print(f"\n[CUSTOM INSTRUCTIONS FOR {skill.upper()}]")
            print(skill_file.read_text())
            found_any = True

    if found_any:
        print("\n" + "="*60)
        print("위 지침은 본 프로젝트의 필수 제약 사항입니다. 표준 절차를 왜곡하지 않는 범위 내에서 무조건 반영하십시오.")
        print("="*60 + "\n")

if __name__ == "__main__":
    main()
