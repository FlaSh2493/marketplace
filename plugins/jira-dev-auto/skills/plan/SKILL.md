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

4. **plan.yaml 생성** (CLI):
   경로: `.docs/work/{workspace}/{domain}/{KEY}.plan.yaml`
   ```yaml
   ticket: PROJ-123
   domain: auth
   execution_mode: sub_agent
   branch: feat/PROJ-123-auth-login
   base_branch: develop
   group_id: 1
   group_mode: parallel
   depends_on: []
   worktree_path: .docs/work/worktrees/PROJ-123
   estimated_complexity: medium
   ```

5. **사용자 검토** (ask_user):
   계획 요약 표시:
   ```
   그룹 1 (병렬): PROJ-123(auth), PROJ-456(payment)
   그룹 2 (순차, 그룹1 완료 후): PROJ-789(api)
   실행 방식: sub_agent
   ```
   선택지: 승인 / 수정 요청 / 거부

6. **수정 요청 시**: 피드백 반영 후 4번부터 재실행

## 출력
- `.docs/work/{workspace}/{domain}/{KEY}.plan.yaml` (각 티켓)

## 다음 단계
승인 후 `jira-implement` 스킬로 구현을 시작한다.
