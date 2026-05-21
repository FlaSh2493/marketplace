"""
jsync update — task.md 변경사항을 Jira에 반영.

Usage:
  update.py MKT-142

Reads:  ~/Documents/jsync/MKT-142/task.md   (edited by user)
        ~/Documents/jsync/MKT-142/raw.json   (SSOT diff baseline)
        ~/Documents/jsync/MKT-142/meta.json  (customfield map, adf_refs)
Writes: stdout 1-liner summary
        raw.json re-synced after PUT
"""
import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import check_deps, issue_dir, STORE_ROOT
check_deps()

import yaml
from jira_client import (
    update_issue, transition_issue, list_transitions,
    add_comment, add_worklog,
    add_issue_link, delete_issue_link,
    get_issue,
)
from md_adf import md_to_adf

ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+-\d+$")
READONLY_SECTIONS = {"Subtasks", "Comments", "Worklog", "Attachments"}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_task_md(path: Path) -> tuple[dict, str, dict]:
    """Returns (frontmatter, description_md, sections)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("task.md missing YAML frontmatter")

    end = text.index("---", 3)
    fm = yaml.safe_load(text[3:end])
    rest = text[end + 3:].strip()

    # Strip title line (# Summary)
    lines = rest.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    rest = "\n".join(lines).strip()

    # Split into named sections
    sections: dict[str, str] = {}
    current_section = None
    current_lines: list[str] = []
    desc_lines: list[str] = []
    in_desc = True

    for line in rest.splitlines():
        m = re.match(r"^## (.+?)(?:\s+<!--.*-->)?$", line)
        if m:
            if in_desc:
                desc_lines = current_lines[:]
                in_desc = False
            else:
                if current_section is not None:
                    sections[current_section] = "\n".join(current_lines).strip()
            current_section = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if in_desc:
        desc_lines = current_lines
    elif current_section:
        sections[current_section] = "\n".join(current_lines).strip()

    description_md = "\n".join(desc_lines).strip()
    return fm, description_md, sections


def load_raw_fm(key: str) -> dict:
    raw_path = STORE_ROOT / key / "raw.json"
    if not raw_path.exists():
        return {}
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    f = raw.get("fields", {})

    assignee = f.get("assignee")
    parent = f.get("parent")
    fm = {
        "summary": f.get("summary", ""),
        "status": (f.get("status") or {}).get("name", ""),
        "priority": (f.get("priority") or {}).get("name", ""),
        "assignee": assignee.get("emailAddress", "") if assignee else "",
        "labels": f.get("labels", []),
        "components": [c["name"] for c in f.get("components", [])],
        "fixVersions": [v["name"] for v in f.get("fixVersions", [])],
        "duedate": f.get("duedate", "") or "",
        "parent": parent["key"] if parent else "",
    }
    return fm


def load_meta(key: str) -> dict:
    meta_path = STORE_ROOT / key / "meta.json"
    if not meta_path.exists():
        return {}
    return json.loads(meta_path.read_text(encoding="utf-8"))


def load_adf_refs(key: str) -> dict:
    meta = load_meta(key)
    return meta.get("adf_refs", {})


# ---------------------------------------------------------------------------
# Diff helpers
# ---------------------------------------------------------------------------

def _norm(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return sorted(str(x) for x in v)
    return str(v).strip()


def diff_scalar_fields(new_fm: dict, old_fm: dict) -> dict:
    """Returns fields that changed (excluding status, links, watchers, description)."""
    skip = {"key", "status", "issuetype", "links", "watchers", "customfields",
            "add_worklog", "reporter"}
    changed = {}
    for k, new_val in new_fm.items():
        if k in skip:
            continue
        old_val = old_fm.get(k)
        if _norm(new_val) != _norm(old_val):
            changed[k] = new_val
    return changed


def map_fields_to_jira(changed: dict, meta: dict) -> dict:
    """Convert display-name fields to Jira API fields."""
    cf_map = meta.get("customfield_map", {})
    result = {}
    for k, v in changed.items():
        if k == "summary":
            result["summary"] = v
        elif k == "priority":
            result["priority"] = {"name": v} if v else None
        elif k == "assignee":
            result["assignee"] = {"emailAddress": v} if v else None
        elif k == "labels":
            result["labels"] = v if isinstance(v, list) else [v]
        elif k == "components":
            result["components"] = [{"name": c} for c in (v or [])]
        elif k == "fixVersions":
            result["fixVersions"] = [{"name": x} for x in (v or [])]
        elif k == "duedate":
            result["duedate"] = v or None
        elif k == "parent":
            result["parent"] = {"key": v} if v else None
    return {k: v for k, v in result.items() if v is not None or k in ("duedate",)}


def map_customfields(new_cf: dict, old_cf: dict, meta: dict) -> dict:
    cf_map = meta.get("customfield_map", {})
    result = {}
    for display_name, new_val in new_cf.items():
        old_val = old_cf.get(display_name)
        if _norm(new_val) == _norm(old_val):
            continue
        field_id = cf_map.get(display_name)
        if not field_id:
            continue
        result[field_id] = new_val
    return result


# ---------------------------------------------------------------------------
# Link diff
# ---------------------------------------------------------------------------

def diff_links(new_links: dict, raw: dict) -> tuple[list, list]:
    """Returns (to_add, to_delete) where each entry is (type, key) or (link_id,)."""
    f = raw.get("fields", {})
    existing: dict[str, list] = {}
    existing_ids: dict[str, str] = {}

    for lnk in f.get("issuelinks", []):
        ltype = lnk.get("type", {}).get("name", "Relates")
        if "outwardIssue" in lnk:
            slug = _slugify_link(lnk["type"].get("outward", ltype))
            key = lnk["outwardIssue"]["key"]
            existing.setdefault(slug, []).append(key)
            existing_ids[f"{slug}:{key}"] = lnk["id"]
        if "inwardIssue" in lnk:
            slug = _slugify_link(lnk["type"].get("inward", ltype))
            key = lnk["inwardIssue"]["key"]
            existing.setdefault(slug, []).append(key)
            existing_ids[f"{slug}:{key}"] = lnk["id"]

    to_add = []
    to_delete = []

    for slug, keys in (new_links or {}).items():
        if not isinstance(keys, list):
            keys = [keys]
        for k in keys:
            token = f"{slug}:{k}"
            if k not in existing.get(slug, []):
                to_add.append((slug, k))
        for k in existing.get(slug, []):
            if k not in keys:
                link_id = existing_ids.get(f"{slug}:{k}")
                if link_id:
                    to_delete.append(link_id)

    # Slugs in existing but not in new -> delete
    for slug, keys in existing.items():
        if slug not in (new_links or {}):
            for k in keys:
                link_id = existing_ids.get(f"{slug}:{k}")
                if link_id:
                    to_delete.append(link_id)

    return to_add, to_delete


def _slugify_link(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


# ---------------------------------------------------------------------------
# Description diff
# ---------------------------------------------------------------------------

def desc_changed(new_md: str, raw: dict, refs: dict) -> bool:
    f = raw.get("fields", {})
    old_adf = f.get("description")
    if not old_adf and not new_md.strip():
        return False
    from md_adf import adf_to_md
    old_md = adf_to_md(old_adf, {}) if old_adf else ""
    return new_md.strip() != old_md.strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    check_deps()
    if len(sys.argv) < 2:
        print("error: usage: update.py <ISSUE-KEY>", file=sys.stderr)
        sys.exit(1)

    key = sys.argv[1].strip().upper()
    if not ISSUE_KEY_RE.match(key):
        print(f"error: '{key}' is not a valid issue key (e.g. MKT-142)", file=sys.stderr)
        sys.exit(1)

    d = STORE_ROOT / key
    task_md_path = d / "task.md"
    raw_path = d / "raw.json"

    if not task_md_path.exists():
        print(f"error: {task_md_path} not found. run fetch first.", file=sys.stderr)
        sys.exit(1)
    if not raw_path.exists():
        print(f"error: {raw_path} not found. run fetch first.", file=sys.stderr)
        sys.exit(1)

    new_fm, desc_md, sections = parse_task_md(task_md_path)
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    old_fm = load_raw_fm(key)
    meta = load_meta(key)
    refs = load_adf_refs(key)

    changed_labels = []
    put_fields = {}

    # Scalar fields
    scalar_changed = diff_scalar_fields(new_fm, old_fm)
    if scalar_changed:
        put_fields.update(map_fields_to_jira(scalar_changed, meta))
        changed_labels.extend(scalar_changed.keys())

    # Custom fields
    new_cf = new_fm.get("customfields") or {}
    old_cf_raw = {}
    for display_name, field_id in meta.get("customfield_map", {}).items():
        val = raw.get("fields", {}).get(field_id)
        if val is not None:
            if isinstance(val, dict):
                val = val.get("value") or val.get("name") or val.get("key") or str(val)
            old_cf_raw[display_name] = val
    cf_fields = map_customfields(new_cf, old_cf_raw, meta)
    if cf_fields:
        put_fields.update(cf_fields)
        changed_labels.append("customfields")

    # Description
    if desc_changed(desc_md, raw, refs):
        put_fields["description"] = md_to_adf(desc_md, refs)
        changed_labels.append("description")

    # PUT
    if put_fields:
        update_issue(key, put_fields)

    # Status transition
    new_status = (new_fm.get("status") or "").strip()
    old_status = old_fm.get("status", "").strip()
    if new_status and new_status.lower() != old_status.lower():
        transition_issue(key, new_status)
        changed_labels.append(f"status→{new_status}")

    # Links
    new_links = new_fm.get("links") or {}
    links_add, links_del = diff_links(new_links, raw)
    for slug, target_key in links_add:
        link_type = slug.replace("_", " ").title()
        add_issue_link(key, target_key, link_type)
        changed_labels.append(f"link+{target_key}")
    for link_id in links_del:
        delete_issue_link(link_id)
        changed_labels.append(f"link-{link_id}")

    # New Comment
    new_comment = (sections.get("New Comment") or "").strip()
    if new_comment:
        comment_adf = md_to_adf(new_comment, {})
        add_comment(key, comment_adf)
        changed_labels.append("comment")

    # Worklog
    worklog_entry = (new_fm.get("add_worklog") or "").strip()
    if worklog_entry:
        # Format: "2h optional comment text"
        parts = worklog_entry.split(None, 1)
        time_spent = parts[0]
        comment = parts[1] if len(parts) > 1 else ""
        add_worklog(key, time_spent, comment)
        changed_labels.append(f"worklog({time_spent})")

    if not changed_labels:
        print(f"no changes  {key}")
        return

    # Re-fetch raw.json + re-render task.md to clear write-only fields
    from fetch import save_issue
    updated_issue = get_issue(key)
    save_issue(updated_issue)

    print(f"updated {key}: {', '.join(changed_labels)}")


if __name__ == "__main__":
    main()
