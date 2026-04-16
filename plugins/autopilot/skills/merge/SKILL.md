---
name: autopilot-merge
description: base_branch가 main/develop 계열이면 origin/base를 워크트리에 merge(싱크), umbrella 브랜치면 origin/umbrella를 워크트리에 rebase 후 워크트리를 umbrella에 머지(커밋 통합)한다.
---

# Worktree Merge

**실행 주체: Main Session**
git push 금지.

## 사용법
`/autopilot:merge [{워크트리브랜치}]` — 워크트리명 지정 또는 목록에서 선택
- `base_branch`가 main/develop 등이면 → **케이스 1**: origin/base → 워크트리 merge (PR 전 싱크)
- `base_branch`가 umbrella 브랜치면 → **케이스 2**: origin/umbrella → 워크트리 rebase 후 워크트리 → umbrella 머지

## 실행 절차

STEP 0: 워크트리 및 타겟 브랜치 확인

  **워크트리 경로 확보:**
  브랜치명이 주어지면:
    ```bash
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure_worktree.py '{워크트리브랜치}' --find-only
    ```
    성공: `data.worktree_path` 보관
    실패 (WORKTREE_NOT_FOUND): "워크트리가 없습니다. /autopilot:plan 을 먼저 실행하세요." 출력 후 [STOP]

  브랜치명이 없으면:
    ```bash
    git worktree list --porcelain
    ```
    워크트리 목록(첫 번째 main 워크트리 제외)을 파싱하여 AskUserQuestion 으로 선택
    선택된 경로를 `worktree_path`로 보관

  **이슈키 및 타겟 브랜치 확보:**
  ```bash
  cd '{worktree_path}' && python3 -c "
  import json; d=json.load(open('.autopilot')); print(d.get('base_branch','')); print(','.join(d.get('issues',[])))
  " 2>/dev/null
  ```
  첫 번째 줄 → target_branch, 두 번째 줄 → issues (쉼표 구분, 없으면 빈 문자열)
  target_branch 가 비어있으면: "`.autopilot` 에서 base_branch 를 읽을 수 없습니다. /autopilot:plan 을 먼저 실행하세요." 출력 후 [STOP]

  **가드레일:**
  ```bash
  cd '{worktree_path}' && git rev-parse --abbrev-ref HEAD
  ```
  → worktree_branch 확보
  worktree_branch == target_branch 이면: "워크트리 브랜치와 타겟 브랜치가 동일합니다. 브랜치를 확인하세요." 출력 후 [STOP]

  **root_path 확보:**
  ```bash
  git worktree list --porcelain
  ```
  첫 번째 worktree 경로 → root_path
  `cd '{root_path}' && git rev-parse --abbrev-ref HEAD` → root_branch

  **이슈키 보관**: issues 문자열을 파싱하여 배열로 보관 (빈 문자열이면 빈 배열)

  **이후 모든 Bash 명령은 `cd '{worktree_path}' && command` 형태로 실행**

  **케이스 판별**:
  BASE_BRANCHES = ["develop", "main", "master", "release", "staging", "stg", "stag", "dev"]
  target_branch 가 위 목록에 포함되거나 "release/"로 시작하면 → [케이스 1 흐름]으로 이동
  그 외 → [케이스 2 흐름]으로 이동

---

## [케이스 1] 베이스 → 워크트리 rebase (PR 전 싱크)

베이스(main/develop 등)의 최신 커밋을 워크트리에 반영한다.

STEP 1: 미커밋 변경사항 커밋
  `cd {worktree_path} && git status --porcelain` 실행
  변경사항 없으면: 스킵
  변경사항 있으면:
    1. 전체 변경사항 파악:
       - `cd {worktree_path} && git diff HEAD`
       - `cd {worktree_path} && git ls-files --others --exclude-standard`
       신규 파일은 내용도 Read하여 분석에 포함
    2. 변경사항을 논리적 단위로 그룹핑
    3. scope 결정: issues[0]이 있으면 이슈키, 없으면 worktree_branch
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

STEP 2: fetch + merge
  ```bash
  cd '{worktree_path}' && git fetch origin {target_branch}
  ```
  실패 시: 에러 출력 후 [STOP]

  ```bash
  cd '{worktree_path}' && git merge origin/{target_branch}
  ```
  성공 (exit 0): STEP 3으로
  충돌 (exit 1):
    Read(`${CLAUDE_PLUGIN_ROOT}/skills/_shared/CONFLICT_RESOLUTION.md`) 후 절차를 따른다.
    변수: resolve_root={worktree_path}, 피처브랜치={target_branch}, branch={worktree_branch}
    충돌 해결 완료 후: `cd {worktree_path} && git merge --continue`
    충돌 해결 실패 시: [STOP]

