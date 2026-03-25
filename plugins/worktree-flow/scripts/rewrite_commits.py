#!/usr/bin/env python3
"""
WIP 커밋들을 의미 있는 단위로 재정의 (git reset --soft + git commit).
Usage: python3 rewrite_commits.py {issue} --branch {branch} --base {base} --groups '{json}'
groups JSON 형식: [{"message": "feat(PLAT-101): ...", "commit_indices": [0,1,2]}, ...]
"""
import argparse, json, os, sys, subprocess, tempfile

def run(cmd, cwd=None, input=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, input=input)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def find_git_root():
    common, _, _ = run("git rev-parse --git-common-dir")
    if common:
        return os.path.abspath(os.path.join(common, ".."))
    out, _, _ = run("git rev-parse --show-toplevel")
    return out or None

def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False, indent=2))
    sys.exit(0)

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("issue")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--groups", required=True, help="JSON 배열 문자열")
    args = parser.parse_args()

    try:
        groups = json.loads(args.groups)
    except json.JSONDecodeError as e:
        error("INVALID_JSON", f"groups JSON 파싱 실패: {e}")

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    # 현재 브랜치 저장
    orig_branch, _, _ = run("git rev-parse --abbrev-ref HEAD", cwd=root)

    # 워크트리 브랜치로 이동
    _, err, code = run(f"git checkout '{args.branch}'", cwd=root)
    if code != 0:
        error("CHECKOUT_FAILED", f"브랜치 체크아웃 실패: {err}")

    # base로 soft reset
    _, err, code = run(f"git reset --soft {args.base}", cwd=root)
    if code != 0:
        run(f"git checkout '{orig_branch}'", cwd=root)
        error("RESET_FAILED", f"git reset --soft 실패: {err}")

    # 그룹별 커밋 (모든 변경사항이 스테이징된 상태)
    # 단일 그룹이면 한 번에, 복수면 순서대로 부분 스테이징은 불가하므로 전체를 하나로
    if len(groups) == 1:
        msg = groups[0]["message"]
        wip_list_out, _, _ = run(f"git log {args.base}..HEAD --oneline 2>/dev/null || echo ''", cwd=root)
        body = f"\nSquashed WIP commits:\n" + "\n".join(f"- {c}" for c in wip_list_out.split("\n") if c)
        full_msg = msg + body

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tf:
            tf.write(full_msg)
            tf_path = tf.name

        _, err, code = run(f"git commit -F '{tf_path}'", cwd=root)
        os.unlink(tf_path)
        if code != 0:
            error("COMMIT_FAILED", f"커밋 실패: {err}")
    else:
        # 복수 그룹: 전체를 하나로 커밋 후 메시지에 그룹 정보 포함
        # (파일 단위 분할은 사용자가 직접 하는 경우에 해당, 여기선 메시지만 통합)
        messages = "\n".join(f"- {g['message']}" for g in groups)
        wip_list_out, _, _ = run(f"git log {args.base}..HEAD --oneline 2>/dev/null || echo ''", cwd=root)
        body = f"\nSquashed WIP commits:\n" + "\n".join(f"- {c}" for c in wip_list_out.split("\n") if c)
        full_msg = f"{groups[0]['message']}\n\nAdditional changes:\n{messages}{body}"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tf:
            tf.write(full_msg)
            tf_path = tf.name

        _, err, code = run(f"git commit -F '{tf_path}'", cwd=root)
        os.unlink(tf_path)
        if code != 0:
            error("COMMIT_FAILED", f"커밋 실패: {err}")

    # 원래 브랜치로 복귀
    run(f"git checkout '{orig_branch}'", cwd=root)

    ok({"issue": args.issue, "branch": args.branch, "groups_count": len(groups)})

if __name__ == "__main__":
    main()
