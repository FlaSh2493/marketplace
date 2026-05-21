"""
jsync fetch — Jira 이슈를 ~/Documents/jsync/<KEY>/ 에 저장.

Usage:
  fetch.py MKT                        # 프로젝트: 활성스프린트 × 본인할당
  fetch.py MKT,ADX                    # 다중 프로젝트 (콤마)
  fetch.py MKT ADX                    # 다중 프로젝트 (공백)
  fetch.py MKT-142                    # 이슈 키 직접 (스프린트 제약 없음)
  fetch.py MKT-142,ADX-77             # 다중 이슈 키 (콤마)
  fetch.py MKT-142 MKT-200            # 다중 이슈 키 (공백)
  fetch.py --jql "status = Done" MKT  # 프로젝트 모드에 추가 JQL
"""
import sys
import json
import re
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import check_deps, issue_dir, get_env
check_deps()

import yaml
from jira_client import get_issue, get_editmeta, search_issues, get_comments, get_worklogs
from md_adf import adf_to_md

ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+-\d+$")


def parse_args(argv: list[str]) -> tuple[list[str], list[str], str]:
    """Returns (issue_keys, project_keys, extra_jql)"""
    extra_jql = ""
    tokens = []
    i = 0
    while i < len(argv):
        if argv[i] == "--jql" and i + 1 < len(argv):
            extra_jql = argv[i + 1]
            i += 2
        else:
            # Split by comma
            for t in argv[i].split(","):
                t = t.strip()
                if t:
                    tokens.append(t)
            i += 1

    if not tokens:
        print("error: no project or issue key given", file=sys.stderr)
        print("  usage: fetch.py MKT   or   fetch.py MKT-142", file=sys.stderr)
        sys.exit(1)

    issue_keys = [t for t in tokens if ISSUE_KEY_RE.match(t)]
    project_keys = [t for t in tokens if not ISSUE_KEY_RE.match(t)]

    if issue_keys and project_keys:
        print("error: mixed issue/project tokens. use one type at a time.", file=sys.stderr)
        sys.exit(1)

    if extra_jql and issue_keys:
        print("error: --jql is only valid in project mode", file=sys.stderr)
        sys.exit(1)

    return issue_keys, project_keys, extra_jql


def build_jql(project_keys: list[str], extra_jql: str) -> str:
    proj = ", ".join(project_keys)
    jql = f'project in ({proj}) AND sprint in openSprints() AND assignee = currentUser()'
    if extra_jql:
        jql += f" AND ({extra_jql})"
    return jql


def build_customfield_map(editmeta: dict) -> dict:
    """Returns {display_name: field_id} for all customfields."""
    mapping = {}
    for field_id, meta in editmeta.items():
        if field_id.startswith("customfield_"):
            name = meta.get("name", field_id)
            mapping[_slugify(name)] = field_id
    return mapping


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def build_transitions_map(issue: dict) -> dict:
    """Returns {status_name: transition_id} — placeholder; fetched lazily on update."""
    return {}


