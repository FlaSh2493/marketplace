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
from common import check_deps, tasks_root, log_file

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
    pr_commits = pr.get("commits") if isinstance(pr, dict) else None
    pr_commits = pr_commits if isinstance(pr_commits, list) else []

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

    # --- status header ---
    pr_state = (pr.get("state") if pr else "") or ""
    if result and result[0].get("outcome"):
        # result.md의 outcome이 가장 권위 있는 최종 상태
        state = str(result[0]["outcome"])
    elif pr_state == "MERGED":
        state = "merged"
    elif pr_state == "OPEN":
        state = "PR open"
    elif pr:
        state = f"PR {pr_state.lower()}"
    else:
        state = "in progress"

    header_bits = [f"**상태:** {state}"]
    if pr:
        pr_num = pr.get("number")
        pr_url = pr.get("url") or ""
        if pr_num and pr_url:
            header_bits.append(f"PR [#{pr_num}]({pr_url})")
        elif pr_num:
            header_bits.append(f"PR #{pr_num}")
    if pr_commits:
        header_bits.append(f"{len(pr_commits)} commits")
    if summary and summary[0].get("check_result"):
        header_bits.append(f"check {str(summary[0]['check_result']).upper()}")
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

    # --- Build (개요 + 변경 파일 + 검사 결과, 모두 summary.md에서) ---
    if summary:
        present.append("build")
        lines = ["### 🔨 Build"]
        overview = section_text(summary[1], "개요")
        if overview:
            lines.append(overview)

        bits = []
        fc = summary[0].get("files_changed")
        ins = summary[0].get("insertions")
        dels = summary[0].get("deletions")
        if fc is not None:
            bits.append(f"변경 {fc} files (+{ins or 0} / -{dels or 0})")
        fa = summary[0].get("fix_attempts")
        if fa:
            bits.append(f"수정 시도 {fa}회")
        lines.append("- " + " · ".join(bits) if bits else "- (기록 없음)")

        groups = section_groups(summary[1], "변경 파일")
        if groups:
            lines.append("**변경 파일:**")
            for name, items in groups:
                lines.append(f"- {name}")
                lines += [f"  - {it}" for it in items]
        else:
            changed = section_bullets(summary[1], "변경 파일", limit=6)
            if changed:
                lines.append("**변경 파일:**")
                lines += [f"- {c}" for c in changed]

        # 검사·검증 결과 (build 스킬이 summary.md frontmatter에 흡수)
        tools = summary[0].get("check_tools") or {}
        tool_bits = [f"{k} {str(v).upper()}" for k, v in tools.items() if v]
        detail = " · ".join(tool_bits) if tool_bits else str(summary[0].get("check_result", "")).upper()
        rc = summary[0].get("requirements_checked")
        if rc is not None:
            detail += f" · 요구사항 검증 {rc}건"
        if detail.strip():
            lines.append(f"- {detail}".rstrip())
        body_parts.append("\n".join(lines))

    # --- Commits (GitHub PR에서 파생. PR 없으면 스킵) ---
    if pr_commits:
        present.append("commit")
        cnt = len(pr_commits)
        lines = [f"### 📦 Commits ({cnt})"]
        for c in pr_commits[:20]:
            sha = str(c.get("oid", ""))[:7]
            msg = str(c.get("messageHeadline", "")).strip()
            lines.append(f"- `{sha}` {msg}".rstrip())
        if cnt > 20:
            lines.append(f"- … 외 {cnt - 20}건")
        body_parts.append("\n".join(lines))

    # --- PR (GitHub에서 직접 조회. 없으면 스킵) ---
    if pr:
        present.append("pr")
        lines = ["### 🔀 PR"]
        title = str(pr.get("title", "")).strip()
        pr_num = pr.get("number")
        pr_url = pr.get("url") or ""
        base = pr.get("baseRefName")
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
    print(f"logged {key}: {', '.join(present)} ({len(present)} sections)")


if __name__ == "__main__":
    main()
