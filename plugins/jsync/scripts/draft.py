"""jsync draft — compose/merge a task.md description body from prompt requirements.

The agent does the creative writing (turning prose requirements into a structured
description, and merging with the existing body). This script does the mechanical,
byte-preserving text surgery and file I/O so frontmatter and read-only sections are
never corrupted.

Subcommands:
    extract  <KEY|DRAFT-x>           print current description body (stdin not used)
    splice   <KEY|DRAFT-x>           replace description body with stdin (UTF-8)
    scaffold "<summary>" [opts]      create a new DRAFT-* task.md (body from stdin, optional)
    addimage <KEY|DRAFT-x> <path>    copy an image into attachments/, print its relative path
"""
import sys
import re
import shutil
from pathlib import Path

from common import check_deps, issue_dir, attachments_dir, STORE_ROOT

check_deps()
import yaml  # noqa: E402

# Same section-boundary regex as update.parse_task_md (read-only marker tolerated).
SECTION_RE = re.compile(r"^## (.+?)(?:\s+<!--.*-->)?$")

# Frontmatter key order mirrors fetch.render_task_md for a consistent task.md shape.
DRAFT_FRONTMATTER_ORDER = [
    "key", "summary", "status", "issuetype", "priority", "assignee",
    "labels", "components", "fixVersions", "duedate", "parent", "watchers",
    "links", "customfields", "add_worklog",
]


# --------------------------------------------------------------------------- #
# Byte-preserving description slicer
# --------------------------------------------------------------------------- #
def slice_description(text: str) -> tuple[str, str, str]:
    """Split a task.md into (head, description_body, tail) by substring offsets.

    head: frontmatter block + the '# <title>' line (everything before the body).
    description_body: from after the title line up to the first '## ' section.
    tail: the first '## ' section to EOF (read-only sections, New Comment) — byte-exact.

    Fallbacks: if there is no '# ' title, the body starts right after the
    frontmatter; if there is no '## ' section, tail is empty.
    """
    if not text.startswith("---"):
        raise ValueError("task.md missing YAML frontmatter")
    fm_end = text.index("---", 3) + 3  # offset just after the closing '---'

    # (line_start_offset, line_with_newline) for every line.
    lines: list[tuple[int, str]] = []
    off = 0
    for ln in text.splitlines(keepends=True):
        lines.append((off, ln))
        off += len(ln)

    # Description start: skip blank lines after the frontmatter, then an optional
    # '# ' title line. If a title is present, the body starts after it.
    desc_start = fm_end
    j = 0
    while j < len(lines) and lines[j][0] < fm_end:
        j += 1
    while j < len(lines) and lines[j][1].strip() == "":
        j += 1
    if j < len(lines) and lines[j][1].startswith("# "):
        desc_start = lines[j][0] + len(lines[j][1])

    # Tail start: first '## ' section header at or after desc_start.
    tail_start = len(text)
    for o, ln in lines:
        if o >= desc_start and SECTION_RE.match(ln.rstrip("\n")):
            tail_start = o
            break

    return text[:desc_start], text[desc_start:tail_start], text[tail_start:]


def splice_description(text: str, new_body: str) -> str:
    """Return task.md with only the description body replaced; everything else byte-exact."""
    head, _old, tail = slice_description(text)
    result = head.rstrip() + "\n\n" + new_body.strip() + "\n"
    if tail.strip():
        result += "\n" + tail.lstrip("\n")
    if not result.endswith("\n"):
        result += "\n"
    return result


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def task_path(key: str) -> Path:
    return STORE_ROOT / key / "task.md"


def read_stdin() -> str:
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read()


def draft_slug(summary: str, override: str | None = None) -> str:
    """Slug for a DRAFT-* directory. Keeps unicode word chars (Korean summaries
    survive, unlike fetch._slugify which is ASCII-only). Never purely numeric, so
    'DRAFT-<slug>' can't match ISSUE_KEY_RE (^[A-Z][A-Z0-9_]+-\\d+$)."""
    base = (override or summary or "").strip()
    s = re.sub(r"[^\w]+", "-", base, flags=re.UNICODE).strip("-")[:40].strip("-")
    if not s:
        s = "untitled"
    if s.isdigit():
        s = "draft-" + s
    return s


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #
def cmd_extract(key: str):
    p = task_path(key)
    if not p.exists():
        return  # empty output: nothing to merge with yet
    _head, body, _tail = slice_description(p.read_text(encoding="utf-8"))
    sys.stdout.write(body.strip())


