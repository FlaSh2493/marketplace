"""
cruise log — cruise 단계별 산출물을 모아 Jira 이슈에 '작업 로그' 댓글 1건으로 POST.

Usage:
  log.py MKT-142            # 산출물을 조합해 댓글 POST
  log.py MKT-142 --dry-run  # POST 없이 조합된 다이제스트를 stdout으로만 출력

Reads:  ~/Documents/tasks/<KEY>/{plan,summary,review,result}.md
        (cruise 하네스가 남긴 산출물. CONTRACT.md v9 스키마)
        PR·커밋 정보는 산출물이 아니라 GitHub(gh)에서 직접 조회한다.
Writes: Jira 이슈 댓글 1건 (기존 add_comment 재사용)
        ~/Documents/tasks/<KEY>/.jsync-log.json  (중복 방지용 해시 상태)
        stdout 1-liner summary
"""
import sys
import json
import re
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import check_deps, tasks_root, log_file, load_settings

check_deps()

import yaml
from jira_client import add_comment
from md_adf import md_to_adf

ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+-\d+$")
STATE_FILE = ".jsync-log.json"


# ---------------------------------------------------------------------------
# Artifact parsing
# ---------------------------------------------------------------------------

def artifact_field(arts: list, field: str) -> str:
    """여러 산출물 frontmatter에서 field의 첫 비어있지 않은 값을 반환."""
    for a in arts:
        if a and a[0].get(field):
            return str(a[0][field])
    return ""


def gh_pr_info(repo: str, branch: str) -> dict | None:
    """gh로 branch에 연결된 PR을 조회. GitHub이 PR·커밋의 단일 진실 원천.

    log.py는 repo 체크아웃 밖(~/Documents/tasks)에서 돌기 때문에 --repo로 조회한다.
    PR이 없거나 gh 미설치/미인증/타임아웃이면 None 반환 (호출측이 섹션을 스킵)."""
    if not repo or not branch:
        return None
    try:
        r = subprocess.run(
            ["gh", "pr", "list", "--repo", repo, "--head", branch,
             "--state", "all", "--limit", "1",
             "--json", "number,url,title,baseRefName,state,commits"],
            capture_output=True, text=True, timeout=20,
        )
    except Exception:
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        arr = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    return arr[0] if arr else None


def read_artifact(d: Path, name: str) -> tuple[dict, str] | None:
    """Read a cruise artifact. Returns (frontmatter, body) or None if absent."""
    p = d / name
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text.strip()
    try:
        end = text.index("---", 3)
    except ValueError:
        return {}, text.strip()
    try:
        fm = yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        fm = {}
    body = text[end + 3:].strip()
    return fm, body


def body_section(body: str, heading: str) -> str:
    """Extract the text under a `## heading` up to the next `## `."""
    lines = body.splitlines()
    out: list[str] = []
    capturing = False
    for line in lines:
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            if capturing:
                break
            capturing = m.group(1).strip().startswith(heading)
            continue
        if capturing:
            out.append(line)
    return "\n".join(out).strip()


def section_bullets(body: str, heading: str, limit: int = 5) -> list[str]:
    """`## heading` 아래 불릿 목록. '- 없음'은 제외."""
    out = []
    for line in body_section(body, heading).splitlines():
        s = line.strip()
        if s.startswith("- ") or s.startswith("* "):
            item = s[2:].strip()
            if item and item != "없음":
                out.append(item)
    return out[:limit]


def section_text(body: str, heading: str) -> str:
    """`## heading` 아래 첫 문단(비불릿) 텍스트."""
    out = []
    for line in body_section(body, heading).splitlines():
        s = line.strip()
        if not s or s.startswith("- ") or s.startswith("* "):
            if out:
                break
            continue
        out.append(s)
    return " ".join(out)


def section_groups(body: str, heading: str, group_limit: int = 5, item_limit: int = 5) -> list[tuple[str, list[str]]]:
    """`## heading` 아래 `### 그룹명` 서브헤딩별로 묶인 불릿 목록.
    서브헤딩이 없으면(구 flat 포맷) 빈 리스트를 반환 — 호출측이 section_bullets로 폴백."""
    groups: list[tuple[str, list[str]]] = []
    name: str | None = None
    items: list[str] = []
    for line in body_section(body, heading).splitlines():
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            if name is not None:
                groups.append((name, items[:item_limit]))
            name = m.group(1).strip()
            items = []
            continue
        s = line.strip()
        if s.startswith("- ") or s.startswith("* "):
            item = s[2:].strip()
            if item and item != "없음":
                items.append(item)
    if name is not None:
        groups.append((name, items[:item_limit]))
    return groups[:group_limit]


# ---------------------------------------------------------------------------
# Digest composition
# ---------------------------------------------------------------------------

