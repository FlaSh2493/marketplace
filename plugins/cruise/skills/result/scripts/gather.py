#!/usr/bin/env python3
"""
result.md 작성용 결정적 필드 수집기.

~/Documents/tasks/<KEY>/ 의 형제 산출물 frontmatter에서 스칼라 필드를 긁어
result.md frontmatter에 그대로 복사할 값들을 JSON으로 출력한다.
에이전트는 본문 학습(잘된 점/실패/결정/사용 기술)만 하면 된다.

result.md frontmatter는 공통 5필드 + outcome 뿐이다 (CONTRACT §5, v9).
PR·커밋·이슈키·base 등은 산출물에 담지 않으므로 여기서도 계산하지 않는다
(소비자가 gh/git·본문에서 파생). outcome 도출에 필요한 gh PR '상태'만 조회한다.

Usage: python3 gather.py <KEY>
Output: JSON {summary, branch, repo, outcome, now}
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# 플러그인 공용 스크립트(common.py)를 import — tasks_root 단일 소스.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from common import tasks_root  # noqa: E402

# commit.md/pr.md 는 폐지 — PR·커밋은 GitHub(gh)에서 파생한다.
ARTIFACTS = ["task", "plan", "summary", "review", "result"]


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.returncode


def gh_pr_state(repo: str, branch: str) -> str:
    """gh로 branch에 연결된 PR의 상태만 조회 (outcome 도출용).

    반환: "MERGED" | "OPEN" | "CLOSED" | "" (PR 없음/gh 실패).
    PR URL·번호·커밋 수는 산출물에 담지 않으므로 조회하지 않는다 — 소비자가 gh로 직접 파생."""
    if not repo or not branch:
        return ""
    out, rc = run(
        f"gh pr list --repo {repo} --head {branch} --state all "
        f"--json state --limit 1"
    )
    if rc != 0 or not out:
        return ""
    try:
        arr = json.loads(out)
    except Exception:
        return ""
    return (arr[0].get("state") or "") if arr else ""


def load_context():
    """동일 플러그인의 context.py 를 현재 repo CWD에서 실행해 live git 정보 획득."""
    ctx_py = Path(__file__).resolve().parents[3] / "scripts" / "context.py"
    try:
        out, rc = run(f'python3 "{ctx_py}"')
        return json.loads(out) if rc == 0 and out else {}
    except Exception:
        return {}


def read_frontmatter(path: Path) -> dict:
    """--- ... --- 사이의 최상위 스칼라 라인만 파싱 (중첩/리스트는 무시)."""
    if not path.exists():
        return {}
    fm = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        # 들여쓰기 있는 라인(중첩 값)은 건너뜀
        if line[:1] in (" ", "\t"):
            continue
        m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        # 따옴표 제거
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        fm[key] = val
    return fm


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "USAGE: gather.py <KEY>"}))
        sys.exit(1)
    key = sys.argv[1]
    tasks_dir = tasks_root() / key

    fms = {name: read_frontmatter(tasks_dir / f"{name}.md") for name in ARTIFACTS}

    # summary: task.md 우선, 없으면 cruise 산출물에서
    def pick(field, order):
        for name in order:
            v = fms.get(name, {}).get(field)
            if v:
                return v
        return ""

    summary = pick("summary", ["task", "plan", "summary"])
    # branch/repo: cruise 산출물에서 (Jira task.md에는 없음)
    cruise_order = ["review", "summary", "plan", "task"]
    repo = pick("repo", cruise_order)

    # branch: frontmatter 기록값(작업 시점 권위)을 우선.
    fm_branch = pick("branch", cruise_order)
    ctx = load_context()
    ctx_branch = ctx.get("branch") or ""
    branch = fm_branch or ctx_branch

    # 현재 CWD가 이 task의 체크아웃일 때만 live git repo를 폴백으로 신뢰.
    in_task_checkout = bool(ctx_branch) and (not fm_branch or fm_branch == ctx_branch)
    if not repo and in_task_checkout:
        repo = ctx.get("repo") or ""

    # outcome 도출: cancelled 산출물이 있으면 abandoned, 아니면 gh PR 상태로.
    # PR URL·번호·커밋 수는 산출물에 담지 않으므로 조회하지 않는다 (소비자가 gh로 파생).
    statuses = {fms.get(n, {}).get("status") for n in cruise_order}
    pr_state = gh_pr_state(repo, branch)
    if "cancelled" in statuses:
        outcome = "abandoned"
    elif pr_state == "MERGED":
        outcome = "merged"
    elif pr_state:                    # OPEN/CLOSED 등 PR이 존재
        outcome = "shipped"
    else:
        outcome = "in-progress"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    result = {
        "summary": summary,
        "branch": branch,
        "repo": repo,
        "outcome": outcome,
        "now": now,
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
