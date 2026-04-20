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

    no_spec = "--no-spec" in args
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

    # 이슈 2개 이상은 지원하지 않음
    if len(issues) > 1:
        error(f"이슈는 1개만 지정할 수 있습니다. 입력된 이슈: {', '.join(issues)}\n각 이슈는 별도 워크트리에서 독립적으로 실행하세요.")

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
    elif len(issues) == 1:
        mode = "single"
    else:
        mode = "no-issues"

    issue = issues[0] if issues else ""

    data = {
        "issue": issue,
        "branch": branch,
        "mode": mode,
        "flags": {
            "no_spec": no_spec,
        },
    }

    ok(data)


if __name__ == "__main__":
    main()
