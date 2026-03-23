---
name: jira-merge
description: 완료된 worktree를 대상 브랜치에 병합하고 충돌을 해결합니다.
---

이 스킬은 구현이 완료된 브랜치를 병합합니다. 충돌 시 LLM이 해결 전략을 제안하고 사용자가 승인합니다.

## 사전 조건
- `jira-implement` 완료 (status=completed, merged=false)
- `jira-refresh` 체크포인트 통과
- `references/merge-strategy.md` 로드

## 작업 (Tasks)

1. **병합 대상 확인** (CLI):
   ```bash
   # _index.yaml에서 status=completed, merged=false 티켓 조회
   cat .docs/{workspace}/_index.yaml
   ```

2. **병합 제안** (ask_user):
   - 병합 가능한 티켓 목록 + 커밋 수 표시
   - 병합 순서 제안 (의존성 기준)
   - 대상 브랜치 선택: develop(기본) / main / 직접 입력

3. **병합 시도** (CLI):
   ```bash
   git checkout {target_branch}
   git merge --no-commit --no-ff {feature_branch}
   ```

4. **충돌 확인** (CLI):
   ```bash
   git diff --name-only --diff-filter=U
   ```
   - 충돌 없음 → 7번으로
   - 충돌 있음 → 5번으로

5. **충돌 블록 추출** (CLI, 충돌 파일마다):
   ```bash
   awk '/^<<<<<<</,/^>>>>>>>/' {conflicted_file}
   ```

6. **충돌 해결 루프** (충돌 파일마다):
   a. `references/merge-strategy.md` 로드
   b. LLM에 충돌 블록만 입력 (~1500 토큰/파일):
      - 출력: 전략 선택 (`ours` / `theirs` / `manual`) + 이유
   c. ask_user: 제안된 전략 확인 및 승인
   d. 전략 적용 (CLI):
      - `ours`: `git checkout --ours {file} && git add {file}`
      - `theirs`: `git checkout --theirs {file} && git add {file}`
      - `manual`: LLM이 통합 코드 생성 → 사용자 승인 → 적용

7. **빌드 검증** (CLI):
   ```bash
   npm run build && npm run test 2>&1 | tail -20
   ```
   실패 시 수정 후 재검증

8. **병합 커밋** (CLI):
   ```bash
   git commit -m "merge: {KEY} - {summary}"
   ```

9. **status.yaml 갱신** (CLI):
   ```yaml
   merged: true
   merged_at: "<ISO8601>"
   target_branch: develop
   ```

10. **Jira 상태 업데이트** (MCP):
    - `mcp__atlassian__jira_update_issue`: status → "Done"

11. **worktree 정리 제안** (ask_user):
    - 정리: `git worktree remove {path}`
    - 보존: 기록만 유지

## 출력
- 병합 커밋
- `.docs/{workspace}/{domain}/{KEY}.status.yaml` (merged: true)

## 다음 단계
모든 병합 완료 후 `/jira status`로 결과를 확인한다.
