---
name: autopilot-merge
description: 워크트리를 피처 브랜치에 머지하거나, 대상 브랜치를 워크트리에 반영(pull+merge)한다.
---

# Worktree Merge

**실행 주체: Merger 에이전트 전용**
git push 금지.

## 사용법
- `/autopilot:merge {피처브랜치}` — 케이스 1: 워크트리 → 피처브랜치 (rebase 선행)
- `/autopilot:merge develop` — 케이스 2: 대상 브랜치 → 워크트리 (PR 전 싱크)

## 실행 절차

STEP 0: 워크트리 확인
  다음 명령을 각각 실행하여 컨텍스트 확보:
  - `git rev-parse --show-toplevel` → worktree_path
  - `git rev-parse --abbrev-ref HEAD` → current_branch
  - `git worktree list --porcelain` 출력에서 첫 번째 worktree 경로 → root_path
  - `cd {root_path} && git rev-parse --abbrev-ref HEAD` → root_branch

  current_branch == {피처브랜치} 이면: "피처 브랜치에서는 실행할 수 없습니다. 워크트리 안에서 실행하세요." 출력 후 [STOP]

  **이슈키 확보**: `{worktree_path}/.autopilot` 파일 읽기
  성공: `issues` 배열 보관. 없거나 비어있으면 이슈키 없이 진행 (커밋 메시지 scope는 current_branch 사용)
  실패: 이슈키 없이 진행

  **이후 파일 작업과 git 명령은 `cd {worktree_path} && command` 형태로 실행.**

  **케이스 판별**:
  CASE_2_BRANCHES = ["develop", "main", "master", "release", "staging", "stg", "stag", "dev"]
  {피처브랜치}가 위 목록에 포함되거나 "release/"로 시작하면 → [케이스 2 흐름]으로 이동
  그 외 → [케이스 1 흐름] 계속 진행

---

## [케이스 1] 워크트리 → 피처브랜치

STEP 1: 미커밋 변경사항 커밋
  `cd {worktree_path} && git status --porcelain` 실행
  변경사항 없으면: 스킵
  변경사항 있으면:
    1. 전체 변경사항 파악:
       - `cd {worktree_path} && git diff HEAD`
       - `cd {worktree_path} && git ls-files --others --exclude-standard`
       신규 파일은 내용도 Read하여 분석에 포함
    2. 변경사항을 논리적 단위로 그룹핑
    3. scope 결정: issues[0]이 있으면 이슈키, 없으면 current_branch
    4. 각 그룹별로 순서대로 커밋 (subject + body):
       - subject: `{type}({scope}): {단위 요약}`
       - body:
         ```
         요구사항: {이 변경이 필요한 이유 / 요청된 내용}
         작업내용: {실제 변경 내용 (파일별로 간략히)}
         특이사항: {주요 결정, 트레이드오프, 제약사항 (없으면 생략)}
         ```
       Write("/tmp/commit_msg.txt", "{subject}\n\n{body 전체}")
       그룹에 속한 파일만 개별 quote하여 stage 후 커밋:
       ```
       cd {worktree_path} && git add -- {shlex.quote(파일1)} ... && git commit -F /tmp/commit_msg.txt
       ```

STEP 1.5: 피처브랜치 최신화 (rebase)
  `cd {worktree_path} && git fetch origin {피처브랜치}` 실행
  origin/{피처브랜치} 존재 시:
    `cd {worktree_path} && git rebase origin/{피처브랜치}` 실행
    충돌 시:
      Read(`${CLAUDE_PLUGIN_ROOT}/skills/_shared/CONFLICT_RESOLUTION.md`) 후 절차를 따른다.
      변수: resolve_root={worktree_path}, 피처브랜치={피처브랜치}, branch={current_branch}
      충돌 해결 완료 후 `cd {worktree_path} && git rebase --continue`
      충돌 해결 실패 시: [STOP]
    성공: 계속 진행
  origin/{피처브랜치} 없으면 (로컬 only): rebase 생략, 계속 진행

