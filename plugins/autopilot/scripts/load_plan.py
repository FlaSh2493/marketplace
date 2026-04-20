#!/usr/bin/env python3
"""
plan.md를 파싱하여 구조화된 JSON으로 반환한다.
Phases 또는 구현 순서 섹션을 탐색한다.
"""
import json, os, re, sys
from pathlib import Path

def parse_yaml(content):
    """정규식 기반 간단한 YAML 파서 (PyYAML 대용)"""
    data = {}
    for line in content.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            elif val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            data[key] = val
    return data

def extract_steps_from_phases(content):
    phases = []
    phase_blocks = re.split(r"### Phase \d+:", content)[1:]
    titles = re.findall(r"### Phase \d+: (.*)", content)

    for i, block in enumerate(phase_blocks):
        title = titles[i].strip() if i < len(titles) else f"Phase {i+1}"

        files = []
        files_match = re.search(r"- 대상 파일:\s*\n((?:\s{2,}- .*\n?)+)", block)
        if files_match:
            files = [f.strip("- ").split(" ")[0].strip() for f in files_match.group(1).strip().splitlines()]

        steps = []
        steps_match = re.search(r"- 작업:\s*\n((?:\s{2,}\d+\. .*\n?)+)", block)
        if steps_match:
            for line in steps_match.group(1).strip().splitlines():
                m = re.match(r"\s*\d+\.\s*(.*)", line)
                if m:
                    steps.append({"text": m.group(1).strip(), "files": files})

        phases.append({
            "idx": i + 1,
            "title": title,
            "files": files,
            "steps": steps,
        })
    return phases

def extract_steps_legacy(content):
    """## 구현 순서 섹션 파싱 (하위 호환)"""
    steps = []
    match = re.search(r"## 구현 순서\s*((?:\s*\d+\. .*\n?)+)", content)
    if match:
        for idx, line in enumerate(match.group(1).strip().splitlines()):
            m = re.match(r"\s*\d+\.\s*(.*)", line)
            if m:
                text = m.group(1).strip()
                files = []
                f_match = re.search(r"\(files:\s*(.*?)\)", text)
                if f_match:
                    files = [f.strip() for f in f_match.group(1).split(",")]
                    text = text[:f_match.start()].strip()
                steps.append({"text": text, "files": files})

    if steps:
        return [{
            "idx": 1,
            "title": "Implementation",
            "steps": steps,
            "files": list(set([f for s in steps for f in s["files"]])),
        }]
    return []

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue-doc-root", required=True)
    parser.add_argument("--issue", required=True)
    args = parser.parse_args()

    path = Path(args.issue_doc_root) / "tasks" / args.issue / "plan.md"
    if not path.exists():
        print(json.dumps({"status": "error", "reason": f"플랜 파일을 찾을 수 없습니다: {args.issue}"}, ensure_ascii=False))
        sys.exit(1)

    content = path.read_text()

    fm_match = re.match(r"---(.*?)---", content, re.DOTALL)
    frontmatter = parse_yaml(fm_match.group(1)) if fm_match else {}

    body = content[fm_match.end():] if fm_match else content

    phases = extract_steps_from_phases(body)
    if not phases:
        phases = extract_steps_legacy(body)

    images = []
    img_match = re.search(r"## 이미지 목록\s*((?:\s*- .*\n?)+)", body)
    if img_match:
        images = [line.strip("- ").strip() for line in img_match.group(1).strip().splitlines()]

    all_files = []
    files_summary_match = re.search(r"## 대상 파일 요약\s*\|.*?\|.*?\|.*?\|\s*\|[-| ]*\|\s*((?:\|.*?\|.*?\|.*?\|\s*\n?)+)", body)
    if files_summary_match:
        for line in files_summary_match.group(1).strip().splitlines():
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if parts:
                all_files.append(parts[0])

    plan = {
        "issue": args.issue,
        "path": str(path),
        "frontmatter": frontmatter,
        "phases": phases,
        "target_files": list(set(all_files)),
        "image_paths": images,
    }

    print(json.dumps({"status": "ok", "data": {"plans": [plan]}}, ensure_ascii=False))

if __name__ == "__main__":
    main()
