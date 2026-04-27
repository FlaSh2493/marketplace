# PR 제목 및 본문 규약

## 제목 생성 규칙
- **형식**: `{type}({scope}): {요약} {issue_key}`
- **Type**: `feat`, `fix`, `refactor`, `chore`, `docs`, `style`, `test`, `perf`
- **Scope**: 도메인 라벨이 있으면 해당 라벨명, 없으면 변경의 핵심 모듈명
- **요약**: 70자 이내, 단일 행, 현재 시제(예: "Add filter" 대신 "Add filter")
- **Issue Key**: 브랜치명이나 커밋 메시지에 있는 경우 제목 끝에 포함 (예: `(DC-123)`)

## 본문 생성 규칙
- **Summary**: 주요 변경사항을 3~5개의 bullet point로 요약
- **Changes**: 전체 커밋 목록 (해시 + 메시지) 포함
- **통계 활용**: `prepare_pr_content.py`에서 제공하는 `stats`와 `major_areas`를 적극 반영
