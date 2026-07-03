#!/usr/bin/env python3
"""한 task의 사실 추출 — 결정적 부분만. LLM은 이 출력을 받아 node plan을 만든다.

두 가지 task.md 형태(jsync/Jira, cruise-inline)를 감지해 정체성을 읽고,
실행 사실은 cruise 산출물에서, 회고는 result.md 고정 H2에서 파싱한다.

Usage: python3 extract.py <KEY>
Output: JSON {key, identity, execution, result, existing_patterns, existing_technologies}
"""
import json
import sys
from pathlib import Path

import common as C


def load_fm(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        fm, _ = C.split_frontmatter(path.read_text(encoding="utf-8"))
        return fm or {}
    except Exception:
        return C.parse_frontmatter_scalars(path)


def load_body(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        _, body = C.split_frontmatter(path.read_text(encoding="utf-8"))
        return body
    except Exception:
        return ""


def parse_sections(body: str) -> dict:
    """## 헤딩별로 내용을 모은다. {heading: {text, bullets[]}}."""
    sections = {}
    cur = None
    buf = []

    def flush():
        if cur is None:
            return
        text = "\n".join(buf).strip()
        bullets = [ln.strip()[2:].strip() for ln in buf
                   if ln.strip().startswith("- ") and ln.strip()[2:].strip()
                   and ln.strip()[2:].strip() != "없음"]
        sections[cur] = {"text": text, "bullets": bullets}

    for line in body.splitlines():
        if line.startswith("## "):
            flush()
            cur = line[3:].strip()
            buf = []
        elif cur is not None:
            buf.append(line)
    flush()
    return sections


def detect_identity(task_fm: dict) -> dict:
    is_inline = task_fm.get("skill") == "task" or task_fm.get("source") == "cruise-inline"
    return {
        "key": task_fm.get("key", ""),
        "summary": task_fm.get("summary", ""),
        "shape": "cruise-inline" if is_inline else "jira",
        "jira_status": None if is_inline else task_fm.get("status"),
        "issuetype": task_fm.get("issuetype"),
        "parent": task_fm.get("parent")
                  or (task_fm.get("customfields", {}) or {}).get("epic_link"),
        "tags": task_fm.get("tags", []) if isinstance(task_fm.get("tags"), list) else [],
    }


def section_get(sections: dict, *names) -> dict:
    for n in names:
        if n in sections:
            return sections[n]
    return {"text": "", "bullets": []}


def vault_slugs(node_type: str) -> list:
    d = C.node_dir(node_type)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.md"))


def extract_facts(key: str) -> dict:
    tdir = C.tasks_root() / key
    task_fm = load_fm(tdir / "task.md")
    plan_fm = load_fm(tdir / "plan.md")
    summary_fm = load_fm(tdir / "summary.md")
    pr_fm = load_fm(tdir / "pr.md")
    commit_fm = load_fm(tdir / "commit.md")
    result_fm = load_fm(tdir / "result.md")

    identity = detect_identity(task_fm)
    if not identity["key"]:
        identity["key"] = key

    def first(field, fms):
        for fm in fms:
            v = fm.get(field)
            if v:
                return v
        return ""

    cruise_fms = [result_fm, plan_fm, summary_fm, commit_fm, pr_fm]
    branch = first("branch", cruise_fms)
    repo = first("repo", cruise_fms)
    base_branch = first("base_branch", [result_fm, summary_fm, pr_fm])

    execution = {
        "branch": branch,
        "repo": repo,
        "base_branch": base_branch,
        "pr_url": result_fm.get("pr_url") or pr_fm.get("pr_url", "") or "",
        "pr_number": result_fm.get("pr_number") or pr_fm.get("pr_number"),
        "commits_count": result_fm.get("commits_count")
                         or commit_fm.get("commits_count") or 0,
        "files_changed": summary_fm.get("files_changed"),
        "insertions": summary_fm.get("insertions"),
        "deletions": summary_fm.get("deletions"),
    }

    has_result = (tdir / "result.md").exists()
    rbody = load_body(tdir / "result.md")
    sections = parse_sections(rbody)
    sbody = load_body(tdir / "summary.md")
    ssections = parse_sections(sbody)

    technologies = result_fm.get("technologies", [])
    if not isinstance(technologies, list):
        technologies = []

    outcome = result_fm.get("outcome")
    if not outcome:
        if (tdir / "merge.md").exists():
            outcome = "merged"
        elif execution["pr_url"] or execution["pr_number"]:
            outcome = "shipped"
        else:
            outcome = "in-progress"

    result = {
        "has_result": has_result,
        "outcome": outcome,
        "technologies": technologies,
        "result_text": section_get(sections, "결과").get("text", ""),
        "worked": section_get(sections, "잘된 점").get("bullets", []),
        "failed": section_get(sections, "어려웠던 점 / 실패",
                              "어려웠던 점/실패", "실패").get("bullets", []),
        "decisions": section_get(sections, "결정").get("bullets", []),
        "tech_notes": section_get(sections, "사용 기술").get("bullets", []),
        "followups": section_get(sections, "후속 작업").get("bullets", []),
        "background": section_get(ssections, "개요").get("text", ""),
    }

    # feature: result.md 권위값만 사용 (추측 금지). 빈값/부재 → unassigned.
    feature_branch = result_fm.get("feature") or ""
    feature_slug = C.slugify(feature_branch) if feature_branch else None
    worktree = result_fm.get("worktree") or {}
    if not isinstance(worktree, dict):
        worktree = {}
    issue_keys = result_fm.get("issue_keys", [])
    if not isinstance(issue_keys, list):
        issue_keys = []
    feature = {
        "feature_branch": feature_branch,
        "feature_slug": feature_slug,            # None = unassigned
        "base_source": result_fm.get("base_source") or "unknown",
        "worktree_kind": worktree.get("kind") or "",
        "worktree_name": worktree.get("name") or "",
        "issue_keys": issue_keys,
    }

    return {
        "key": key,
        "identity": identity,
        "execution": execution,
        "result": result,
        "feature": feature,
        "existing_patterns": vault_slugs("pattern"),
        "existing_technologies": vault_slugs("technology"),
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "USAGE: extract.py <KEY>"}))
        sys.exit(1)
    print(json.dumps(extract_facts(sys.argv[1]), ensure_ascii=False))


if __name__ == "__main__":
    main()
