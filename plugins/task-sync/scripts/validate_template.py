#!/usr/bin/env python3
"""
이슈 파일 포맷 검증. 저장 전 필수 실행.
Usage: python3 validate_template.py {file_path}
Exit 0: ok / Exit 1: error (포맷 불일치)
"""
import json, os, re, sys
from common import ok, error


REQUIRED_HEADER_FIELDS = ["jira", "상태", "담당자", "생성일", "최근 업데이트", "출처"]
# extract 전용 필수 섹션/필드
EXTRACT_REQUIRED_SECTIONS = ["## 설명", "## 메타데이터"]
EXTRACT_REQUIRED_META_FIELDS = ["deps", "api", "states"]


def get_source(content: str) -> str:
    """헤더의 출처 필드 값을 반환. 파싱 실패 시 빈 문자열."""
    m = re.search(r"^- 출처:\s*(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def main():
    if len(sys.argv) < 2:
        error("MISSING_ARGS", "사용법: validate_template.py {file_path}")

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        error("FILE_NOT_FOUND", f"파일이 없습니다: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    failures = []

    # 1. 첫 줄: # {KEY}: {제목}
    if not lines or not re.match(r"^# \S+: .+", lines[0]):
        failures.append("첫 줄이 '# {JIRA-KEY}: {작업 제목}' 형식이 아닙니다")

    # 2. 헤더 필드 6개 존재 여부
    for field in REQUIRED_HEADER_FIELDS:
        if not re.search(rf"^- {re.escape(field)}:", content, re.MULTILINE):
            failures.append(f"헤더 필드 누락: '{field}'")

    # 3. 헤더 필드 순서
    positions = {}
    for field in REQUIRED_HEADER_FIELDS:
        m = re.search(rf"^- {re.escape(field)}:", content, re.MULTILINE)
        if m:
            positions[field] = m.start()
    ordered = sorted(positions.items(), key=lambda x: x[1])
    actual_order = [k for k, _ in ordered]
    if actual_order != REQUIRED_HEADER_FIELDS:
        failures.append(f"헤더 필드 순서 오류. 현재: {actual_order}, 필요: {REQUIRED_HEADER_FIELDS}")

    source = get_source(content)

    if source == "jira-fetch":
        # jira-fetch: ## 설명 필수, 메타데이터 불필요
        if "## 설명" not in content:
            failures.append("필수 섹션 누락: '## 설명'")
    else:
        # extract (기본): 기존 규칙 유지
        for section in EXTRACT_REQUIRED_SECTIONS:
            if section not in content:
                failures.append(f"필수 섹션 누락: '{section}'")
        for field in EXTRACT_REQUIRED_META_FIELDS:
            if not re.search(rf"^- {re.escape(field)}:", content, re.MULTILINE):
                failures.append(f"메타데이터 필드 누락: '{field}'")

    # 섹션 구분선 (---)
    if content.count("\n---\n") < 2:
        failures.append("섹션 구분선('---')이 2개 이상 있어야 합니다")

    # 설명 섹션 내용 비어있지 않은지
    desc_match = re.search(r"## 설명\n\n(.+?)(?=\n---|\n## |\Z)", content, re.DOTALL)
    if desc_match and not desc_match.group(1).strip():
        failures.append("'## 설명' 섹션이 비어 있습니다")

    if failures:
        error("FORMAT_INVALID", "포맷 검증 실패:\n" + "\n".join(f"  - {f}" for f in failures))

    ok({"file_path": file_path, "message": "포맷 검증 통과"})


if __name__ == "__main__":
    main()