def cmd_splice(key: str):
    p = task_path(key)
    if not p.exists():
        print(f"error: {p} not found — run /jsync:fetch {key} first "
              f"(or /jsync:draft with no key to create a new draft)", file=sys.stderr)
        sys.exit(1)
    new_body = read_stdin()
    text = p.read_text(encoding="utf-8")
    p.write_text(splice_description(text, new_body), encoding="utf-8")
    print(f"drafted {key}: description ({len(new_body.strip())} chars)")


def cmd_scaffold(summary: str, issuetype: str, slug_override: str | None):
    summary = summary.strip()
    if not summary:
        print("error: scaffold requires a summary", file=sys.stderr)
        sys.exit(1)

    slug = draft_slug(summary, slug_override)
    name = f"DRAFT-{slug}"
    # Avoid clobbering an existing draft with the same slug.
    n = 2
    while (STORE_ROOT / name).exists():
        name = f"DRAFT-{slug}-{n}"
        n += 1

    fm = {
        "key": "", "summary": summary, "status": "", "issuetype": issuetype,
        "priority": "", "assignee": "", "labels": [], "components": [],
        "fixVersions": [], "duedate": "", "parent": "", "watchers": [],
        "links": {}, "customfields": {}, "add_worklog": "",
    }
    ordered = {k: fm[k] for k in DRAFT_FRONTMATTER_ORDER}
    yaml_str = yaml.dump(ordered, allow_unicode=True, default_flow_style=False, sort_keys=False)

    body = read_stdin().strip()
    parts = [
        f"---\n{yaml_str}---\n",
        f"# {summary}\n",
        body,
        "\n## New Comment  <!-- write-only: fill to post, cleared after send -->\n\n",
    ]
    content = "\n".join(p for p in parts if p).rstrip() + "\n"

    d = issue_dir(name)
    (d / "task.md").write_text(content, encoding="utf-8")
    print(f"draft created: {name}  ({d / 'task.md'})")


def cmd_addimage(key: str, src: str):
    src_path = Path(src).expanduser()
    if not src_path.exists() or not src_path.is_file():
        print(f"error: image not found: {src}", file=sys.stderr)
        sys.exit(1)
    adir = attachments_dir(key)
    dest = adir / src_path.name
    if dest.exists():
        stem, suffix = src_path.stem, src_path.suffix
        n = 1
        while dest.exists():
            dest = adir / f"{stem}_{n}{suffix}"
            n += 1
    shutil.copy2(src_path, dest)
    print(f"attachments/{dest.name}")


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    cmd, rest = argv[0], argv[1:]

    if cmd == "extract":
        if len(rest) != 1:
            print("usage: draft.py extract <KEY|DRAFT-x>", file=sys.stderr)
            sys.exit(1)
        cmd_extract(rest[0])

    elif cmd == "splice":
        if len(rest) != 1:
            print("usage: draft.py splice <KEY|DRAFT-x>  (body on stdin)", file=sys.stderr)
            sys.exit(1)
        cmd_splice(rest[0])

    elif cmd == "scaffold":
        # scaffold "<summary>" [--issuetype Task] [--slug xxx]
        summary_parts: list[str] = []
        issuetype = "Task"
        slug_override = None
        i = 0
        while i < len(rest):
            tok = rest[i]
            if tok == "--issuetype" and i + 1 < len(rest):
                issuetype = rest[i + 1]
                i += 2
            elif tok == "--slug" and i + 1 < len(rest):
                slug_override = rest[i + 1]
                i += 2
            else:
                summary_parts.append(tok)
                i += 1
        cmd_scaffold(" ".join(summary_parts), issuetype, slug_override)

    elif cmd == "addimage":
        if len(rest) != 2:
            print("usage: draft.py addimage <KEY|DRAFT-x> <src_path>", file=sys.stderr)
            sys.exit(1)
        cmd_addimage(rest[0], rest[1])

    else:
        print(f"error: unknown command '{cmd}'", file=sys.stderr)
        print(__doc__, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
