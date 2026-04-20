#!/usr/bin/env python3
"""
레거시 tasks/.state/ 구조를 새로운 이슈 폴더 구조로 마이그레이션한다.
- tasks/.state/build-handoff.json → tasks/{issue}/build-handoff.json
- tasks/.state/archive/*.json → tasks/{issue}/archive/
- tasks/.state/{이슈키}.published → tasks/{이슈키}/published
- .autopilot 메타의 issues[] → issue 단일값

Usage: python3 migrate_state.py [--dry-run]
"""
import json, os, shutil, sys
from datetime import datetime
from pathlib import Path


def find_git_root():
    import subprocess
    r = subprocess.run("git rev-parse --git-common-dir", shell=True, capture_output=True, text=True)
    common = r.stdout.strip()
    if common:
        return os.path.abspath(os.path.join(common, ".."))
    r2 = subprocess.run("git rev-parse --show-toplevel", shell=True, capture_output=True, text=True)
    return r2.stdout.strip() or None


def migrate(dry_run=False):
    root = find_git_root()
    if not root:
        print("error: git root를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    tasks_dir = Path(root) / "tasks"
    state_dir = tasks_dir / ".state"
    moved = []
    skipped = []
    warnings = []

    # 1. build-handoff.json → tasks/{issue}/build-handoff.json
    handoff_path = state_dir / "build-handoff.json"
    if handoff_path.exists():
        try:
            data = json.loads(handoff_path.read_text())
            issue = data.get("issue") or (data.get("issues") or [""])[0]
            if issue:
                dest = tasks_dir / issue / "build-handoff.json"
                print(f"  [handoff] {handoff_path} → {dest}")
                if not dry_run:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(handoff_path), str(dest))
                moved.append(str(handoff_path))
            else:
                warnings.append(f"build-handoff.json에서 issue를 식별할 수 없어 건너뜁니다.")
        except Exception as e:
            warnings.append(f"build-handoff.json 처리 실패: {e}")

    # 2. tasks/.state/archive/*.json → tasks/{issue}/archive/
    archive_dir = state_dir / "archive"
    if archive_dir.exists():
        for f in sorted(archive_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                issue = data.get("issue") or (data.get("issues") or [""])[0]
                if issue:
                    dest_dir = tasks_dir / issue / "archive"
                    dest = dest_dir / f.name
                    print(f"  [archive] {f} → {dest}")
                    if not dry_run:
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(f), str(dest))
                    moved.append(str(f))
                else:
                    warnings.append(f"archive/{f.name}: issue 식별 불가, 건너뜀")
            except Exception as e:
                warnings.append(f"archive/{f.name} 처리 실패: {e}")

    # 3. tasks/.state/{이슈키}.published → tasks/{이슈키}/published
    if state_dir.exists():
        for f in sorted(state_dir.glob("*.published")):
            issue = f.stem
            dest = tasks_dir / issue / "published"
            print(f"  [marker]  {f} → {dest}")
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(dest))
            moved.append(str(f))

    # 4. .autopilot 메타 issues[] → issue 단일값
    import subprocess
    wt_out = subprocess.run(
        "git worktree list --porcelain", shell=True, capture_output=True, text=True
    ).stdout.strip()
    worktree_paths = []
    for line in wt_out.splitlines():
        if line.startswith("worktree "):
            worktree_paths.append(line[9:].strip())

    for wt_path in worktree_paths:
        meta_path = Path(wt_path) / ".autopilot"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
            if "issues" in meta and "issue" not in meta:
                issues_list = meta.get("issues", [])
                if len(issues_list) > 1:
                    warnings.append(
                        f"{meta_path}: issues가 {len(issues_list)}개입니다 ({', '.join(issues_list)}). "
                        f"첫 번째({issues_list[0]})로 변환합니다. 나머지는 수동 확인 필요."
                    )
                new_issue = issues_list[0] if issues_list else ""
                meta["issue"] = new_issue
                del meta["issues"]
                print(f"  [meta]    {meta_path}: issues{issues_list} → issue={new_issue!r}")
                if not dry_run:
                    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
                moved.append(str(meta_path))
        except Exception as e:
            warnings.append(f"{meta_path} 처리 실패: {e}")

    print()
    print(f"완료: {len(moved)}개 처리, {len(warnings)}개 경고")
    for w in warnings:
        print(f"  ⚠ {w}")
    if dry_run:
        print("\n(dry-run 모드: 실제 변경 없음)")


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=== Dry-run 모드 (변경 없이 확인만) ===\n")
    else:
        print("=== 마이그레이션 실행 ===\n")
    migrate(dry_run=dry_run)


if __name__ == "__main__":
    main()
