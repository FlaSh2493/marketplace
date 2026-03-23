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

4. **하이브리드 plan.md 생성** (CLI):
   - 경로: `.docs/work/{workspace}/{domain}/{KEY}/plan.md`
   - **구성**:
     - **[사람용 상세 섹션]**:
       - `# [KEY] 티켓 제목`
       - `## 1. 구현 목표 (Goal)`: 비즈니스 가치 및 최종 상태
       - `## 2. 세부 구현 접근 방식 (Detailed Approach)`: 단계별 로직, 알고리즘, 패턴
       - `## 3. 수정 및 생성 대상 파일 (Files)`: 구체적인 파일 경로 및 변경 내역
       - `## 4. 검증 전략 (Verification)`: 단위 테스트 항목, 통합 테스트 항목, Edge Case
     - **[에이전트 전용 섹션]**:
       - `## Agent Specs (Do Not Edit)`
       - YAML 코드 블록: `ticket`, `domain`, `execution_mode`, `branch`, `base_branch`, `worktree_path`, `files_to_modify`, `scripts` (test/build) 등

## 출력
- `.docs/work/{workspace}/{domain}/{KEY}/plan.md`

## 다음 단계
계획 수립 완료 후 `jira-approve` 스킬을 통해 각 티켓의 계획을 개별적으로 검토하고 승인한다.