STEP 2: 머지 대상 커밋 확인
  단일 Bash 호출로 커밋 목록 확보:
  ```bash
  cd '{worktree_path}' && \
    MERGE_BASE=$(git merge-base "origin/{피처브랜치}" HEAD 2>/dev/null || git merge-base "{피처브랜치}" HEAD 2>/dev/null) && \
    [ -n "$MERGE_BASE" ] && git log "$MERGE_BASE"..HEAD --oneline || echo "MERGE_BASE_NOT_FOUND"
  ```
  출력이 "MERGE_BASE_NOT_FOUND" 이면 "머지 베이스를 찾을 수 없습니다." 출력 후 [STOP]
  그 외: 커밋 목록 표시

[GATE] STEP 3: 머지 승인
  AskUserQuestion("{피처브랜치}에 위 커밋들을 머지할까요? (yes / no)")
  [LOCK: 응답 전 머지 실행 금지]

  응답 "yes": STEP 4 진행
  응답 "no": "머지 취소." [TERMINATE]

STEP 4: 머지 실행
  실행:
  ```
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --branch {current_branch}
  ```
  성공 (exit 0): 워크트리 동기화 후 STEP 5
  충돌 (exit 2): 충돌 해결 프로세스 진입

  [워크트리 동기화] — 머지 성공 시 (충돌 해결 후 포함)
    ```
    cd {root_path} && git checkout {root_branch}
    cd {worktree_path} && git merge --ff-only {피처브랜치}
    ```

  [충돌 해결 프로세스] — 머지 충돌은 root_path(피처 브랜치 체크아웃 상태)에서 발생
    Read(`${CLAUDE_PLUGIN_ROOT}/skills/_shared/CONFLICT_RESOLUTION.md`) 후 절차를 따른다.
    변수: resolve_root={root_path}, 피처브랜치={피처브랜치}, branch={current_branch}

    충돌 해결 실패 시 (마커 잔존 또는 exit 1): [STOP]

STEP 5: 완료 출력
  issues_str = issues가 있으면 ", ".join(issues), 없으면 "-"
  ```
  ┌───────────────────────────────────────────────┐
  │ 머지 완료                                      │
  │ 브랜치: {피처브랜치}                           │
  │ 워크트리: {current_branch}                     │
  │ 이슈: {issues_str}                             │
  └───────────────────────────────────────────────┘
  ```

  AskUserQuestion으로 다음 선택지 제시:
  ```
  머지가 완료되었습니다. 다음 중 선택하세요:
  1. `/autopilot:pr` — develop 대상 PR 생성
  2. `/autopilot:cleanup` — 머지 완료된 워크트리 정리
  3. 추가 작업 계속
  ```

[TERMINATE]

---

## [케이스 2] 대상 브랜치 → 워크트리 (PR 전 싱크)

STEP C2-1: 미커밋 변경사항 커밋
  케이스 1 STEP 1과 동일 프로세스

STEP C2-2: 대상 브랜치 fetch + merge
  `cd {worktree_path} && git fetch origin {피처브랜치}` 실행
  실패 시: 에러 출력 후 [STOP]
  `cd {worktree_path} && git merge origin/{피처브랜치}` 실행
  성공 (exit 0): merge commit 자동 생성 → STEP C2-3
  충돌 (exit 1):
    Read(`${CLAUDE_PLUGIN_ROOT}/skills/_shared/CONFLICT_RESOLUTION.md`) 후 절차를 따른다.
    변수: resolve_root={worktree_path}, 피처브랜치={피처브랜치}, branch={current_branch}
    충돌 해결 완료 후: `cd {worktree_path} && git merge --continue` 실행
    충돌 해결 실패 시: [STOP]

STEP C2-3: 완료 출력
  ```
  ┌─────────────────────────────────────────────┐
  │ 동기화 완료                                  │
  │ 반영된 브랜치: {피처브랜치}                   │
  │ 현재 브랜치: {current_branch}                │
  └─────────────────────────────────────────────┘
  ```

  AskUserQuestion으로 다음 선택지 제시:
  ```
  동기화가 완료되었습니다. 다음 중 선택하세요:
  1. `/autopilot:pr` — PR 생성
  2. 추가 작업 계속
  ```

[TERMINATE]
