"""
Markdown <-> ADF (Atlassian Document Format) converter.
Covers: paragraphs, headings, bullet/ordered lists, task lists,
        code blocks, inline code, bold, italic, links, blockquotes.
ADF nodes not round-trippable (panel, media, mention, inlineCard, etc.)
are preserved as <!-- adf-ref:<idx> --> placeholders.
"""
import re
import json


# ---------------------------------------------------------------------------
# ADF -> Markdown
# ---------------------------------------------------------------------------

def adf_to_md(node: dict, refs: dict | None = None,
              media_map: dict | None = None, media_refs: dict | None = None) -> str:
    if refs is None:
        refs = {}
    t = node.get("type", "")
    content = node.get("content", [])
    attrs = node.get("attrs", {})

    if t == "doc":
        return "\n\n".join(_adf_block(c, refs, media_map, media_refs) for c in content).strip()
    return _adf_block(node, refs, media_map, media_refs)


def _render_media(node: dict, media_map: dict | None, media_refs: dict | None) -> str | None:
    """Render a media / mediaSingle / mediaGroup node as markdown image line(s).
    Returns None if any media id is unknown (caller falls back to placeholder).
    Records the original wrapper in media_refs (keyed by local path) for round-trip."""
    t = node.get("type", "")
    if t == "media":
        medias = [node]
    else:  # mediaSingle / mediaGroup
        medias = [c for c in node.get("content", []) if c.get("type") == "media"]
    if not medias:
        return None

    single_wrapper = t == "mediaSingle" and len(medias) == 1
    lines = []
    for m in medias:
        mid = m.get("attrs", {}).get("id", "")
        fname = (media_map or {}).get(mid)
        if not fname:
            return None  # unknown media -> let caller preserve as placeholder
        path = f"attachments/{fname}"
        if media_refs is not None:
            if single_wrapper:
                media_refs[path] = node  # exact original wrapper (common case)
            else:
                media_refs[path] = {
                    "type": "mediaSingle",
                    "attrs": {"layout": "center"},
                    "content": [m],
                }
        lines.append(f"![{fname}]({path})")
    return "\n\n".join(lines)


def _adf_block(node: dict, refs: dict,
               media_map: dict | None = None, media_refs: dict | None = None) -> str:
    t = node.get("type", "")
    content = node.get("content", [])
    attrs = node.get("attrs", {})

    if t == "paragraph":
        return _inline_content(content, refs, media_map, media_refs)

    if t == "heading":
        level = attrs.get("level", 1)
        text = _inline_content(content, refs, media_map, media_refs)
        return f"{'#' * level} {text}"

    if t == "bulletList":
        return "\n".join(_list_item(c, refs, False, 0, media_map, media_refs) for c in content)

    if t == "orderedList":
        return "\n".join(_list_item(c, refs, True, i+1, media_map, media_refs) for i, c in enumerate(content))

    if t == "taskList":
        return "\n".join(_task_item(c, refs, media_map, media_refs) for c in content)

    if t == "codeBlock":
        lang = attrs.get("language", "")
        code = "".join(c.get("text", "") for c in content if c.get("type") == "text")
        return f"```{lang}\n{code}\n```"

    if t == "blockquote":
        inner = "\n\n".join(_adf_block(c, refs, media_map, media_refs) for c in content)
        return "\n".join(f"> {line}" for line in inner.splitlines())

    if t == "rule":
        return "---"

    if t == "table":
        return _adf_table(node, refs, media_map, media_refs)

    if t in ("media", "mediaSingle", "mediaGroup"):
        rendered = _render_media(node, media_map, media_refs)
        if rendered is not None:
            return rendered
        # fall through to placeholder if media id unknown

    # Unsupported node — preserve as placeholder
    idx = len(refs)
    key = f"adf-ref-{idx}"
    refs[key] = node
    return f"<!-- {key} -->"


def _list_item(node: dict, refs: dict, ordered: bool, idx: int = 0,
               media_map: dict | None = None, media_refs: dict | None = None) -> str:
    prefix = f"{idx}." if ordered else "-"
    parts = []
    for c in node.get("content", []):
        if c.get("type") == "paragraph":
            parts.append(_inline_content(c.get("content", []), refs, media_map, media_refs))
        else:
            inner = _adf_block(c, refs, media_map, media_refs)
            parts.append("\n" + "\n".join(f"  {l}" for l in inner.splitlines()))
    return f"{prefix} " + "\n".join(parts)


def _task_item(node: dict, refs: dict,
               media_map: dict | None = None, media_refs: dict | None = None) -> str:
    done = node.get("attrs", {}).get("state") == "DONE"
    check = "[x]" if done else "[ ]"
    text = _inline_content(node.get("content", [{}])[0].get("content", []), refs, media_map, media_refs)
    return f"- {check} {text}"


