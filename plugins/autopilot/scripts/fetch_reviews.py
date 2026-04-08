#!/usr/bin/env python3
"""
PR의 CodeRabbit 리뷰 코멘트를 수집하고 필터링한다.
Usage: python3 fetch_reviews.py {owner_repo} {pr_number} {worktree_path} [--pushed-at {ISO8601}]
Exit 0: ok (data.has_reviews, data.active_count, data.comments[], ...)
Exit 1: error
"""
import argparse, json, os, subprocess, sys
from datetime import datetime, timezone


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def gh(endpoint, extra=""):
    out, err, rc = run(f"gh api {endpoint} --paginate {extra}")
    if rc != 0:
        error("GH_API_FAILED", f"gh api 실패: {err or out}")
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        error("GH_PARSE_FAILED", f"gh api 응답 파싱 실패: {out[:200]}")


def is_outdated(path, worktree_path):
    """파일이 워크트리에 존재하지 않으면 outdated"""
    _, _, rc = run(f"git ls-files --error-unmatch '{path}'", cwd=worktree_path)
    return rc != 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("owner_repo")
    parser.add_argument("pr_number")
    parser.add_argument("worktree_path")
    parser.add_argument("--pushed-at", dest="pushed_at", default=None)
    args = parser.parse_args()

    owner_repo = args.owner_repo
    pr_number = args.pr_number
    worktree_path = os.path.abspath(args.worktree_path)
    pushed_at = args.pushed_at

    # 1. PR 코멘트 전체 수집
    raw_comments = gh(f"repos/{owner_repo}/pulls/{pr_number}/comments",
                      "--jq '.'")
    if not isinstance(raw_comments, list):
        raw_comments = []

    # 2. CodeRabbit 코멘트만 필터
    cr_comments = [c for c in raw_comments if c.get("user", {}).get("login") == "coderabbitai[bot]"]

    # 3. resolved (+1 reaction) 판별
    def is_resolved(comment):
        reactions = comment.get("reactions", {})
        return (reactions.get("+1", 0) or 0) > 0

    # 4. 스레드 합산: in_reply_to_id 기준으로 후속 코멘트를 최초 코멘트에 합산
    root_comments = {}   # id -> comment
    reply_comments = {}  # in_reply_to_id -> [comments]

    for c in cr_comments:
        if c.get("in_reply_to_id") is None:
            root_comments[c["id"]] = dict(c)
        else:
            pid = c["in_reply_to_id"]
            reply_comments.setdefault(pid, []).append(c)

    # 후속 코멘트 body를 최초 코멘트에 append
    for root_id, replies in reply_comments.items():
        if root_id in root_comments:
            for r in sorted(replies, key=lambda x: x.get("created_at", "")):
                root_comments[root_id]["body"] = (
                    root_comments[root_id]["body"] + "\n---\n" + r["body"]
                )

    # 5. 활성 코멘트 필터링
    active_comments = []
    for c in root_comments.values():
        if is_resolved(c):
            continue
        path = c.get("path", "")
        if path and is_outdated(path, worktree_path):
            continue
        active_comments.append({
            "id": c["id"],
            "path": path,
            "line": c.get("line") or c.get("original_line"),
            "side": c.get("side", "RIGHT"),
            "body": c["body"],
            "diff_hunk": c.get("diff_hunk", ""),
            "created_at": c.get("created_at", ""),
            "in_reply_to_id": c.get("in_reply_to_id"),
        })

    # 6. PR 리뷰 수집 (맥락용 review body)
    reviews = gh(f"repos/{owner_repo}/pulls/{pr_number}/reviews", "--jq '.'")
    if not isinstance(reviews, list):
        reviews = []

    cr_reviews = [r for r in reviews if r.get("user", {}).get("login") == "coderabbitai[bot]"]
    has_reviews = len(cr_reviews) > 0
    review_bodies = [r.get("body", "") for r in cr_reviews if r.get("body")]

    # 7. pushed_at 이후 새 코멘트 여부
    new_since_push = False
    if pushed_at:
        new_since_push = any(
            c.get("created_at", "") > pushed_at for c in cr_comments
        )

    ok({
        "has_reviews": has_reviews,
        "active_count": len(active_comments),
        "total_count": len(root_comments),
        "new_since_push": new_since_push,
        "review_bodies": review_bodies,
        "comments": active_comments,
    })


if __name__ == "__main__":
    main()
