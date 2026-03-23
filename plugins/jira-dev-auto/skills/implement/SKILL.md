---
name: jira-implement
description: worktree를 생성하고 코드·테스트를 작성한 뒤 빌드 검증 후 커밋합니다.
---

이 스킬은 plan.yaml에 따라 실행 그룹별로 구현을 진행합니다. 병렬 그룹은 `jira-implementer` 서브에이전트를 사용합니다.

## 사전 조건
- `jira-plan` 완료 및 사용자 승인
- `jira-refresh` 체크포인트 통과 (변경 없음 확인)
- `references/worktree-management.md`, `references/commit-convention.md` 로드

## 작업 (Tasks) — 실행 그룹마다

### A. 준비

1. **worktree 생성** (CLI 배치):
   ```bash
   git worktree add {worktree_path} -b {branch} {base_branch}
   ```

2. **패키지 매니저 & 스크립트 확인** (CLI 배치):
   ```bash
   # 1. worktree에서 가장 가까운 package.json 탐색 (현재 디렉토리부터 루트까지)
   PKG=$(cd {worktree_path} && \
     dir=$PWD; while [ "$dir" != "/" ]; do \
       [ -f "$dir/package.json" ] && echo "$dir/package.json" && break; \
       dir=$(dirname "$dir"); \
     done)
   echo "package.json: $PKG"

   # 2. 사용 가능한 스크립트 목록 확인
   jq '.scripts | keys[]' "$PKG" 2>/dev/null
   ```
   - `lint`, `test`, `build` 스크립트 존재 여부 확인
   - 스크립트명이 다를 경우 (예: `type-check`, `check`) → ask_user로 직접 입력 받기
   - package.json 미발견 시 → ask_user: "빌드/테스트 명령어를 직접 입력해주세요"

   이후 사전 설치 및 빌드:
   ```bash
   cd {worktree_path} && pnpm install && pnpm run build 2>&1 | tail -20
   ```
   실패 시 원인 보고 후 중단.

### B. 병렬 그룹

3. **서브에이전트 병렬 호출** (`jira-implementer`):
   - 각 에이전트에 전달: `requirement.yaml` 1개 + `plan.yaml` 해당 task 섹션 + `commit-convention.md`
   - **절대 전달하지 않는 것**: 다른 티켓 requirement, 전체 소스, 대화 히스토리

### C. 순차 그룹

4. **단일 세션에서 순차 실행**:
   - 동일한 구현 흐름 (코드 → 테스트 → 빌드 → 커밋)

### D. 구현 흐름 (각 티켓)

5. **코드 작성** (LLM):
   - `requirement.yaml`의 `technical_spec.files`에 명시된 파일만 수정
   - `technical_spec.apis`, `models` 기준으로 구현

6. **테스트 작성** (LLM):
   - `verification.unit`, `verification.integration` 항목에 맞는 테스트

7. **빌드/린트 검증** (CLI):
   ```bash
   # package.json에서 확인된 스크립트명 사용 (pnpm)
   pnpm run {lint_script} 2>&1 | tail -20
   pnpm run {test_script} 2>&1 | tail -30
   pnpm run {build_script} 2>&1 | tail -20
   ```
   - `{lint_script}`, `{test_script}`, `{build_script}`는 2번 단계에서 탐지한 스크립트명
   - 스크립트 없는 경우 해당 단계 스킵 또는 ask_user로 직접 입력
   - 실패 시 에러 메시지 분석 → 자동 수정 시도 → 재검증 (최대 3회)
   - 3회 실패 시 사용자에게 에러 보고

8. **커밋** (CLI):
   ```bash
   git add -A && git commit -m "{type}({scope}): {description} [{KEY}]"
   ```
   형식은 `references/commit-convention.md` 참조

9. **status.yaml 갱신** (CLI):
   ```yaml
   ticket: PROJ-123
   status: completed
   merged: false
   commits: 2
   last_commit: "<sha>"
   updated_at: "<ISO8601>"
   ```

### E. 완료 처리

10. **Jira 상태 업데이트** (MCP):
    - `mcp__atlassian__jira_update_issue`: status → "In Review"

## 출력
- 커밋된 코드 (각 worktree)
- `.docs/work/{workspace}/{domain}/{KEY}.status.yaml`

## 다음 단계
구현 완료 후 오케스트레이터가 `jira-merge` 스킬로 병합을 진행한다.
