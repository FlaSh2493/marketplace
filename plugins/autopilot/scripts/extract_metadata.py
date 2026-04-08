#!/usr/bin/env python3
"""
이슈 키워드로 코드베이스에서 API 엔드포인트와 상태관리 패턴을 자동 추출한다.
Usage: python3 extract_metadata.py {worktree_path} --keywords kw1 kw2 ...
Exit 0: ok (data.apis[], data.states[])
Exit 1: error
"""
import argparse, json, os, subprocess, sys


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def extract_apis(worktree_path, keywords):
    """API 호출 파일에서 엔드포인트 추출"""
    apis = []

    # API 호출 패턴이 있는 파일 탐색
    api_pattern = r"(fetch|axios|apiClient|useMutation|useQuery|useInfiniteQuery)\("
    out, _, rc = run(
        f"rg -n \"{api_pattern}\" --type ts -l | head -20",
        cwd=worktree_path
    )
    if rc != 0 or not out:
        return apis

    candidate_files = out.splitlines()

    # 키워드와 관련된 파일만 필터
    relevant_files = []
    for f in candidate_files:
        for kw in keywords:
            check_out, _, _ = run(f"grep -l '{kw}' '{f}' 2>/dev/null", cwd=worktree_path)
            if check_out:
                relevant_files.append(f)
                break

    if not relevant_files:
        relevant_files = candidate_files[:5]  # fallback: 상위 5개

    # 각 파일에서 엔드포인트 추출
    endpoint_pattern = r"['\"`](/api/[^'\"`\s]+|/v\d+/[^'\"`\s]+)['\"`]"
    for f in relevant_files:
        out, _, rc = run(f"rg -n \"{endpoint_pattern}\" '{f}'", cwd=worktree_path)
        if rc != 0 or not out:
            continue
        for line in out.splitlines():
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            lineno = parts[1]
            content = parts[2]
            # 메서드 추론 (fetch/axios/apiClient 패턴)
            method = "GET"
            content_lower = content.lower()
            if any(m in content_lower for m in ["post(", ".post", "method: 'post'", 'method: "post"']):
                method = "POST"
            elif any(m in content_lower for m in ["put(", ".put", "method: 'put'", 'method: "put"']):
                method = "PUT"
            elif any(m in content_lower for m in ["patch(", ".patch", "method: 'patch'"]):
                method = "PATCH"
            elif any(m in content_lower for m in ["delete(", ".delete", "method: 'delete'"]):
                method = "DELETE"

            # 엔드포인트 추출
            import re
            endpoints = re.findall(r"['\"`](/(?:api|v\d+)/[^'\"`\s]+)['\"`]", content)
            for ep in endpoints:
                rel_file = os.path.relpath(f, worktree_path) if os.path.isabs(f) else f
                apis.append({"method": method, "endpoint": ep, "file": rel_file})

    # 중복 제거
    seen = set()
    unique_apis = []
    for a in apis:
        key = (a["method"], a["endpoint"])
        if key not in seen:
            seen.add(key)
            unique_apis.append(a)

    return unique_apis


def extract_states(worktree_path, keywords):
    """상태관리 패턴에서 관련 store/hook 추출"""
    states = []

    state_pattern = r"(useStore|create\(|atom\(|useState|useReducer|useContext)"
    out, _, rc = run(
        f"rg -n \"{state_pattern}\" --type ts -l | head -10",
        cwd=worktree_path
    )
    if rc != 0 or not out:
        return states

    candidate_files = out.splitlines()

    # 키워드와 관련된 파일 필터
    relevant_files = []
    for f in candidate_files:
        for kw in keywords:
            check_out, _, _ = run(f"grep -l '{kw}' '{f}' 2>/dev/null", cwd=worktree_path)
            if check_out:
                relevant_files.append(f)
                break

    for f in relevant_files:
        rel_file = os.path.relpath(f, worktree_path) if os.path.isabs(f) else f
        # store/hook 이름 추출
        out, _, _ = run(f"rg -n \"{state_pattern}\" '{f}'", cwd=worktree_path)
        if out:
            import re
            names = re.findall(r"(?:const|let)\s+(\w+)\s*=\s*(?:useStore|create|atom|useState|useReducer|useContext)", out)
            for name in names:
                states.append({"store": os.path.basename(f), "state_name": name, "file": rel_file})

    return states


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("worktree_path")
    parser.add_argument("--keywords", nargs="+", default=[])
    args = parser.parse_args()

    worktree_path = os.path.abspath(args.worktree_path)
    if not os.path.isdir(worktree_path):
        error("NOT_A_DIR", f"디렉토리가 아닙니다: {worktree_path}")

    keywords = args.keywords or []

    apis = extract_apis(worktree_path, keywords)
    states = extract_states(worktree_path, keywords)

    ok({"apis": apis, "states": states})


if __name__ == "__main__":
    main()