def render_task_md(issue: dict, refs: dict, cf_map: dict, comments: list, worklogs: list) -> str:
    f = issue.get("fields", {})

    # --- Frontmatter ---
    fm = {}
    fm["key"] = issue["key"]
    fm["summary"] = f.get("summary", "")
    fm["status"] = (f.get("status") or {}).get("name", "")
    fm["issuetype"] = (f.get("issuetype") or {}).get("name", "")
    fm["priority"] = (f.get("priority") or {}).get("name", "")

    assignee = f.get("assignee")
    fm["assignee"] = assignee.get("emailAddress", assignee.get("displayName", "")) if assignee else ""

    fm["labels"] = f.get("labels", [])
    fm["components"] = [c["name"] for c in f.get("components", [])]
    fm["fixVersions"] = [v["name"] for v in f.get("fixVersions", [])]
    fm["duedate"] = f.get("duedate", "") or ""

    parent = f.get("parent")
    fm["parent"] = parent["key"] if parent else ""

    # Watchers — not in standard GET, set empty for now
    fm["watchers"] = []

    # Links
    links: dict = {}
    for lnk in f.get("issuelinks", []):
        ltype = lnk.get("type", {}).get("name", "Relates")
        if "outwardIssue" in lnk:
            slug = _slugify(lnk["type"].get("outward", ltype))
            links.setdefault(slug, []).append(lnk["outwardIssue"]["key"])
        if "inwardIssue" in lnk:
            slug = _slugify(lnk["type"].get("inward", ltype))
            links.setdefault(slug, []).append(lnk["inwardIssue"]["key"])
    fm["links"] = links

    # Custom fields
    cf = {}
    for display_name, field_id in cf_map.items():
        val = f.get(field_id)
        if val is None:
            continue
        if isinstance(val, dict):
            val = val.get("value") or val.get("name") or val.get("key") or str(val)
        cf[display_name] = val
    fm["customfields"] = cf

    fm["add_worklog"] = ""

    # --- YAML ---
    yaml_str = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)

    # --- Description body ---
    description_adf = f.get("description")
    if description_adf and isinstance(description_adf, dict):
        body = adf_to_md(description_adf, refs)
    else:
        body = ""

    # --- Subtasks ---
    subtasks = f.get("subtasks", [])
    subtasks_md = ""
    if subtasks:
        subtasks_md = "\n## Subtasks  <!-- read-only -->\n"
        for st in subtasks:
            subtasks_md += f"- [{st['key']}] {st['fields']['summary']}\n"

    # --- Comments ---
    comments_md = "\n## Comments  <!-- read-only -->\n"
    for c in comments:
        author = (c.get("author") or {}).get("emailAddress", "unknown")
        created = c.get("created", "")[:10]
        body_adf = c.get("body", {})
        c_md = adf_to_md(body_adf, {}) if isinstance(body_adf, dict) else str(body_adf)
        comments_md += f"\n**{author} — {created}**\n{c_md}\n"

    new_comment_md = "\n## New Comment  <!-- write-only: fill to post, cleared after send -->\n\n\n"

    # --- Worklog ---
    worklog_md = "\n## Worklog  <!-- read-only -->\n"
    for w in worklogs:
        author = (w.get("author") or {}).get("emailAddress", "unknown")
        started = w.get("started", "")[:10]
        time_spent = w.get("timeSpent", "")
        comment_adf = w.get("comment", {})
        c_text = adf_to_md(comment_adf, {}) if isinstance(comment_adf, dict) else ""
        worklog_md += f"- {author}  {time_spent}  {started}"
        if c_text:
            worklog_md += f"  — {c_text}"
        worklog_md += "\n"

    # --- Attachments ---
    attachments = f.get("attachment", [])
    att_md = ""
    if attachments:
        att_md = "\n## Attachments  <!-- read-only -->\n"
        for a in attachments:
            att_md += f"- [{a['filename']}]({a['content']})\n"

    parts = [
        f"---\n{yaml_str}---\n",
        f"# {fm['summary']}\n",
        body,
        subtasks_md,
        comments_md,
        new_comment_md,
        worklog_md,
        att_md,
    ]
    return "\n".join(p for p in parts if p).rstrip() + "\n"


def save_issue(issue: dict):
    key = issue["key"]
    d = issue_dir(key)
    env = get_env()

    # editmeta for customfield mapping
    editmeta = get_editmeta(key)
    cf_map = build_customfield_map(editmeta)

    # comments + worklogs
    comments = get_comments(key)
    worklogs = get_worklogs(key)

    # adf refs (for round-trip)
    refs: dict = {}
    task_md = render_task_md(issue, refs, cf_map, comments, worklogs)

    # raw.json
    (d / "raw.json").write_text(json.dumps(issue, ensure_ascii=False, indent=2), encoding="utf-8")

    # meta.json
    meta = {
        "key": key,
        "base_url": env["base_url"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "customfield_map": cf_map,
        "adf_refs": refs,
    }
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # task.md
    (d / "task.md").write_text(task_md, encoding="utf-8")

    return d


def main():
    check_deps()
    argv = sys.argv[1:]
    issue_keys, project_keys, extra_jql = parse_args(argv)

    if issue_keys:
        issues = [get_issue(k) for k in issue_keys]
        label = ", ".join(issue_keys)
    else:
        jql = build_jql(project_keys, extra_jql)
        issues = search_issues(jql)
        label = f"{','.join(project_keys)} active sprint"

    if not issues:
        print(f"no issues found for {label}")
        return

    for issue in issues:
        save_issue(issue)

    keys = ", ".join(i["key"] for i in issues)
    n = len(issues)
    print(f"fetched {n} issue{'s' if n > 1 else ''} from {label}: {keys}")


if __name__ == "__main__":
    main()
