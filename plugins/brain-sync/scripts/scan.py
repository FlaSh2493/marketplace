#!/usr/bin/env python3
"""cruise task 저장소 인벤토리 + 매니페스트 diff.

각 task 디렉토리의 산출물·source_hash 를 계산하고 매니페스트와 비교해
new / changed / unchanged / no_result 로 분류한다. 쓰기 없음.

Usage:
  python3 scan.py [--jira-only]
Output: JSON {tasks_root, brain_root, total, counts, tasks:[...]}
"""
import json
import sys
from pathlib import Path

import common as C
import manifest as M

ALL_ARTIFACTS = ["task", "plan", "build", "summary", "check",
                 "commit", "merge", "pr", "review", "result"]


def classify(key: str, src_hash: str, has_result: bool, mtasks: dict) -> str:
    entry = mtasks.get(key)
    if entry is None:
        return "new"
    if entry.get("source_hash") != src_hash:
        return "changed"
    return "unchanged"


def main():
    jira_only = "--jira-only" in sys.argv
    troot = C.tasks_root()
    m = M.load_manifest()
    mtasks = m["tasks"]

    tasks = []
    if troot.exists():
        for d in sorted(troot.iterdir()):
            if not d.is_dir():
                continue
            key = d.name
            if jira_only and not C.is_jira_key(key):
                continue
            present = [a for a in ALL_ARTIFACTS if (d / f"{a}.md").exists()]
            if not present:
                continue  # 빈 디렉토리 / 산출물 없음
            has_result = "result" in present
            src = C.source_hash(d)
            status = classify(key, src, has_result, mtasks)
            tasks.append({
                "key": key,
                "is_jira": C.is_jira_key(key),
                "status": status,
                "has_result": has_result,
                "artifacts": present,
                "source_hash": src,
            })

    counts = {"new": 0, "changed": 0, "unchanged": 0, "no_result": 0}
    for t in tasks:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
        if not t["has_result"]:
            counts["no_result"] += 1

    print(json.dumps({
        "tasks_root": str(troot),
        "brain_root": str(C.brain_root()),
        "contract_version": C.CONTRACT_VERSION,
        "total": len(tasks),
        "counts": counts,
        "tasks": tasks,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
