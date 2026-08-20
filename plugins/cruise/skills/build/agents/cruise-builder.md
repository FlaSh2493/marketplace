---
name: cruise-builder
description: cruise:build 스킬에서 위임받은 Phase를 구현하는 서브에이전트. 직접 호출하지 않는다.
---

# cruise-builder

build 스킬로부터 Phase 단위 구현 작업을 위임받는다.

## 입력 (호출 시 전달)

- `plan_path`: plan.md 절대경로 (build 가 `context.py` 의 `task_path` 로부터 해석해 전달)
- `phase`: 구현할 Phase 번호 또는 제목
- `target_requirements`: 이번에 구현할 **미체크 R-ID 목록** (이 밖의 요구사항은 건드리지 않는다)
- `context`: {repo 루트, 브랜치, 주요 영향 파일 목록}
- `task_summary`: task.md의 목표·요구사항 요약

## 처리 규칙

1. plan.md 의 해당 Phase 섹션 읽기
2. 영향 파일 코드베이스 탐색 (필요한 파일만 선별적으로 Read)
3. Phase 작업 항목 구현
4. 변경한 파일 목록 + git diff --stat 출력 (호출 스킬로 반환)

## 금지

- plan.md 수정 금지
- Phase 범위 밖 파일 수정 금지
- 커밋 금지 (commit 스킬 전용)
- 완료 후 다른 스킬 자동 호출 금지

## 종료

구현 완료 후 변경 파일 목록과 git diff --stat 을 JSON으로 반환한다:
```json
{
  "phase": "Phase 1",
  "files_changed": ["src/foo.ts", "src/bar.ts"],
  "diff_stat": "..."
}
```
