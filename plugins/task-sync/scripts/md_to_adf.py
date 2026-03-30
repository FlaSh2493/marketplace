#!/usr/bin/env python3
"""
마크다운 → ADF(Atlassian Document Format) 변환기.
이미지는 Jira에 첨부파일로 업로드 후 mediaSingle 노드로 교체한다.

Usage:
  python3 md_to_adf.py {issue_key} {md_file_path}
  python3 md_to_adf.py {issue_key} - < input.md   # stdin

환경변수:
  JIRA_URL    예: https://yourcompany.atlassian.net
  JIRA_TOKEN  Jira API 토큰 (Basic auth: email:token base64)
  JIRA_EMAIL  Jira 계정 이메일

Exit 0: ADF JSON 출력 (stdout)
Exit 1: 오류 JSON 출력 (stdout)
"""
import json, os, sys, re, base64

# ── 의존성 체크 ────────────────────────────────────────────────────────────────

def check_mistune():
    try:
        import mistune
        return mistune
    except ImportError:
        error(
            "MISSING_DEPENDENCY",
            "mistune 라이브러리가 필요합니다.\n"
            "설치: pip install mistune\n"
            "또는: pip3 install mistune"
        )

# ── 출력 헬퍼 ─────────────────────────────────────────────────────────────────

def ok(adf):
    print(json.dumps(adf, ensure_ascii=False))
    sys.exit(0)

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)

# ── 환경변수 ──────────────────────────────────────────────────────────────────

def get_jira_config():
    url = os.environ.get("JIRA_URL", "").rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_TOKEN", "")

    missing = []
    if not url:
        missing.append("JIRA_URL")
    if not email:
        missing.append("JIRA_EMAIL")
    if not token:
        missing.append("JIRA_TOKEN")

    if missing:
        error(
            "MISSING_ENV",
            f"환경변수가 설정되지 않았습니다: {', '.join(missing)}\n"
            "예:\n"
            "  export JIRA_URL=https://yourcompany.atlassian.net\n"
            "  export JIRA_EMAIL=you@example.com\n"
            "  export JIRA_TOKEN=your_api_token"
        )
    return url, email, token

# ── Jira 첨부파일 업로드 ──────────────────────────────────────────────────────

