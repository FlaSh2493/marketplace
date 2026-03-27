---
name: autopilot-merge-all
description: 피처 브랜치의 모든 활성 워크트리를 충돌 수 기준으로 정렬하여 순차적으로 squash merge하고 워크트리를 정리한다.
---

# Worktree Merge All

**실행 주체: Main Session 전용**
워크트리 브랜치 히스토리 직접 수정 절대 금지. git push 금지.

## 사용법
`/autopilot:merge-all {피처브랜치}`

## 실행 절차

STEP 0: 컨텍스트 확보
  다음 명령을 각각 실행:
  - `git rev-parse --show-toplevel` → root_path
  - `git rev-parse --abbrev-ref HEAD` → current_branch

  current_branch가 `worktree-` prefix로 시작하면: "워크트리 브랜치 안에서는 실행할 수 없습니다." 출력 후 [STOP]
  current_branch == {피처브랜치}이면: "피처 브랜치에서는 실행할 수 없습니다. 메인/다른 브랜치 세션에서 실행하세요." 출력 후 [STOP]

  **이후 모든 git/스크립트 명령은 cd prefix 없이 실행 — merge_worktrees.py가 내부적으로 git root를 탐색함**
  **단, 워크트리 내 파일 작업과 git 명령은 `cd {worktree_path} && command` 형태로 실행**

STEP 1: 머지 계획 조회
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --dry-run`
  실패 (exit 1): reason 출력 후 [STOP]
  merge_order가 비어있으면: "머지할 워크트리가 없습니다." 출력 후 [STOP]

  결과 표시:
  ```
  머지 순서 (충돌 적은 순):
  ┌──────┬──────────────────────────┬────────┬────────┐
  │ 순서 │ 이슈                      │ WIP수  │ 충돌   │
  ├──────┼──────────────────────────┼────────┼────────┤
  │  1   │ PLAT-101                  │  3개   │  0개   │
  │  2   │ PLAT-102                  │  1개   │  2개   │
  └──────┴──────────────────────────┴────────┴────────┘
  ```

[GATE] STEP 2: 머지 계획 승인
  AskUserQuestion("위 순서로 전체 머지를 진행할까요? (yes / no)")
  응답 "no": "머지 취소." [TERMINATE]
  응답 "yes": STEP 3 진행

STEP 3: 전체 워크트리 커밋 + 요구사항 동기화
  skipped_issues = []

  merge_order의 각 이슈에 대해 순서대로:
    이슈키 = merge_order[i].issue
    worktree_path = {root_path}/.claude/worktrees/{이슈키}

    [미커밋 변경사항 커밋]
    `cd {worktree_path} && git status --porcelain` 실행
    변경사항 있으면:
      1. 전체 변경사항 파악:
         - `cd {worktree_path} && git diff HEAD` — staged + unstaged 전체 수정사항
         - `cd {worktree_path} && git ls-files --others --exclude-standard` — 신규 파일 목록
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
         Write("/tmp/commit_msg_{이슈키}.txt", "{subject}\n\n{body 전체}")
         그룹에 속한 파일만 개별 quote하여 stage 후 커밋:
         ```
         cd {worktree_path} && git add -- {shlex.quote(파일1)} {shlex.quote(파일2)} ... && git commit -F /tmp/commit_msg_{이슈키}.txt
         ```

    [요구사항 동기화]
    단일 Bash 호출로 MERGE_BASE + log 전체 확보:
    ```bash
    cd '{worktree_path}' && \
      MERGE_BASE=$(git merge-base "origin/{피처브랜치}" HEAD 2>/dev/null || git merge-base "{피처브랜치}" HEAD 2>/dev/null) && \
      [ -n "$MERGE_BASE" ] && git log "$MERGE_BASE"..HEAD --format="%s%n%b" || echo "MERGE_BASE_NOT_FOUND"
    ```
    출력이 "MERGE_BASE_NOT_FOUND": skipped_issues에 추가 (경고 출력), 다음 이슈로

    그 외:
      log 출력에서 `요구사항:` 로 시작하는 줄만 추출, 중복 제거
      추출된 항목이 있으면:
        `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키}` 실행 → data.md_path 확보
        실패 시 경고 출력 후 스킵 (머지는 계속 진행)
        data.md_path 의 `## 추가 요구사항` 섹션 끝에 append (섹션 없으면 파일 끝에 생성):
        ```
        <!-- merge-all {날짜} -->
        - {요구사항 항목1}
        - {요구사항 항목2}
        ```

