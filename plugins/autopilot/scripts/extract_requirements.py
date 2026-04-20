#!/usr/bin/env python3
"""
로그에서 요구사항 추출 및 이슈 문서 마크다운 조작.
Usage:
  python3 extract_requirements.py extract-log {wt_path} {target_branch}
  python3 extract_requirements.py upsert-doc {md_path} --req-items item1 item2 ... --api-rows row1 row2 ...
"""
import json, os, re, subprocess, sys
from datetime import datetime

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def extract_log(wt_path, target_branch):
    # Find MERGE_BASE
    # git merge-base "origin/{target_branch}" HEAD 2>/dev/null || git merge-base "{target_branch}" HEAD 2>/dev/null
    cmd = (f'MERGE_BASE=$(git merge-base "origin/{target_branch}" HEAD 2>/dev/null || '
           f'git merge-base "{target_branch}" HEAD 2>/dev/null) && '
           f'[ -n "$MERGE_BASE" ] && git log "$MERGE_BASE"..HEAD --format="%s%n%b" || echo "MERGE_BASE_NOT_FOUND"')
    out, _, _ = run(cmd, cwd=wt_path)
    
    if out == "MERGE_BASE_NOT_FOUND":
        return {"status": "error", "reason": "MERGE_BASE_NOT_FOUND"}
    
    reqs = []
    for line in out.splitlines():
        if line.strip().startswith("요구사항:"):
            reqs.append(line.replace("요구사항:", "").strip())
    
    # De-duplicate while preserving order
    seen = set()
    unique_reqs = [x for x in reqs if not (x in seen or seen.add(x))]
    
    return {"status": "ok", "data": {"requirements": unique_reqs, "log": out}}

def upsert_doc(md_path, req_items, api_rows):
    if not os.path.exists(md_path):
        return {"status": "error", "reason": "FILE_NOT_FOUND"}

    content = open(md_path).read()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. ## 추가 요구사항 append
    if req_items:
        new_req_block = f"\n<!-- req {now} -->\n" + "\n".join([f"- {item}" for item in req_items]) + "\n"
        
        if "## 추가 요구사항" in content:
            # 섹션 뒤에 추가 (다른 섹션 시작 전까지 찾기)
            pattern = r"(## 추가 요구사항.*?)(\n## |$)"
            def repl(m):
                return m.group(1).rstrip() + "\n" + new_req_block + m.group(2)
            content = re.sub(pattern, repl, content, flags=re.DOTALL)
        else:
            content = content.rstrip() + "\n\n## 추가 요구사항\n" + new_req_block

    # 2. ## 사용 API 목록 upsert (replace or create)
    if api_rows is not None:
        api_header = "| 메서드 | 엔드포인트 | 호출 위치 |\n|--------|-----------|----------|\n"
        api_table = api_header + "\n".join(api_rows) + "\n"
        if not api_rows:
            api_table = "(없음 — 신규 API 작성 필요)\n"
            
        new_api_block = "\n## 사용 API 목록\n\n" + api_table
        
        if "## 사용 API 목록" in content:
            # 섹션 전체 교체
            pattern = r"## 사용 API 목록.*?(?=\n## |$)"
            content = re.sub(pattern, new_api_block.strip(), content, flags=re.DOTALL)
        else:
            content = content.rstrip() + "\n\n" + new_api_block

    with open(md_path, "w") as f:
        f.write(content)

    return {"status": "ok"}

def main():
    if len(sys.argv) < 2:
        print("Usage: extract_requirements.py {extract-log|upsert-doc} ...", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "extract-log":
        wt_path = sys.argv[2]
        target_branch = sys.argv[3]
        print(json.dumps(extract_log(wt_path, target_branch), ensure_ascii=False))
    elif cmd == "upsert-doc":
        md_path = sys.argv[2]
        
        req_items = []
        if "--req-items" in sys.argv:
            idx = sys.argv.index("--req-items")
            # 다음 flag 전까지 수집
            for i in range(idx + 1, len(sys.argv)):
                if sys.argv[i].startswith("--"): break
                req_items.append(sys.argv[i])
        
        api_rows = None
        if "--api-rows" in sys.argv:
            api_rows = []
            idx = sys.argv.index("--api-rows")
            for i in range(idx + 1, len(sys.argv)):
                if sys.argv[i].startswith("--"): break
                api_rows.append(sys.argv[i])
        
        print(json.dumps(upsert_doc(md_path, req_items, api_rows), ensure_ascii=False))

if __name__ == "__main__":
    main()
