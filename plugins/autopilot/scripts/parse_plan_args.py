#!/usr/bin/env python3
"""
/autopilot:plan 인수를 파싱하여 구조화된 JSON을 반환한다.
Usage: python3 parse_plan_args.py [args...]
Exit 0: ok  Exit 1: error
"""
import json, re, sys


ISSUE_KEY_RE = re.compile(r"^[A-Z]+-[0-9]+$")


def slugify(text):
    """이슈키를 브랜치명 슬러그로 변환 (소문자, 특수문자→하이픈)"""
    s = text.lower()
    s = re.sub(r"[^a-z0-9._-]", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:64]


def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)


def error(reason):
    print(json.dumps({"status": "error", "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def main():
    args = sys.argv[1:]

    # 플래그 추출
    no_spec = "--no-spec" in args
    # --replan 제거됨
    args = [a for a in args if a != "--no-spec"]

    # -b 브랜치명 추출
    custom_branch = None
    if "-b" in args:
        idx = args.index("-b")
        if idx + 1 >= len(args):
            error("-b 다음에 브랜치명이 필요합니다")
        custom_branch = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    # 나머지 인수 분류: 이슈키 vs 브랜치명
    issues = []
    positional_branch = None

    for i, arg in enumerate(args):
        if ISSUE_KEY_RE.match(arg):
            issues.append(arg)
        elif i == 0 and not issues:
            positional_branch = arg

    # -b + 이슈 여러 개 → 에러
    if custom_branch and len(issues) > 1:
        error("에러: -b는 이슈 1개일 때만 사용 가능합니다")

    # 브랜치명 결정
    if custom_branch:
        branch = custom_branch
    elif positional_branch:
        branch = positional_branch
    elif len(issues) == 1:
        branch = f"feat/{slugify(issues[0])}"
    else:
        branch = None

    # mode 결정
    if no_spec:
        mode = "no-spec"
    elif len(issues) > 1:
        mode = "multi"
    elif len(issues) == 1:
        mode = "single"
    else:
        mode = "no-issues"

    # 다중 이슈: 브랜치별 매핑 생성
    branches = {}
    if mode == "multi":
        for issue in issues:
            branches[issue] = f"feat/{slugify(issue)}"

    data = {
        "issues": issues,
        "branch": branch,
        "mode": mode,
        "flags": {
          "no_spec": no_spec,
        }
    }
    # multi 모드일 때만 branches 추가
    if branches:
        data["branches"] = branches

    ok(data)


if __name__ == "__main__":
    main()