[GATE] STEP 4: 머지 승인
  각 이슈의 커밋 목록 표시 (STEP 3에서 수집한 log)
  AskUserQuestion("위 커밋들을 {피처브랜치}에 머지할까요? (yes / no)")
  응답 "no": "머지 취소." [TERMINATE]
  응답 "yes": STEP 5 진행

STEP 5: 순서대로 rebase + fast-forward 머지 실행
  merged_issues = []

  merge_order의 각 이슈에 대해 순서대로 (skipped_issues 제외):
    이슈키 = 현재 이슈

    실행:
    ```
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --issue {이슈키}
    ```
    exit 0: merged_issues에 추가, 다음 이슈로
    exit 1: 오류 출력, 해당 이슈 건너뜀, 다음 이슈로
    exit 2 (충돌): 충돌 해결 프로세스 진입

    [충돌 해결 프로세스] — rebase 중 충돌
      실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/show_conflicts.py`
      충돌 파일마다:
        [GATE] AskUserQuestion("충돌: {파일명}\n{diff}\n\n선택: [feature / base / 직접편집]")
        응답 "feature": `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py '{파일}' feature`
        응답 "base": `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py '{파일}' base`
        응답 "직접편집":
          [GATE] AskUserQuestion("편집 완료 후 'done' 입력")
          'done' 입력 시:
            `grep -Ec "^(<{7} |>{7} )" '{파일명}'` 실행
            exit 0 이면 (마커 존재): "충돌 마커(<<<<<<< 또는 >>>>>>>)가 아직 남아있습니다. 파일을 다시 확인하세요." 출력 후 → [GATE] 반복
            exit 1 이면 (마커 없음): `git add -- '{파일명}'` 실행

      [--continue 전 최종 마커 검사]
        `git diff --name-only --cached` 로 staged 파일 목록 확보
        각 파일에 대해: `grep -lE "^(<{7} |>{7} )" '{파일명}'`
        마커가 남은 파일이 있으면:
          해당 파일 목록 출력: "아직 충돌 마커가 남아있는 파일: {목록}"
          해당 이슈 건너뜀 (skipped_issues에 추가), 다음 이슈로

      실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --issue {이슈키} --continue`
      exit 0: merged_issues에 추가, 다음 이슈로
      exit 2: 다음 커밋 충돌 — 충돌 해결 프로세스 반복
      exit 1: 오류 출력, 해당 이슈 건너뜀, 다음 이슈로

STEP 6: 완료 출력
  merged_issues가 비어있으면: "머지된 이슈가 없습니다." [TERMINATE]

  ```
  ┌──────────────────────────────────────────────────────────┐
  │ 전체 머지 완료                                            │
  │ 브랜치: {피처브랜치}                                      │
  │ 처리된 이슈: {merged_issues 목록}                         │
  └──────────────────────────────────────────────────────────┘
  ```

  skipped_issues가 있으면 아래 형식으로 출력:
  ```
  ⚠ 머지 실패 이슈:
  {이슈키마다 한 줄씩}
    워크트리: {root_path}/.claude/worktrees/{이슈키}
    재시도:   /autopilot:merge {피처브랜치}  (해당 워크트리 세션에서 실행)
  ```

  AskUserQuestion("머지가 완료되었습니다. 이어서 `/autopilot:cleanup`으로 머지된 워크트리를 정리할까요?")

[TERMINATE]
