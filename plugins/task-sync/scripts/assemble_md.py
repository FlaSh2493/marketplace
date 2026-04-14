#!/usr/bin/env python3
"""
converted.json + 다운로드 결과 → 최종 .md 파일 조립.
Claude가 Read/Edit할 필요 없이 Python이 직접 파일을 완성한다.

Usage:
  python3 assemble_md.py {converted_json} {target_md} --issue-key {이슈키} --assets-dir {assets_dir}

Exit 0: {"ok": true, "file": "..."}
Exit 1: {"ok": false, "reason": "..."}
"""

import json
import os
import re
import sys
from datetime import datetime


def parse_description_sections(description_md: str):
    """description_md의 ## 헤딩을 파싱하여 (heading, content) 리스트 반환.
    ## 헤딩이 없으면 None 반환 → fallback."""
    if not description_md:
        return None
    parts = re.split(r'^(## .+)$', description_md, flags=re.MULTILINE)
    # parts = [preamble, heading1, content1, heading2, content2, ...]
    if len(parts) < 3:
        return None
    sections = []
    preamble = parts[0].strip()
    for i in range(1, len(parts), 2):
        heading = parts[i]
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if preamble and heading == "## 설명":
            content = preamble + "\n\n" + content if content else preamble
            preamble = ""
        sections.append((heading, content))
    if preamble:
        sections.insert(0, ("## 설명", preamble))
    return sections


def find_inline_images(description_md: str) -> set:
    """description_md에서 참조된 이미지 파일명(./assets/ 이후)을 추출."""
    pattern = re.compile(r'!\[[^\]]*\]\(\./assets/([^)]+)\)')
    return set(pattern.findall(description_md))


def classify_attachments(attachments: list, inline_names: set):
    """첨부파일을 inline 참조 이미지 / 미참조 이미지 / 비이미지로 분류."""
    IMAGE_MIMES = {"image/png", "image/jpeg", "image/gif", "image/svg+xml", "image/webp"}
    extra_images = []
    non_images = []

    for att in attachments:
        local_name = att.get("localName", "")
        mime = att.get("mimeType", "")
        # assets_dir에 실제 다운로드된 파일만 포함 (url이 있으면 다운로드 대상이었음)
        if not att.get("url"):
            continue

        if mime in IMAGE_MIMES:
            if local_name not in inline_names:
                extra_images.append(att)
        else:
            non_images.append(att)

    return extra_images, non_images


def assemble(converted_path: str, target_md: str, issue_key: str, assets_dir: str) -> dict:
    try:
        with open(converted_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"ok": False, "reason": f"converted.json 읽기 실패: {e}"}

    summary = data.get("summary", "")
    status = data.get("status", "")
    assignee = data.get("assignee", "미배정")
    created = data.get("created", "")
    description_md = data.get("description_md", "")
    comments_md = data.get("comments_md", "")
    attachments = data.get("attachments", [])

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 인라인 이미지 판별
    inline_names = find_inline_images(description_md)

    # 실제 다운로드된 파일만 필터 (assets_dir에 존재하는 것)
    downloaded = []
    for att in attachments:
        local_path = os.path.join(assets_dir, att.get("localName", ""))
        if os.path.exists(local_path):
            downloaded.append(att)

    extra_images, non_images = classify_attachments(downloaded, inline_names)

    # 조립
    lines = [
        f"# {issue_key}: {summary}",
        "",
        f"- jira: {issue_key}",
        f"- 상태: {status}",
        f"- 담당자: {assignee}",
        f"- 생성일: {created}",
        f"- 최근 업데이트: {now}",
        "- 출처: jira-fetch",
        "",
        "---",
    ]

    parsed_sections = parse_description_sections(description_md)
    if parsed_sections:
        for heading, content in parsed_sections:
            lines += ["", heading, "", content if content else "(내용 없음)", "", "---"]
    else:
        lines += ["", "## 설명", "", description_md if description_md else "(내용 없음)", "", "---"]

    # 첨부 이미지 (description 미참조만)
    if extra_images:
        lines.append("")
        lines.append("## 첨부 이미지")
        lines.append("")
        for att in extra_images:
            name = att["localName"]
            lines.append(f"![{att.get('filename', name)}](./assets/{name})")
        lines.append("")
        lines.append("---")

    # 첨부 파일 (비이미지)
    if non_images:
        lines.append("")
        lines.append("## 첨부 파일")
        lines.append("")
        for att in non_images:
            name = att["localName"]
            lines.append(f"- [{att.get('filename', name)}](./assets/{name})")
        lines.append("")
        lines.append("---")

    # 댓글
    if comments_md.strip():
        lines.append("")
        lines.append("## 댓글")
        lines.append("")
        lines.append(comments_md)
        lines.append("")
        lines.append("---")

    content = "\n".join(lines)

    try:
        os.makedirs(os.path.dirname(target_md), exist_ok=True)
        with open(target_md, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return {"ok": False, "reason": f"파일 쓰기 실패: {e}"}

    return {"ok": True, "file": target_md}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="converted.json → 최종 .md 조립")
    parser.add_argument("converted_json", help="converted JSON 경로")
    parser.add_argument("target_md", help="출력 .md 경로")
    parser.add_argument("--issue-key", required=True, help="이슈 키")
    parser.add_argument("--assets-dir", required=True, help="assets 디렉토리 경로")

    args = parser.parse_args()
    result = assemble(args.converted_json, args.target_md, args.issue_key, args.assets_dir)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