def compose(d: Path) -> tuple[str, list[str], str]:
    """Returns (digest_md, present_sections, updated_date)."""
    task = read_artifact(d, "task.md")
    plan = read_artifact(d, "plan.md")
    summary = read_artifact(d, "summary.md")
    review = read_artifact(d, "review.md")
    result = read_artifact(d, "result.md")

    # PR·커밋·머지는 산출물이 아니라 git/GitHub에서 직접 조회한다 (commit.md/pr.md/merge.md 폐지).
    # repo·branch는 남은 cruise 산출물 frontmatter에서 얻는다.
    # 최신 산출물부터 조회 (stale plan.md가 최신 summary.md 이후 값을 덮어쓰지 않도록)
    repo = artifact_field([result, review, summary, plan], "repo")
    branch = artifact_field([result, review, summary, plan], "branch")
    pr = gh_pr_info(repo, branch)  # dict 또는 None(없음/gh 실패 → 섹션 스킵)

    present: list[str] = []
    body_parts: list[str] = []

    # --- most recent `updated` among artifacts, for the header line ---
    updated = ""
    for art in (plan, summary, review, result):
        if art and art[0].get("updated"):
            u = str(art[0]["updated"])
            if u > updated:
                updated = u
    updated_date = updated[:10] if updated else ""

    # --- 해결한 문제 (task.md 배경 → summary 개요 폴백) ---
    problem: list[str] = []
    if task:
        problem = section_bullets(task[1], "배경", limit=4) or [
            ln for ln in section_text(task[1], "배경").splitlines() if ln.strip()
        ][:3]
    if not problem and summary:
        problem = [ln for ln in section_text(summary[1], "개요").splitlines() if ln.strip()][:3]
    if problem:
        present.append("문제")
        body_parts.append("**해결한 문제**\n" + "\n".join(f"- {b}" for b in problem))

    # --- 완료한 작업 / 미해결 (plan.md 요구사항 체크박스) ---
    done, todo = [], []
    if plan:
        req_body = body_section(plan[1], "요구사항")
        for m in re.finditer(r"^-\s*\[([ xX])\]\s*R\d+:\s*(.+?)\s*$", req_body, re.MULTILINE):
            checked, text = m.group(1).lower() == "x", m.group(2).strip()
            if "(철회" in text:          # 철회 항목은 집계·표시에서 제외 (CONTRACT §4a)
                continue
            (done if checked else todo).append(text)
    if done:
        present.append("작업")
        body_parts.append("**완료한 작업**\n" + "\n".join(f"- {t}" for t in done))
    if todo:
        present.append("미해결")
        body_parts.append("**미해결**\n" + "\n".join(f"- {t}" for t in todo))

    # --- 상태 (브랜치 · 검사 · PR) ---
    status_bits = []
    if branch:
        status_bits.append(f"- 브랜치: `{branch}`")
    if summary:
        tools = summary[0].get("check_tools") or {}
        tool_bits = [f"{k} {str(v).upper()}" for k, v in tools.items() if v]
        if tool_bits:
            status_bits.append("- 검사: " + " · ".join(tool_bits))
        elif summary[0].get("check_result"):
            status_bits.append(f"- 검사: {str(summary[0]['check_result']).upper()}")
    if pr:
        pr_num, pr_url = pr.get("number"), pr.get("url") or ""
        st = str(pr.get("state") or "").upper()
        label = f"#{pr_num} {st}".strip()
        status_bits.append(f"- PR: [{label}]({pr_url})" if pr_url else f"- PR: {label}")
    if review:
        iters = review[0].get("iterations") or []
        if iters:
            status_bits.append(f"- 리뷰: {len(iters)}회 반영")
    if status_bits:
        present.append("상태")
        body_parts.append("**상태**\n" + "\n".join(status_bits))

    head_line = f"🚀 작업내역 — {updated_date}" if updated_date else "🚀 작업내역"
    digest = head_line + "\n\n" + "\n\n".join(body_parts)
    return digest, present, updated_date


# ---------------------------------------------------------------------------
# Dedup state
# ---------------------------------------------------------------------------

def content_hash(digest: str) -> str:
    """Hash the digest excluding the volatile header timestamp line."""
    body = digest.split("\n", 1)[1] if "\n" in digest else digest
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_state(d: Path) -> dict:
    p = d / STATE_FILE
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(d: Path, h: str):
    (d / STATE_FILE).write_text(
        json.dumps(
            {"last_hash": h, "last_posted_at": datetime.now(timezone.utc).isoformat()},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = {a for a in sys.argv[1:] if a.startswith("-")}
    dry_run = "--dry-run" in flags

    if not args:
        print("error: KEY required. usage: log.py <KEY> [--dry-run]", file=sys.stderr)
        sys.exit(1)
    key = args[0]

    if not ISSUE_KEY_RE.match(key):
        print(
            f"error: '{key}' is not a Jira issue key (cruise slug 디렉토리로 보임). "
            "댓글은 Jira 이슈에만 남길 수 있습니다.",
            file=sys.stderr,
        )
        sys.exit(1)

    d = tasks_root() / key
    if not d.is_dir():
        print(f"error: no task directory: {d}", file=sys.stderr)
        sys.exit(1)

    digest, present, updated_date = compose(d)
    if not present:
        print(f"no artifacts  {key}  (cruise 산출물이 없습니다)")
        sys.exit(0)

    if dry_run:
        print(digest)
        print(f"\n--- dry-run: {len(present)} sections ({', '.join(present)}) ---", file=sys.stderr)
        return

    h = content_hash(digest)
    state = load_state(d)
    if state.get("last_hash") == h:
        print(f"no changes  {key}  (마지막 로그 이후 변경 없음)")
        return

    try:
        add_comment(key, md_to_adf(digest))
    except Exception as e:
        print(f"error: failed to post comment for {key}: {e}", file=sys.stderr)
        print(f"  자세한 내용: {log_file(key)}", file=sys.stderr)
        sys.exit(1)

    save_state(d, h)
    try:
        base = str(load_settings()["base_url"]).rstrip("/")
        url = f"{base}/browse/{key}"
    except Exception:
        url = ""
    tail = f"  {url}" if url else ""
    print(f"logged {key}: {', '.join(present)} ({len(present)} sections){tail}")


if __name__ == "__main__":
    main()