STEP 3: 완료 출력
  issues_str = issues가 있으면 ", ".join(issues), 없으면 "-"
  ```
  ┌─────────────────────────────────────────────┐
  │ 싱크 완료 (rebase)                           │
  │ 반영된 브랜치: {target_branch}               │
  │ 워크트리: {worktree_branch}                  │
  │ 이슈: {issues_str}                           │
  └─────────────────────────────────────────────┘
  ```

  AskUserQuestion으로 다음 선택지 제시:
  ```
  싱크가 완료되었습니다. 다음 중 선택하세요:
  1. `/autopilot:pr` — PR 생성
  2. 추가 작업 계속
  ```

[TERMINATE]

---

## [케이스 2] 워크트리 → umbrella 머지 (커밋 통합)

워크트리의 커밋들을 umbrella(피처) 브랜치에 통합한다.

STEP C2-1: 미커밋 변경사항 커밋
  케이스 1 STEP 1과 동일 프로세스

STEP C2-1.5: umbrella 브랜치 최신화 (rebase)
  `cd {worktree_path} && git fetch origin {target_branch}` 실행
  origin/{target_branch} 존재 시:
    `cd {worktree_path} && git rebase origin/{target_branch}` 실행
    충돌 시:
      Read(`${CLAUDE_PLUGIN_ROOT}/skills/_shared/CONFLICT_RESOLUTION.md`) 후 절차를 따른다.
      변수: resolve_root={worktree_path}, 피처브랜치={target_branch}, branch={worktree_branch}
      충돌 해결 완료 후 `cd {worktree_path} && git rebase --continue`
      충돌 해결 실패 시: [STOP]
    성공: 계속 진행
  origin/{target_branch} 없으면 (로컬 only): rebase 생략, 계속 진행

STEP C2-2: 머지 대상 커밋 확인
  단일 Bash 호출로 커밋 목록 확보:
  ```bash
  cd '{worktree_path}' && \
    MERGE_BASE=$(git merge-base "origin/{target_branch}" HEAD 2>/dev/null || git merge-base "{target_branch}" HEAD 2>/dev/null) && \
    [ -n "$MERGE_BASE" ] && git log "$MERGE_BASE"..HEAD --oneline || echo "MERGE_BASE_NOT_FOUND"
  ```
  출력이 "MERGE_BASE_NOT_FOUND" 이면 "머지 베이스를 찾을 수 없습니다." 출력 후 [STOP]
  그 외: 커밋 목록 표시

[GATE] STEP C2-3: 머지 승인
  AskUserQuestion("{target_branch}에 위 커밋들을 머지할까요? (yes / no)")
  [LOCK: 응답 전 머지 실행 금지]

  응답 "yes": STEP C2-4 진행
  응답 "no": "머지 취소." [TERMINATE]

STEP C2-4: 머지 실행
  실행:
  ```
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {target_branch} --branch {worktree_branch}
  ```
  성공 (exit 0): 워크트리 동기화 후 STEP C2-5
  충돌 (exit 2): 충돌 해결 프로세스 진입

  [워크트리 동기화] — 머지 성공 시 (충돌 해결 후 포함)
    ```
    cd {root_path} && git checkout {root_branch}
    cd {worktree_path} && git merge --ff-only {target_branch}
    ```

  [충돌 해결 프로세스] — 머지 충돌은 root_path(umbrella 브랜치 체크아웃 상태)에서 발생
    Read(`${CLAUDE_PLUGIN_ROOT}/skills/_shared/CONFLICT_RESOLUTION.md`) 후 절차를 따른다.
    변수: resolve_root={root_path}, 피처브랜치={target_branch}, branch={worktree_branch}
    충돌 해결 실패 시 (마커 잔존 또는 exit 1): [STOP]

STEP C2-5: 완료 출력
  issues_str = issues가 있으면 ", ".join(issues), 없으면 "-"
  ```
  ┌───────────────────────────────────────────────┐
  │ 머지 완료                                      │
  │ umbrella: {target_branch}                      │
  │ 워크트리: {worktree_branch}                    │
  │ 이슈: {issues_str}                             │
  └───────────────────────────────────────────────┘
  ```

  AskUserQuestion으로 다음 선택지 제시:
  ```
  머지가 완료되었습니다. 다음 중 선택하세요:
  1. `/autopilot:pr` — PR 생성
  2. `/autopilot:cleanup` — 머지 완료된 워크트리 정리
  3. 추가 작업 계속
  ```

[TERMINATE]
