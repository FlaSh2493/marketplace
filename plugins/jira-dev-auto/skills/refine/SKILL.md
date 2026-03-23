---
name: jira-refine
description: Jira 티켓을 7항목 요구사항 규격으로 변환하고 모호한 항목을 사용자 질문으로 해소합니다.
---

이 스킬은 각 티켓을 `references/requirement-spec.md`의 7항목 규격에 따라 `requirement.yaml`로 변환합니다.

## 사전 조건
- `jira-analyze` 완료 (도메인 분류 완료)
- `references/requirement-spec.md` 판단 기준 로드

## 작업 (Tasks) — 티켓마다 반복

1. **Skill 로드**: `references/requirement-spec.md`

2. **LLM 변환**:
   - 입력: 해당 티켓 `snapshot.json`의 `data` 전체 + 7항목 템플릿
   - 출력: `requirement.yaml` 초안

3. **모호 항목 감지**:
   질문 트리거 확인:
   - 수치 미명시 → 정책 결정 질문
   - 구현 방식 2가지 이상 → 기술 선택 질문
   - 범위 경계 모호 → 범위 확인 질문
   - 파일 공유 충돌 → 우선순위 질문
   - 테스트 수준 미명시 → 검증 범위 질문

4. **질문 루프** (pending 항목이 있는 동안 반복):
   - ask_user: 모호한 항목들을 묶어 한 번에 질문
     - 가능한 경우 선택지(`[1]`, `[2]`, `[자유 입력]`)를 포함하여 질문합니다.
   - 답변을 `requirement.yaml`의 해당 필드에 기록
   - 다시 모호 항목 감지 → 없으면 종료

5. **requirement.yaml 저장** (CLI):
   경로: `.docs/work/{workspace}/{domain}/{KEY}.requirement.yaml`
   ```yaml
   ticket: PROJ-123
   domain: auth
   version: 1
   objective:
     goal: "..."
     success_criteria: [...]
   scope:
     included: [...]
     excluded: [...]
   technical_spec:
     files: [...]
     apis: [...]
     models: [...]
   constraints:
     performance: "..."
     security: "..."
     compatibility: "..."
   verification:
     unit: [...]
     integration: [...]
     edge_cases: [...]
   dependencies:
     upstream: [...]
     downstream: [...]
   open_questions: []
   ```

6. **스냅샷 PIN** (CLI):
   `snapshot.json`의 `pinned_at` 필드를 현재 시각으로 기록

## 토큰 절약
- 티켓 1개씩 처리 (배치 금지)
- 질문은 pending 항목 전체를 1회 ask_user로 묶기

## 출력
- `.docs/work/{workspace}/{domain}/{KEY}.requirement.yaml`
- `.docs/work/{workspace}/_cache/{KEY}.snapshot.json` (pinned_at 갱신)

## 다음 단계
모든 티켓 정제 완료 후 `jira-plan` 스킬로 구현 계획을 수립한다.