def upload_attachment(issue_key, file_path, jira_url, email, token):
    """이미지를 Jira에 업로드하고 attachment id를 반환한다."""
    import urllib.request, urllib.error

    if not os.path.exists(file_path):
        return None, f"이미지 파일이 없습니다: {file_path} (건너뜀)"

    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    upload_url = f"{jira_url}/rest/api/3/issue/{issue_key}/attachments"

    # multipart/form-data 수동 구성
    boundary = "----TaskSyncBoundary"
    filename = os.path.basename(file_path)

    with open(file_path, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        upload_url,
        data=body,
        headers={
            "Authorization": f"Basic {credentials}",
            "X-Atlassian-Token": "no-check",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
            if isinstance(result, list) and result:
                att = result[0]
                return att.get("id"), None
            error(
                "UPLOAD_FAILED",
                f"첨부파일 업로드 응답이 비어있습니다: {issue_key} / {filename}"
            )
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        error(
            "UPLOAD_FAILED",
            f"첨부파일 업로드 실패: {issue_key} / {filename}\n"
            f"HTTP {e.code}: {body_text}"
        )
    except urllib.error.URLError as e:
        error(
            "UPLOAD_FAILED",
            f"Jira 연결 실패: {e.reason}\n"
            f"JIRA_URL을 확인하세요: {jira_url}"
        )

# ── ADF 노드 빌더 ─────────────────────────────────────────────────────────────

def text_node(text, marks=None):
    node = {"type": "text", "text": text}
    if marks:
        node["marks"] = marks
    return node

def paragraph(children):
    return {"type": "paragraph", "content": children}

def heading(level, children):
    return {"type": "heading", "attrs": {"level": level}, "content": children}

def bullet_list(items):
    return {
        "type": "bulletList",
        "content": [
            {"type": "listItem", "content": [paragraph(item)]}
            for item in items
        ]
    }

def ordered_list(items):
    return {
        "type": "orderedList",
        "content": [
            {"type": "listItem", "content": [paragraph(item)]}
            for item in items
        ]
    }

def code_block(code, language=""):
    return {
        "type": "codeBlock",
        "attrs": {"language": language or ""},
        "content": [{"type": "text", "text": code}]
    }

def rule_node():
    return {"type": "rule"}

def media_single(attachment_id):
    return {
        "type": "mediaSingle",
        "attrs": {"layout": "center"},
        "content": [
            {
                "type": "media",
                "attrs": {
                    "id": attachment_id,
                    "type": "attachment",
                    "collection": ""
                }
            }
        ]
    }

def table_node(header_row, body_rows):
    def cell(children, is_header=False):
        return {
            "type": "tableHeader" if is_header else "tableCell",
            "attrs": {},
            "content": [paragraph(children)]
        }

    def row(cells, is_header=False):
        return {
            "type": "tableRow",
            "content": [cell(c, is_header) for c in cells]
        }

    rows = [row(header_row, is_header=True)]
    for r in body_rows:
        rows.append(row(r))

    return {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
        "content": rows
    }

# ── 인라인 마크다운 파서 ──────────────────────────────────────────────────────

def parse_inline(text):
    """
    인라인 마크다운 → ADF text 노드 목록.
    지원: **bold**, *italic*, `code`, [link](url), ![img](path) (이미지는 경로만 보존)
    """
    nodes = []
    # 패턴 순서 중요: 더 구체적인 것 먼저
    pattern = re.compile(
        r'(\*\*(.+?)\*\*)'          # bold
        r'|(\*(.+?)\*)'             # italic
        r'|(`(.+?)`)'               # inline code
        r'|(\[(.+?)\]\((.+?)\))'   # link
        r'|(__(.+?)__)'             # bold alt
        r'|(_(.+?)_)'              # italic alt
    )
    last = 0
    for m in pattern.finditer(text):
        start, end = m.span()
        if start > last:
            nodes.append(text_node(text[last:start]))
        if m.group(1):  # **bold**
            nodes.append(text_node(m.group(2), [{"type": "strong"}]))
        elif m.group(3):  # *italic*
            nodes.append(text_node(m.group(4), [{"type": "em"}]))
        elif m.group(5):  # `code`
            nodes.append(text_node(m.group(6), [{"type": "code"}]))
        elif m.group(7):  # [link](url)
            nodes.append({
                "type": "text",
                "text": m.group(8),
                "marks": [{"type": "link", "attrs": {"href": m.group(9)}}]
            })
        elif m.group(10):  # __bold__
            nodes.append(text_node(m.group(11), [{"type": "strong"}]))
        elif m.group(12):  # _italic_
            nodes.append(text_node(m.group(13), [{"type": "em"}]))
        last = end
    if last < len(text):
        nodes.append(text_node(text[last:]))
    return nodes if nodes else [text_node(text)]

# ── 마크다운 → ADF 변환 ───────────────────────────────────────────────────────

IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
TABLE_RE = re.compile(r'^\|(.+)\|$')

def convert(md_text, issue_key, md_dir, jira_url, email, token, upload_images):
    content = []
    lines = md_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        # 코드블록
        if line.startswith("```"):
            lang = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            content.append(code_block("\n".join(code_lines), lang))
            i += 1
            continue

        # HR
        if re.match(r'^[-*_]{3,}$', line.strip()):
            content.append(rule_node())
            i += 1
            continue

        # ATX 헤더 (# ## ###)
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            level = min(len(m.group(1)), 6)
            content.append(heading(level, parse_inline(m.group(2))))
            i += 1
            continue

        # Setext 헤더 (=== 또는 ---)
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            if re.match(r'^=+$', next_line.strip()) and line.strip():
                content.append(heading(1, parse_inline(line.strip())))
                i += 2
                continue
            if re.match(r'^-+$', next_line.strip()) and line.strip():
                content.append(heading(2, parse_inline(line.strip())))
                i += 2
                continue

        # 테이블
        if TABLE_RE.match(line):
            header_cells = [c.strip() for c in line.strip("|").split("|")]
            body_rows = []
            i += 1
            # 구분선 skip
            if i < len(lines) and re.match(r'^[\|\-\s:]+$', lines[i]):
                i += 1
            while i < len(lines) and TABLE_RE.match(lines[i]):
                row_cells = [c.strip() for c in lines[i].strip("|").split("|")]
                body_rows.append([parse_inline(c) for c in row_cells])
                i += 1
            content.append(table_node(
                [parse_inline(c) for c in header_cells],
                body_rows
            ))
            continue

        # 순서 없는 목록
        if re.match(r'^[-*+]\s+', line):
            items = []
            while i < len(lines) and re.match(r'^[-*+]\s+', lines[i]):
                item_text = re.sub(r'^[-*+]\s+', '', lines[i])
                items.append(parse_inline(item_text))
                i += 1
            content.append(bullet_list(items))
            continue

        # 순서 있는 목록
        if re.match(r'^\d+\.\s+', line):
            items = []
            while i < len(lines) and re.match(r'^\d+\.\s+', lines[i]):
                item_text = re.sub(r'^\d+\.\s+', '', lines[i])
                items.append(parse_inline(item_text))
                i += 1
            content.append(ordered_list(items))
            continue

        # 이미지 (단독 줄)
        img_m = IMAGE_RE.match(line.strip())
        if img_m:
            img_path = img_m.group(2)
            abs_path = img_path if os.path.isabs(img_path) else os.path.join(md_dir, img_path)

            if upload_images:
                att_id, warn = upload_attachment(issue_key, abs_path, jira_url, email, token)
                if att_id:
                    content.append(media_single(att_id))
                else:
                    # 경고만 출력하고 계속
                    sys.stderr.write(f"[경고] {warn}\n")
            else:
                # 업로드 없이 alt 텍스트로 대체
                content.append(paragraph([text_node(f"[이미지: {img_m.group(1) or img_path}]")]))
            i += 1
            continue

        # 빈 줄
        if not line.strip():
            i += 1
            continue

        # 일반 단락 (인라인 이미지 포함 가능)
        para_nodes = []
        for part in IMAGE_RE.split(line):
            # IMAGE_RE.split은 (alt, path) 쌍을 포함한 리스트 반환
            pass
        # 단락 내 이미지는 텍스트로 대체 (mediaSingle은 블록 레벨)
        clean_line = IMAGE_RE.sub(lambda m: f"[이미지: {m.group(1) or m.group(2)}]", line)
        inline = parse_inline(clean_line)
        if inline:
            content.append(paragraph(inline))
        i += 1

    return {"version": 1, "type": "doc", "content": content}

# ── 진입점 ────────────────────────────────────────────────────────────────────

def main():
    check_mistune()  # mistune 설치 확인 (실제 파싱은 자체 구현 사용)

    args = sys.argv[1:]
    if len(args) < 2:
        error("MISSING_ARGS", "사용법: md_to_adf.py {issue_key} {md_file_path|-}")

    issue_key = args[0]
    file_arg = args[1]

    if file_arg == "-":
        md_text = sys.stdin.read()
        md_dir = os.getcwd()
    else:
        if not os.path.exists(file_arg):
            error("FILE_NOT_FOUND", f"파일이 없습니다: {file_arg}")
        with open(file_arg, encoding="utf-8") as f:
            md_text = f.read()
        md_dir = os.path.dirname(os.path.abspath(file_arg))

    # 이미지가 포함된 경우에만 Jira 환경변수 필요
    has_images = bool(IMAGE_RE.search(md_text))
    if has_images:
        jira_url, email, token = get_jira_config()
        upload_images = True
    else:
        jira_url = email = token = ""
        upload_images = False

    adf = convert(md_text, issue_key, md_dir, jira_url, email, token, upload_images)
    ok(adf)


if __name__ == "__main__":
    main()
