"""
jsync log — cruise 단계별 산출물을 모아 Jira 이슈에 '작업 로그' 댓글 1건으로 POST.

Usage:
  log.py MKT-142            # 산출물을 조합해 댓글 POST
  log.py MKT-142 --dry-run  # POST 없이 조합된 다이제스트를 stdout으로만 출력

Reads:  ~/Documents/tasks/<KEY>/{plan,build,summary,check,commit,merge,pr,review}.md
        (cruise 하네스가 남긴 산출물. CONTRACT.md v3 §4 스키마)
Writes: Jira 이슈 댓글 1건 (기존 add_comment 재사용)
        ~/Documents/tasks/<KEY>/.jsync-log.json  (중복 방지용 해시 상태)
        stdout 1-liner summary
"""
import sys
import json
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import check_deps, STORE_ROOT, log_file

check_deps()

import yaml
from jira_client import add_comment
from md_adf import md_to_adf

ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+-\d+$")
STATE_FILE = ".jsync-log.json"


# ---------------------------------------------------------------------------
# Artifact parsing
# ---------------------------------------------------------------------------

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


def first_title(body: str) -> str:
    """First markdown heading or first non-empty line — used as PR title."""
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        return re.sub(r"^#+\s*", "", s)
    return ""


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


# ---------------------------------------------------------------------------
# Digest composition
# ---------------------------------------------------------------------------