def _adf_table(node: dict, refs: dict,
               media_map: dict | None = None, media_refs: dict | None = None) -> str:
    rows = []
    for row in node.get("content", []):
        cells = []
        for cell in row.get("content", []):
            inner = " ".join(_adf_block(c, refs, media_map, media_refs) for c in cell.get("content", []))
            cells.append(inner.replace("|", "\\|"))
        rows.append("| " + " | ".join(cells) + " |")
    if not rows:
        return ""
    header = rows[0]
    sep = "| " + " | ".join("---" for _ in rows[0].split("|")[1:-1]) + " |"
    return "\n".join([header, sep] + rows[1:])


def _inline_content(content: list, refs: dict,
                    media_map: dict | None = None, media_refs: dict | None = None) -> str:
    parts = []
    for node in content:
        t = node.get("type", "")
        text = node.get("text", "")
        marks = {m["type"]: m.get("attrs", {}) for m in node.get("marks", [])}

        if t == "text":
            if "code" in marks:
                text = f"`{text}`"
            if "strong" in marks:
                text = f"**{text}**"
            if "em" in marks:
                text = f"_{text}_"
            if "link" in marks:
                href = marks["link"].get("href", "")
                text = f"[{text}]({href})"
            if "strike" in marks:
                text = f"~~{text}~~"
            parts.append(text)

        elif t == "hardBreak":
            parts.append("  \n")

        elif t == "mention":
            idx = len(refs)
            key = f"adf-ref-{idx}"
            refs[key] = node
            parts.append(f"<!-- {key} -->")

        elif t == "inlineCard":
            url = node.get("attrs", {}).get("url", "")
            parts.append(f"[{url}]({url})" if url else "")

        else:
            idx = len(refs)
            key = f"adf-ref-{idx}"
            refs[key] = node
            parts.append(f"<!-- {key} -->")

    return "".join(parts)


# ---------------------------------------------------------------------------
# Markdown -> ADF
# ---------------------------------------------------------------------------

IMAGE_LINE_RE = re.compile(r"^!\[[^\]]*\]\(([^)]+)\)\s*$")


def md_to_adf(md: str, refs: dict | None = None, media_resolve: dict | None = None) -> dict:
    if refs is None:
        refs = {}
    blocks = _parse_md_blocks(md, refs, media_resolve)
    return {"type": "doc", "version": 1, "content": blocks}


def _parse_md_blocks(md: str, refs: dict, media_resolve: dict | None = None) -> list:
    lines = md.splitlines()
    blocks = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Placeholder restore
        m = re.match(r"^<!--\s*(adf-ref-\d+)\s*-->$", line)
        if m and m.group(1) in refs:
            blocks.append(refs[m.group(1)])
            i += 1
            continue

        # Image line -> media node (resolved by caller: existing or freshly uploaded)
        m = IMAGE_LINE_RE.match(line)
        if m:
            node = (media_resolve or {}).get(m.group(1))
            if node is not None:
                blocks.append(node)
            # unresolved image path -> drop the line (avoid emitting raw markdown)
            i += 1
            continue

        # Heading
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            blocks.append({"type": "heading", "attrs": {"level": level},
                           "content": _parse_inline(m.group(2), refs)})
            i += 1
            continue

        # Code block
        if line.startswith("```"):
            lang = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            blocks.append({"type": "codeBlock",
                           "attrs": {"language": lang} if lang else {},
                           "content": [{"type": "text", "text": "\n".join(code_lines)}]})
            continue

        # Blockquote
        if line.startswith("> "):
            bq_lines = []
            while i < len(lines) and lines[i].startswith("> "):
                bq_lines.append(lines[i][2:])
                i += 1
            inner = _parse_md_blocks("\n".join(bq_lines), refs, media_resolve)
            blocks.append({"type": "blockquote", "content": inner})
            continue

        # Horizontal rule
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", line.strip()):
            blocks.append({"type": "rule"})
            i += 1
            continue

        # Task list
        if re.match(r"^- \[[ x]\] ", line):
            items = []
            while i < len(lines) and re.match(r"^- \[[ x]\] ", lines[i]):
                done = lines[i][3] == "x"
                text = lines[i][6:]
                items.append({
                    "type": "taskItem",
                    "attrs": {"localId": str(i), "state": "DONE" if done else "TODO"},
                    "content": [{"type": "paragraph", "content": _parse_inline(text, refs)}],
                })
                i += 1
            blocks.append({"type": "taskList", "attrs": {"localId": str(i)}, "content": items})
            continue

        # Bullet list
        if re.match(r"^[-*+] ", line):
            items, i = _collect_list_items(lines, i, refs, ordered=False, media_resolve=media_resolve)
            blocks.append({"type": "bulletList", "content": items})
            continue

        # Ordered list
        if re.match(r"^\d+\. ", line):
            items, i = _collect_list_items(lines, i, refs, ordered=True, media_resolve=media_resolve)
            blocks.append({"type": "orderedList", "content": items})
            continue

        # Empty line — skip
        if line.strip() == "":
            i += 1
            continue

        # Paragraph
        para_lines = []
        while i < len(lines) and lines[i].strip() != "" and not _is_block_start(lines[i]):
            para_lines.append(lines[i])
            i += 1
        text = " ".join(para_lines)
        blocks.append({"type": "paragraph", "content": _parse_inline(text, refs)})

    return blocks


