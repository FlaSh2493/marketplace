#!/usr/bin/env python3
"""
Jira raw JSON → 마크다운 변환 스크립트.
renderedFields(HTML)를 파싱하여 마크다운으로 변환한다.
외부 라이브러리 없이 html.parser만 사용.
"""

import json
import os
import re
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional


class HtmlToMarkdown(HTMLParser):
    """HTML → Markdown 변환기 (Jira renderedFields 전용)"""

    def __init__(self, attachment_map: Optional[Dict[str, str]] = None):
        super().__init__()
        self._result: List[str] = []
        self._stack: List[str] = []
        self._list_stack: List[str] = []  # 'ul' or 'ol'
        self._ol_counters: List[int] = []
        self._pre = False
        self._code = False
        self._pre_lang = ""
        self._link_href = ""
        self._attachment_map = attachment_map or {}

    def _indent(self) -> str:
        depth = len(self._list_stack)
        return "  " * max(0, depth - 1) if depth > 0 else ""

    def handle_starttag(self, tag: str, attrs: list):
        attr = dict(attrs)
        self._stack.append(tag)

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self._result.append(f"\n{'#' * level} ")
        elif tag == "p":
            if not self._pre:
                self._result.append("\n")
        elif tag == "br":
            self._result.append("\n")
        elif tag == "strong" or tag == "b":
            self._result.append("**")
        elif tag == "em" or tag == "i":
            self._result.append("*")
        elif tag == "code":
            if not self._pre:
                self._code = True
                self._result.append("`")
        elif tag == "pre":
            self._pre = True
            self._pre_lang = ""
        elif tag == "a":
            self._link_href = attr.get("href", "")
            self._result.append("[")
        elif tag == "ul":
            self._list_stack.append("ul")
            self._result.append("\n")
        elif tag == "ol":
            self._list_stack.append("ol")
            self._ol_counters.append(0)
            self._result.append("\n")
        elif tag == "li":
            indent = self._indent()
            if self._list_stack and self._list_stack[-1] == "ol":
                self._ol_counters[-1] += 1
                self._result.append(f"{indent}{self._ol_counters[-1]}. ")
            else:
                self._result.append(f"{indent}- ")
        elif tag == "img":
            src = attr.get("src", "")
            alt = attr.get("alt", "")
            media_id = attr.get("data-media-id", "")
            if media_id and media_id in self._attachment_map:
                local_name = self._attachment_map[media_id]
                self._result.append(f"![{alt or local_name}](./assets/{local_name})")
            elif src:
                self._result.append(f"![{alt}]({src})")
        elif tag == "table":
            self._result.append("\n")
        elif tag == "th" or tag == "td":
            self._result.append("| ")
        elif tag == "hr":
            self._result.append("\n---\n")
        elif tag == "blockquote":
            self._result.append("\n> ")
        elif tag == "span":
            # Jira uses data-codestyle-language on span inside pre
            lang = attr.get("data-codestyle-language", "")
            if lang and self._pre:
                self._pre_lang = lang

    def handle_endtag(self, tag: str):
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._result.append("\n")
        elif tag == "p":
            if not self._pre:
                self._result.append("\n")
        elif tag == "strong" or tag == "b":
            self._result.append("**")
        elif tag == "em" or tag == "i":
            self._result.append("*")
        elif tag == "code":
            if not self._pre:
                self._code = False
                self._result.append("`")
            elif self._pre:
                # end of code block inside pre
                pass
        elif tag == "pre":
            self._pre = False
            self._result.append("\n```\n")
        elif tag == "a":
            self._result.append(f"]({self._link_href})")
            self._link_href = ""
        elif tag == "ul":
            if self._list_stack:
                self._list_stack.pop()
            self._result.append("\n")
        elif tag == "ol":
            if self._list_stack:
                self._list_stack.pop()
            if self._ol_counters:
                self._ol_counters.pop()
            self._result.append("\n")
        elif tag == "li":
            self._result.append("\n")
        elif tag == "tr":
            self._result.append("|\n")
        elif tag == "thead":
            # Add separator row after header
            pass
        elif tag == "blockquote":
            self._result.append("\n")

    def handle_data(self, data: str):
        if self._pre and not any(t == "code" for t in self._stack):
            # Start of pre block content
            self._result.append(f"\n```{self._pre_lang}\n{data}")
        elif self._pre:
            self._result.append(data)
        else:
            self._result.append(data)

    def get_markdown(self) -> str:
        text = "".join(self._result)
        # Clean up excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def html_to_md(html: str, attachment_map: Optional[Dict[str, str]] = None) -> str:
    """HTML 문자열을 마크다운으로 변환"""
    if not html:
        return ""
    parser = HtmlToMarkdown(attachment_map)
    parser.feed(html)
    return parser.get_markdown()