def compose(d: Path) -> tuple[str, list[str], str]:
    """Returns (digest_md, present_sections, updated_date)."""
    plan = read_artifact(d, "plan.md")
    build = read_artifact(d, "build.md")
    summary = read_artifact(d, "summary.md")
    check = read_artifact(d, "check.md")
    commit = read_artifact(d, "commit.md")
    merge = read_artifact(d, "merge.md")
    pr = read_artifact(d, "pr.md")
    review = read_artifact(d, "review.md")
    result = read_artifact(d, "result.md")

    present: list[str] = []
    body_parts: list[str] = []

    # --- most recent `updated` among artifacts, for the header line ---
    updated = ""
    for art in (plan, build, summary, check, commit, merge, pr, review, result):
        if art and art[0].get("updated"):
            u = str(art[0]["updated"])
            if u > updated:
                updated = u
    updated_date = updated[:10] if updated else ""

    # --- status header ---
    merge_entries = (merge[0].get("entries") if merge else None) or []
    if result and result[0].get("outcome"):
        # result.md의 outcome이 가장 권위 있는 최종 상태
        state = str(result[0]["outcome"])
    elif merge_entries:
        state = "merged"
    elif pr:
        state = "PR open"
    elif commit:
        state = "committed"
    else:
        state = "in progress"

    header_bits = [f"**상태:** {state}"]
    if pr:
        pr_num = pr[0].get("pr_number")
        pr_url = pr[0].get("pr_url") or ""
        if pr_num and pr_url:
            header_bits.append(f"PR [#{pr_num}]({pr_url})")
        elif pr_num:
            header_bits.append(f"PR #{pr_num}")
    if commit and commit[0].get("commits_count") is not None:
        header_bits.append(f"{commit[0]['commits_count']} commits")
    if check and check[0].get("result"):
        header_bits.append(f"check {str(check[0]['result']).upper()}")
    header = " · ".join(header_bits)

    # --- Plan ---
    if plan:
        present.append("plan")
        lines = ["### 📋 Plan"]
        summ = plan[0].get("summary")
        if summ:
            lines.append(str(summ))
        meta_bits = []
        if plan[0].get("phases_count") is not None:
            meta_bits.append(f"Phases {plan[0]['phases_count']}")
        req_body = body_section(plan[1], "요구사항")
        # 신 포맷: `- [ ] R1: ...` 체크리스트 우선, 구 포맷: 평범한 불릿 fallback
        reqs = re.findall(r"^-\s*\[[ xX]\]\s*(R\d+:.*)$", req_body, re.MULTILINE)
        req_count = len(reqs) if reqs else len(re.findall(r"^-\s+\S", req_body, re.MULTILINE))
        if req_count:
            meta_bits.append(f"요구사항 {req_count}건")
        if meta_bits:
            lines.append("- " + " · ".join(meta_bits))
        for r in reqs[:8]:
            lines.append(f"- {r.strip()}")
        body_parts.append("\n".join(lines))

    # --- Build ---
    if build or summary:
        present.append("build")
        lines = ["### 🔨 Build"]
        bits = []
        if build and build[0].get("runs_count") is not None:
            bits.append(f"Runs {build[0]['runs_count']}")
        if summary:
            fc = summary[0].get("files_changed")
            ins = summary[0].get("insertions")
            dels = summary[0].get("deletions")
            if fc is not None:
                bits.append(f"변경 {fc} files (+{ins or 0} / -{dels or 0})")
        lines.append("- " + " · ".join(bits) if bits else "- (기록 없음)")
        body_parts.append("\n".join(lines))

    # --- Check ---
    if check:
        present.append("check")
        lines = ["### ✅ Check"]
        tools = check[0].get("tools") or {}
        tool_bits = [f"{k} {str(v).upper()}" for k, v in tools.items() if v]
        detail = " · ".join(tool_bits) if tool_bits else str(check[0].get("result", "")).upper()
        rc = check[0].get("requirements_checked")
        if rc is not None:
            detail += f" · 요구사항 검증 {rc}건"
        lines.append(f"- {detail}".rstrip())
        body_parts.append("\n".join(lines))

    # --- Commits ---
    if commit:
        present.append("commit")
        commits = commit[0].get("commits") or []
        cnt = commit[0].get("commits_count", len(commits))
        lines = [f"### 📦 Commits ({cnt})"]
        for c in commits[:20]:
            sha = str(c.get("sha", ""))[:7]
            msg = str(c.get("message", "")).splitlines()[0] if c.get("message") else ""
            lines.append(f"- `{sha}` {msg}".rstrip())
        if len(commits) > 20:
            lines.append(f"- … 외 {len(commits) - 20}건")
        body_parts.append("\n".join(lines))

    # --- PR ---
    if pr:
        present.append("pr")
        lines = ["### 🔀 PR"]
        title_body = body_section(pr[1], "제목")
        title = title_body.splitlines()[0].strip() if title_body else first_title(pr[1])
        pr_num = pr[0].get("pr_number")
        pr_url = pr[0].get("pr_url") or ""
        base = pr[0].get("base_branch")
        label = f"#{pr_num} {title}".strip() if pr_num else (title or "PR")
        entry = f"- [{label}]({pr_url})" if pr_url else f"- {label}"
        if base:
            entry += f" → base `{base}`"
        lines.append(entry)
        body_parts.append("\n".join(lines))

    # --- Review ---
    if review:
        present.append("review")
        iters = review[0].get("iterations") or []
        lines = ["### 👀 Review"]
        bits = [f"{len(iters)} iterations"]
        if iters:
            last = iters[-1]
            if last.get("validation"):
                bits.append(f"validation {last['validation']}")
        lines.append("- " + " · ".join(bits))
        body_parts.append("\n".join(lines))

    # --- Merge ---
    if merge_entries:
        present.append("merge")
        lines = ["### 🔗 Merge"]
        for e in merge_entries:
            src = e.get("source", "")
            tgt = e.get("target", "")
            conf = e.get("conflicts_count", 0)
            lines.append(f"- {tgt} ← {src} (conflicts {conf})")
        body_parts.append("\n".join(lines))

    # --- 회고 (result.md) ---
    if result:
        rbody = result[1]
        outcome_line = section_text(rbody, "결과")
        fails = section_bullets(rbody, "어려웠던 점")
        decisions = section_bullets(rbody, "결정")
        wins = section_bullets(rbody, "잘된 점")
        if outcome_line or fails or decisions or wins:
            present.append("result")
            lines = ["### 📝 회고"]
            if outcome_line:
                lines.append(outcome_line)
            if wins:
                lines.append("**잘된 점:**")
                lines += [f"- {b}" for b in wins]
            if fails:
                lines.append("**어려웠던 점 / 실패:**")
                lines += [f"- {b}" for b in fails]
            if decisions:
                lines.append("**결정:**")
                lines += [f"- {b}" for b in decisions]
            body_parts.append("\n".join(lines))

    head_line = f"🚢 cruise 작업 로그 — {updated_date}" if updated_date else "🚢 cruise 작업 로그"
    digest = head_line + "\n\n" + header + "\n\n" + "\n\n".join(body_parts)
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

    d = STORE_ROOT / key
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
    print(f"logged {key}: {', '.join(present)} ({len(present)} sections)")


if __name__ == "__main__":
    main()
