---
name: jira-plan
description: 구현 방식(single/sub_agent/claude_team)을 결정하고 실행 그룹별 plan.yaml을 생성합니다.
---

이 스킬은 요구사항과 의존성 그래프를 바탕으로 최적 실행 전략을 수립합니다.

## 사전 조건
- `jira-refine` 완료 (모든 티켓 `requirement.yaml` 존재)
- `_index.yaml`의 `domains` 섹션 (의존성 포함)

## 작업 (Tasks)

1. **실행 방식 판단** (LLM):
   - 입력: 티켓 수, 도메인 독립성, 복잡도 (`_index.yaml` 요약)
   - 규칙:
     - `single_session`: 티켓 1-2개, 단일 도메인, 낮은 복잡도
     - `sub_agent`: 티켓 3-5개, 독립 도메인, 병렬 가능
     - `claude_team`: 티켓 6개+, 다수 도메인, 높은 상호 의존

2. **실행 그룹 편성** (LLM):
   - 병렬 가능 그룹: `can_parallelize: true`이고 공유 파일 없는 도메인
   - 순차 필수 그룹: 다른 그룹 완료 후 실행해야 하는 것

3. **worktree 전략 결정**:
   - base_branch: `settings.yaml`의 `git.base_branch`
   - 브랜치명 형식: `feat/{KEY}-{summary-slug}`

4. **계획 문서화** (CLI):
   - **`implementation_plan.md`** (Claude Artifact)를 가장 먼저 생성/업데이트합니다.
     - 오케스트레이터가 이를 사용자에게 보여주고 승인을 받을 수 있도록, 모든 구현 상세와 검증 계획을 이 문서에 담습니다.
   - **영구 보관**: 승인된 최종 계획을 `.docs/work/{workspace}/{domain}/{KEY}/plan.md`에 저장합니다.
     - **사람용**: 상세한 마크다운 설명
     - **에이전트용**: YAML 코드 블록 (에이전트 스펙)

## 출력
- `implementation_plan.md` (Claude Artifact - **최우선 생성**)
- `.docs/work/{workspace}/{domain}/{KEY}/plan.md` (영구 보관용)

## 다음 단계
Orchestrator가 `notify_user`를 통해 전체 `implementation_plan.md`에 대한 승인을 요청합니다.