def _is_block_start(line: str) -> bool:
    return bool(
        re.match(r"^#{1,6} ", line) or
        line.startswith("```") or
        line.startswith("> ") or
        re.match(r"^[-*+] ", line) or
        re.match(r"^\d+\. ", line) or
        IMAGE_LINE_RE.match(line) or
        re.match(r"^(-{3,}|\*{3,}|_{3,})$", line.strip())
    )


def _collect_list_items(lines: list, start: int, refs: dict, ordered: bool,
                        media_resolve: dict | None = None) -> tuple:
    items = []
    i = start
    pattern = r"^\d+\. " if ordered else r"^[-*+] "
    while i < len(lines) and re.match(pattern, lines[i]):
        text = re.sub(pattern, "", lines[i], count=1)
        item_content = [{"type": "paragraph", "content": _parse_inline(text, refs)}]
        # nested indented lines
        i += 1
        nested_lines = []
        while i < len(lines) and lines[i].startswith("  "):
            nested_lines.append(lines[i][2:])
            i += 1
        if nested_lines:
            item_content += _parse_md_blocks("\n".join(nested_lines), refs, media_resolve)
        items.append({"type": "listItem", "content": item_content})
    return items, i


def _parse_inline(text: str, refs: dict) -> list:
    nodes = []
    # Split on placeholder references first
    parts = re.split(r"(<!--\s*adf-ref-\d+\s*-->)", text)
    for part in parts:
        m = re.match(r"<!--\s*(adf-ref-\d+)\s*-->", part)
        if m and m.group(1) in refs:
            nodes.append(refs[m.group(1)])
            continue
        nodes.extend(_parse_inline_marks(part))
    return nodes or [{"type": "text", "text": ""}]


def _parse_inline_marks(text: str) -> list:
    if not text:
        return []
    nodes = []

    patterns = [
        ("bold_italic", r"\*\*\*(.*?)\*\*\*"),
        ("bold", r"\*\*(.*?)\*\*"),
        ("italic", r"\*(.*?)\*|_(.*?)_"),
        ("code", r"`([^`]+)`"),
        ("strike", r"~~(.*?)~~"),
        ("link", r"\[([^\]]+)\]\(([^)]+)\)"),
    ]

    # Find first match across all patterns
    earliest = None
    earliest_m = None
    earliest_type = None
    for ptype, pat in patterns:
        m = re.search(pat, text)
        if m and (earliest is None or m.start() < earliest):
            earliest = m.start()
            earliest_m = m
            earliest_type = ptype

    if earliest_m is None:
        return [{"type": "text", "text": text}]

    m = earliest_m
    before = text[:m.start()]
    after = text[m.end():]

    if before:
        nodes.append({"type": "text", "text": before})

    if earliest_type == "bold_italic":
        inner = m.group(1)
        nodes.append({"type": "text", "text": inner,
                      "marks": [{"type": "strong"}, {"type": "em"}]})
    elif earliest_type == "bold":
        nodes.append({"type": "text", "text": m.group(1), "marks": [{"type": "strong"}]})
    elif earliest_type == "italic":
        inner = m.group(1) or m.group(2)
        nodes.append({"type": "text", "text": inner, "marks": [{"type": "em"}]})
    elif earliest_type == "code":
        nodes.append({"type": "text", "text": m.group(1), "marks": [{"type": "code"}]})
    elif earliest_type == "strike":
        nodes.append({"type": "text", "text": m.group(1), "marks": [{"type": "strike"}]})
    elif earliest_type == "link":
        nodes.append({"type": "text", "text": m.group(1),
                      "marks": [{"type": "link", "attrs": {"href": m.group(2)}}]})

    nodes.extend(_parse_inline_marks(after))
    return nodes
