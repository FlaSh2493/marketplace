---
name: merge
description: 현재 워크트리를 피처 브랜치에 rebase 후 fast-forward로 통합한다.
---

# Worktree Merge

**실행 주체: Merger 에이전트 전용**
워크트리 브랜치 히스토리 직접 수정 절대 금지. git push 금지.

## 사용법
`/worktree-flow:merge {피처브랜치}`

## 실행 절차

STEP 0: 워크트리 확인
  다음 명령을 각각 실행하여 컨텍스트 확보:
  - `git rev-parse --show-toplevel` → worktree_path
  - `git rev-parse --abbrev-ref HEAD` → current_branch
  - `git worktree list --porcelain` 출력에서 첫 번째 worktree 경로 → root_path

  current_branch == {피처브랜치} 이면: "피처 브랜치에서는 실행할 수 없습니다. 워크트리 안에서 실행하세요." 출력 후 [STOP]
  current_branch가 `worktree-` prefix로 시작하지 않으면: "워크트리 브랜치가 아닙니다." 출력 후 [STOP]

  이슈키: current_branch에서 `worktree-` prefix 제거

  **이후 파일 작업과 git 명령은 `cd {worktree_path} && command` 형태로 실행. 스크립트(python3) 실행은 cd prefix 불필요 — 스크립트가 내부적으로 git root를 탐색함**

STEP 1: 미커밋 변경사항 커밋
  `cd {worktree_path} && git status --porcelain` 실행
  변경사항 없으면: 스킵
  변경사항 있으면:
    1. 전체 변경사항 파악:
       - `cd {worktree_path} && git diff HEAD` — staged + unstaged 전체 수정사항
       - `cd {worktree_path} && git ls-files --others --exclude-standard` — 신규 untracked 파일 목록
       신규 파일은 내용도 Read하여 분석에 포함
    2. 변경사항을 논리적 단위로 그룹핑 (기능별, 레이어별 등)
    3. 각 그룹별로 순서대로 커밋 (subject + body):
       - subject: `{type}({이슈키}): {단위 요약}` (type: feat/fix/refactor/chore 등)
       - body:
         ```
         요구사항: {이 변경이 필요한 이유 / 요청된 내용}
         작업내용: {실제 변경 내용 (파일별로 간략히)}
         특이사항: {주요 결정, 트레이드오프, 제약사항 (없으면 생략)}
         ```
       Write 도구로 /tmp/commit_msg_{이슈키}.txt에 저장:
       - Write("/tmp/commit_msg_{이슈키}.txt", "{subject}\n\n{body 전체}")
       그룹에 속한 파일만 개별 quote하여 stage 후 커밋:
       ```
       cd {worktree_path} && git add -- {shlex.quote(파일1)} {shlex.quote(파일2)} ... && git commit -F /tmp/commit_msg_{이슈키}.txt
       ```
       파일명에 공백이 있을 수 있으므로 각 경로를 반드시 따옴표로 감쌀 것. 전체 add(`git add -A`)는 금지.

STEP 2: 요구사항 동기화
  단일 Bash 호출로 MERGE_BASE + log 확보:
  ```bash
  cd '{worktree_path}' && \
    MERGE_BASE=$(git merge-base "origin/{피처브랜치}" HEAD 2>/dev/null || git merge-base "{피처브랜치}" HEAD 2>/dev/null) && \
    [ -n "$MERGE_BASE" ] && git log "$MERGE_BASE"..HEAD --format="%s%n%b" || echo "MERGE_BASE_NOT_FOUND"
  ```
  출력이 "MERGE_BASE_NOT_FOUND" 이면 경고 출력 후 스킵
  그 외:
    log 출력에서 `요구사항:` 로 시작하는 줄만 추출, 중복 제거
    추출된 항목이 있으면:
      `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키}` 실행 → data.md_path 확보
      실패 시 경고 출력 후 스킵
      data.md_path 의 `## 추가 요구사항` 섹션 끝에 append (섹션 없으면 파일 끝에 생성):
      ```
      <!-- merge {날짜} -->
      - {요구사항 항목1}
      - {요구사항 항목2}
      ```

STEP 3: 머지 대상 커밋 확인
  단일 Bash 호출로 커밋 목록 확보:
  ```bash
  cd '{worktree_path}' && \
    MERGE_BASE=$(git merge-base "origin/{피처브랜치}" HEAD 2>/dev/null || git merge-base "{피처브랜치}" HEAD 2>/dev/null) && \
    [ -n "$MERGE_BASE" ] && git log "$MERGE_BASE"..HEAD --oneline || echo "MERGE_BASE_NOT_FOUND"
  ```
  출력이 "MERGE_BASE_NOT_FOUND" 이면 "머지 베이스를 찾을 수 없습니다." 출력 후 [STOP]
  그 외: 커밋 목록 표시

[GATE] STEP 4: 머지 승인
  AskUserQuestion("위 커밋들을 {피처브랜치}에 머지할까요? (yes / no)")
  [LOCK: 응답 전 머지 실행 금지]

  응답 "yes": STEP 5 진행
  응답 "no": "머지 취소." [TERMINATE]

STEP 5: Rebase + fast-forward 머지 실행
  실행:
  ```
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --issue {이슈키}
  ```
  성공 (exit 0): STEP 6 진행
  충돌 (exit 2): 충돌 해결 프로세스 진입

  [충돌 해결 프로세스] — rebase 중 충돌은 워크트리 브랜치에서 발생
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/show_conflicts.py`
    충돌 파일마다:
      [GATE] AskUserQuestion("충돌: {파일명}\n{diff}\n\n선택: [feature / base / 직접편집]")
      응답 "feature": `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py '{파일}' feature`
      응답 "base": `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py '{파일}' base`
      응답 "직접편집":
        [GATE] AskUserQuestion("편집 완료 후 'done' 입력")
        사용자가 'done' 입력 시:
          `grep -Ec "^(<{7} |>{7} )" '{파일명}'` 실행
          exit 0 이면 (마커 존재): "충돌 마커(<<<<<<< 또는 >>>>>>>)가 아직 남아있습니다. 파일을 다시 확인하세요." 출력 후 → [GATE] 반복
          exit 1 이면 (마커 없음): `git add -- '{파일명}'` 실행

    [--continue 전 최종 마커 검사] — 모든 파일 해결 완료 후 실행
      `git diff --name-only --cached` 로 staged 파일 목록 확보
      각 파일에 대해: `grep -lE "^(<{7} |>{7} )" '{파일명}'`
      마커가 남은 파일이 있으면:
        해당 파일 목록 출력: "아직 충돌 마커가 남아있는 파일: {목록}"
        [STOP] — --continue 실행하지 않음

    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --issue {이슈키} --continue`
    exit 0: STEP 6 진행
    exit 2: 다음 커밋 충돌 — 충돌 해결 프로세스 반복
    exit 1: 오류 출력 후 [STOP]

STEP 6: 완료 출력
  ```
  ┌───────────────────────────────────────────────┐
  │ 머지 완료                                      │
  │ 브랜치: {피처브랜치}                           │
  │ 처리된 이슈: {이슈키}                          │
  └───────────────────────────────────────────────┘
  ```

  AskUserQuestion("머지가 완료되었습니다. 이어서 `/worktree-flow:cleanup`으로 워크트리를 정리할까요?")

[TERMINATE]
