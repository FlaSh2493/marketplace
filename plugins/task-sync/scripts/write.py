#!/usr/bin/env python3
"""
이슈키를 받아 Jira에서 상세 조회 후 마크다운 생성.
Usage:
  python3 write.py PROJ-101 PROJ-102 --task-dir .docs/tasks/ --state-dir .docs/tasks/.state/
Exit 0: 성공
Exit 1: 실패
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from common import find_git_root, get_task_dir, get_state_dir, load_claude_env
from jira_fetch import fetch_issue
from jira_to_md import convert_issue
from assemble_md import assemble

load_claude_env()

SIZE_LIMIT = 52_428_800  # 50 MB


def get_auth_header():
    email = os.environ.get("JIRA_USERNAME")
    token = os.environ.get("JIRA_API_TOKEN")
    if not email or not token:
        return None
    encoded = base64.b64encode(f"{email}:{token}".encode()).decode()
    return f"Basic {encoded}"


def download_attachments(attachments: list, assets_dir: str) -> list[str]:
    """첨부파일 다운로드. 실패해도 이슈 전체를 멈추지 않는다."""
    os.makedirs(assets_dir, exist_ok=True)
    auth = get_auth_header()
    warnings = []
    for att in attachments:
        local_name = att.get("localName", "")
        url = att.get("url", "")
        size = att.get("size", 0)
        if not url or not local_name:
            continue
        if size > SIZE_LIMIT:
            warnings.append(f"⚠ {local_name}: 50MB 초과 — 스킵")
            continue
        try:
            req = urllib.request.Request(url)
            if auth:
                req.add_header("Authorization", auth)
            with urllib.request.urlopen(req, timeout=30) as resp:
                dest = os.path.join(assets_dir, local_name)
                with open(dest, "wb") as f:
                    f.write(resp.read())
        except Exception as e:
            warnings.append(f"⚠ {local_name}: 다운로드 실패 — {e}")
    return warnings


def process_issue(issue_key: str, state_dir: str, task_dir: str) -> dict:
    """이슈 하나를 Jira에서 조회 후 마크다운으로 변환 및 저장. 스레드 안전."""
    os.makedirs(state_dir, exist_ok=True)

    # 1. Jira 상세 조회
    result = fetch_issue(issue_key)
    if not result["ok"]:
        return {"issue": issue_key, "status": "skip", "reason": result["reason"]}

    # 2. raw.json 저장
    raw_path = os.path.join(state_dir, f"{issue_key}_raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(result["data"], f, indent=2, ensure_ascii=False)

    # 3. 마크다운 변환
    cvt = convert_issue(raw_path, state_dir, issue_key)
    if not cvt["ok"]:
        return {"issue": issue_key, "status": "skip", "reason": cvt["reason"]}

    converted_path = cvt["file"]
    with open(converted_path, encoding="utf-8") as f:
        converted = json.load(f)

    # 4. 첨부파일 다운로드
    assets_dir = os.path.join(task_dir, issue_key, "assets")
    warnings = download_attachments(converted.get("attachments", []), assets_dir)

    # 5. md 조립
    md_path = os.path.join(task_dir, issue_key, f"{issue_key}.md")
    asm = assemble(converted_path, md_path, issue_key, assets_dir)
    if not asm["ok"]:
        return {"issue": issue_key, "status": "skip", "reason": asm["reason"]}

    # 6. published 마커
    marker = os.path.join(task_dir, issue_key, "published")
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    with open(marker, "w") as f:
        f.write(json.dumps({"issue": issue_key, "written_at": datetime.now().isoformat()}))

    return {"issue": issue_key, "status": "ok", "warnings": warnings}


def main():
    parser = argparse.ArgumentParser(description="Jira 상세 조회 후 마크다운 생성")
    parser.add_argument("issue_keys", nargs="+", help="처리할 이슈키")
    parser.add_argument("--task-dir", help="tasks 디렉토리 (기본: git root/.docs/tasks)")
    parser.add_argument("--state-dir", help="state 디렉토리 (기본: .docs/tasks/.state)")
    parser.add_argument("--workers", type=int, default=4, help="병렬 워커 수 (기본: 4)")
    args = parser.parse_args()

    root = None
    if not args.task_dir or not args.state_dir:
        import subprocess
        r = subprocess.run("git rev-parse --show-toplevel", shell=True,
                           capture_output=True, text=True)
        root = r.stdout.strip()

    task_dir = args.task_dir or os.path.join(root, ".docs", "tasks")
    state_dir = args.state_dir or os.path.join(root, ".docs", "tasks", ".state")
    jira_json_path = os.path.join(task_dir, "jira.json")

    # jira.json 읽기
    if not os.path.exists(jira_json_path):
        print(f"❌ {jira_json_path} 없음. fetch부터 실행하세요.", file=sys.stderr)
        sys.exit(1)

    with open(jira_json_path, encoding="utf-8") as f:
        search_data = json.load(f)

    issues = search_data.get("issues", [])
    all_keys = [i.get("key") for i in issues]

    # 요청된 이슈 검증
    all_keys = [i.get("key") for i in issues]
    target_keys = []
    for k in args.issue_keys:
        if k in all_keys:
            target_keys.append(k)
        else:
            print(f"⚠ {k}: jira.json에 없음 — 스킵")

    if not target_keys:
        print("처리할 이슈가 없습니다.", file=sys.stderr)
        sys.exit(1)

    print(f"처리 대상: {', '.join(target_keys)}\n")

    # 병렬 처리
    results = []
    with ThreadPoolExecutor(max_workers=min(args.workers, len(target_keys))) as pool:
        futures = {
            pool.submit(process_issue, key, state_dir, task_dir): key
            for key in target_keys
        }
        for future in as_completed(futures):
            results.append(future.result())

    # 결과 출력
    ok_list = [r for r in results if r["status"] == "ok"]
    skip_list = [r for r in results if r["status"] == "skip"]

    for r in ok_list:
        print(f"✓ {r['issue']}")
        for w in r.get("warnings", []):
            print(f"  {w}")
    for r in skip_list:
        print(f"✗ {r['issue']}: {r['reason']}")

    print(f"\n완료: {len(ok_list)}개 성공, {len(skip_list)}개 스킵")

    if not ok_list:
        sys.exit(1)


if __name__ == "__main__":
    main()
