#!/usr/bin/env python3
"""
cruise 설정 관리 스크립트 (대화형).

**단일 파일** `~/.config/cruise/config.json` 하나만 관리한다. 토큰(비밀)은 이 파일의
`credentials` 블록에, 팀 공통값은 `settings` 블록에 저장되며, 파일은 600 권한 + 레포 밖 +
.gitignore 로 보호된다.

서브커맨드:
  (없음) / set        전체 값을 하나씩 대화형 입력 (Enter=기존값 유지)
  set KEY             특정 값 하나만 수정
  show                현재 설정 상태 표시 (비밀값은 마스킹)
  delete KEY          특정 값 삭제
  delete --all        config.json 파일 전체 삭제

KEY: email | jira_api_token | base_url | default_project

⚠️ Claude Code의 비대화형 Bash에서는 실행하지 말 것(stdin이 없어 실패).
   반드시 사용자 터미널에서 실행한다. stdlib만 사용하므로 venv 설치 전에도 동작한다.
"""

import argparse
import getpass
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common import CONFIG_PATH, STATE_DIR  # noqa: E402

# (키, 블록, 라벨, 비밀?, 선택?, 도움말)
FIELDS = [
    ("email", "credentials", "Jira 이메일", False, False, None),
    ("jira_api_token", "credentials", "Jira API 토큰", True, False,
     "발급: https://id.atlassian.com/manage-profile/security/api-tokens"),
    ("base_url", "settings", "Jira 베이스 URL", False, True,
     "선택 — 기본값 https://madup.atlassian.net"),
    ("default_project", "settings", "기본 프로젝트 키", False, True,
     "선택 — plan 신규 이슈 생성용(예: IET). 없으면 create 비활성."),
]
KNOWN = [f[0] for f in FIELDS]
REQUIRED = [f[0] for f in FIELDS if not f[4]]
META = {f[0]: f for f in FIELDS}
BLOCKS = ("credentials", "settings")


def _keys_of(block: str) -> list:
    return [f[0] for f in FIELDS if f[1] == block]


def _read() -> dict:
    """config.json 전체를 dict로 로드. 파일이 있는데 읽을 수 없으면 **중단**(덮어쓰기 방지)."""
    if not CONFIG_PATH.is_file():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"❌ 기존 설정을 읽을 수 없습니다: {CONFIG_PATH}\n   ({e})")
        print("   덮어쓰면 기존 자격증명·설정이 유실될 수 있어 중단합니다. 파일을 고치거나 백업 후 삭제하세요.")
        sys.exit(1)
    if not isinstance(data, dict):
        print(f"❌ {CONFIG_PATH} 최상위가 JSON 객체가 아닙니다 — 덮어쓰기 방지를 위해 중단합니다.")
        sys.exit(1)
    return data


def _write(cfg: dict) -> None:
    """config.json 원자적 저장 — 처음부터 0600 임시파일에 쓰고 os.replace.

    write 후 chmod 방식은 umask 022에서 잠깐 0644로 노출되므로, mkstemp(0600) + replace 사용.
    각 블록에서 빈 값은 정리하고, 빈 블록은 통째로 제거한다.
    """
    for block in BLOCKS:
        vals = cfg.get(block) or {}
        pruned = {k: vals[k] for k in _keys_of(block) if vals.get(k)}
        if pruned:
            cfg[block] = pruned
        else:
            cfg.pop(block, None)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(STATE_DIR), prefix=".config.", suffix=".tmp")
    try:
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)  # 0600 (mkstemp도 0600이지만 명시)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, CONFIG_PATH)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _mask(key: str, val: str) -> str:
    if not val:
        return "없음"
    if META[key][3]:  # 비밀
        tail = val[-2:] if len(val) >= 2 else ""
        return f"설정됨 (****{tail})"
    return val