def format_datetime(iso_str: str) -> str:
    """ISO 8601 → YYYY-MM-DD HH:mm"""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return iso_str or ""


def convert_issue(raw_path: str, out_dir: str, issue_key: str) -> dict:
    """
    {issue_key}_raw.json → {issue_key}_converted.json

    Returns:
        {"ok": True, "file": "path"} or {"ok": False, "reason": "..."}
    """
    try:
        with open(raw_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"ok": False, "reason": f"JSON 읽기 실패: {e}"}

    fields = data.get("fields", {})
    rendered = data.get("renderedFields") or {}

    if not rendered:
        return {"ok": False, "reason": f"renderedFields가 없습니다. Jira API expand=renderedFields 응답을 확인하세요."}

    # Attachment ID → filename 매핑 (순번 기반)
    attachments = fields.get("attachment") or []
    attachment_map = {}  # media_id → local_name
    attachment_list = []
    for idx, att in enumerate(attachments, 1):
        ext = att.get("filename", "").rsplit(".", 1)[-1] if "." in att.get("filename", "") else "bin"
        local_name = f"{issue_key}-{idx}.{ext}"
        att_id = str(att.get("id", ""))
        if att_id:
            attachment_map[att_id] = local_name
        attachment_list.append({
            "id": att_id,
            "filename": att.get("filename", ""),
            "localName": local_name,
            "mimeType": att.get("mimeType", ""),
            "url": att.get("content", ""),
            "size": att.get("size", 0),
        })

    # Description HTML → Markdown
    desc_html = rendered.get("description", "") or ""
    description_md = html_to_md(desc_html, attachment_map)

    # Comments HTML → Markdown (인용블록 형식)
    comments_raw = rendered.get("comment", {})
    # renderedFields.comment can be a dict with 'comments' list or a list directly
    if isinstance(comments_raw, dict):
        comment_list = comments_raw.get("comments", [])
    elif isinstance(comments_raw, list):
        comment_list = comments_raw
    else:
        comment_list = []

    # Also need original comment data for author/created
    orig_comments = fields.get("comment", {})
    if isinstance(orig_comments, dict):
        orig_comment_list = orig_comments.get("comments", [])
    elif isinstance(orig_comments, list):
        orig_comment_list = orig_comments
    else:
        orig_comment_list = []

    comments_md_parts = []
    for i, rendered_comment in enumerate(comment_list):
        # rendered_comment is HTML string in renderedFields
        orig = orig_comment_list[i] if i < len(orig_comment_list) else {}
        author = (orig.get("author") or {}).get("displayName", "Unknown")
        created = format_datetime(orig.get("created", ""))
        body_html = rendered_comment if isinstance(rendered_comment, str) else rendered_comment.get("body", "")
        body_md = html_to_md(body_html, attachment_map)
        # Prefix each line with >
        quoted = "\n".join(f"> {line}" if line.strip() else ">" for line in body_md.split("\n"))
        comments_md_parts.append(f"> **@{author}** ({created})\n{quoted}")

    comments_md = "\n\n".join(comments_md_parts)

    # Assignee
    assignee_obj = fields.get("assignee") or {}
    assignee = assignee_obj.get("displayName", "미배정")

    result = {
        "summary": fields.get("summary", ""),
        "status": (fields.get("status") or {}).get("name", ""),
        "assignee": assignee,
        "created": format_datetime(fields.get("created", "")),
        "description_md": description_md,
        "comments_md": comments_md,
        "attachments": attachment_list,
        "attachment_map": attachment_map,
    }

    out_file = Path(out_dir) / f"{issue_key}_converted.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return {"ok": True, "file": str(out_file)}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Jira raw JSON → 마크다운 변환")
    parser.add_argument("raw_json", help="raw JSON 파일 경로 (예: /tmp/SPT-123_raw.json)")
    parser.add_argument("--issue-key", required=True, help="이슈 키 (예: SPT-123)")
    parser.add_argument("--out-dir", default=".", help="출력 디렉토리")

    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    result = convert_issue(args.raw_json, args.out_dir, args.issue_key)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