def _prompt_one(key: str, current: str) -> str:
    _, _, label, secret, optional, help_ = META[key]
    if help_:
        print(f"  · {help_}")
    state = "설정됨" if current else "없음"
    tag = " [선택]" if optional else ""
    msg = f"{label} [{key}]{tag} (현재: {state}) — 새 값 입력(Enter=유지): "
    val = getpass.getpass(msg) if secret else input(msg).strip()
    return val or current


def cmd_set(args) -> None:
    if args.key and args.key not in KNOWN:
        print(f"❌ 알 수 없는 키: {args.key} (가능: {', '.join(KNOWN)})")
        sys.exit(1)
    cfg = _read()
    blocks = {b: dict(cfg.get(b) or {}) for b in BLOCKS}
    keys = [args.key] if args.key else KNOWN
    print(f"저장 위치: {CONFIG_PATH}")
    print("비밀값은 입력해도 화면에 표시되지 않습니다.\n")
    for k in keys:
        block = META[k][1]
        blocks[block][k] = _prompt_one(k, blocks[block].get(k, ""))
    for b in BLOCKS:
        cfg[b] = blocks[b]
    _write(cfg)
    missing = [k for k in REQUIRED if not blocks[META[k][1]].get(k)]
    print(f"\n✅ 저장 완료: {CONFIG_PATH} (권한 600)")
    if missing:
        print(f"⚠️ 필수 값 미설정: {', '.join(missing)} — 설정 전엔 스킬이 동작하지 않습니다.")


def cmd_show(args) -> None:
    cfg = _read()
    exists = "있음" if CONFIG_PATH.is_file() else "없음"
    print(f"설정 파일: {CONFIG_PATH} ({exists})")
    for block in BLOCKS:
        vals = cfg.get(block) or {}
        print(f"[{block}]")
        for k in _keys_of(block):
            opt = " [선택]" if META[k][4] else ""
            print(f"  {k}{opt}: {_mask(k, vals.get(k, ''))}")


def cmd_delete(args) -> None:
    if args.all:
        if CONFIG_PATH.is_file():
            CONFIG_PATH.unlink()
            print(f"🗑️  config.json 전체 삭제: {CONFIG_PATH}")
        else:
            print("이미 config.json 이 없습니다.")
        return
    if not args.key:
        print("❌ 삭제할 키를 지정하거나 --all 을 쓰세요.")
        sys.exit(1)
    if args.key not in KNOWN:
        print(f"❌ 알 수 없는 키: {args.key} (가능: {', '.join(KNOWN)})")
        sys.exit(1)
    cfg = _read()
    block = META[args.key][1]
    vals = dict(cfg.get(block) or {})
    if args.key in vals:
        del vals[args.key]
        cfg[block] = vals
        _write(cfg)
        print(f"🗑️  키 삭제: {args.key}")
        if args.key in REQUIRED:
            print(f"⚠️ {args.key} 는 필수 — 다시 설정하기 전엔 스킬이 동작하지 않습니다.")
    else:
        print(f"{args.key} 는 설정돼 있지 않습니다.")


def main() -> None:
    parser = argparse.ArgumentParser(description="cruise 설정 관리 (단일 config.json)")
    sub = parser.add_subparsers(dest="command")

    p_set = sub.add_parser("set", help="전체 또는 특정 키를 대화형 설정")
    p_set.add_argument("key", nargs="?", help=f"수정할 키 (생략 시 전체). 가능: {', '.join(KNOWN)}")

    sub.add_parser("show", help="현재 설정 상태 표시 (비밀값 마스킹)")

    p_del = sub.add_parser("delete", help="특정 키 또는 전체(config.json) 삭제")
    p_del.add_argument("key", nargs="?", help="삭제할 키")
    p_del.add_argument("--all", action="store_true", help="config.json 파일 전체 삭제")

    args = parser.parse_args()
    if args.command == "show":
        cmd_show(args)
    elif args.command == "delete":
        cmd_delete(args)
    else:  # set 또는 서브커맨드 없음
        if args.command is None:
            args.key = None
        cmd_set(args)


if __name__ == "__main__":
    main()
