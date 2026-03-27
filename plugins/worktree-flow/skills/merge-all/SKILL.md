---
name: worktree-flow-merge-all
description: 피처 브랜치의 모든 활성 워크트리를 충돌 수 기준으로 정렬하여 순차적으로 squash merge하고 워크트리를 정리한다.
---

# Worktree Merge All

**실행 주체: Main Session 전용**
워크트리 브랜치 히스토리 직접 수정 절대 금지. git push 금지.

## 사용법
`/worktree-flow:merge-all {피처브랜치}`

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

STEP 3: 전체 워크트리 WIP 커밋 + 커밋 메시지 수집
  proposed_messages = {}  (이슈키 → 제안 커밋 메시지 매핑)
  skipped_issues = []

  merge_order의 각 이슈에 대해 순서대로:
    이슈키 = merge_order[i].issue
    worktree_path = {root_path}/.claude/worktrees/{이슈키}

    [WIP 커밋]
    `cd {worktree_path} && git status --porcelain` 실행
    변경사항 있으면:
      1. 전체 변경사항 파악:
         - `cd {worktree_path} && git diff HEAD` — staged + unstaged 전체 수정사항
         - `cd {worktree_path} && git ls-files --others --exclude-standard` — 신규 파일 목록
         신규 파일은 내용도 Read하여 분석에 포함
      2. 변경사항을 논리적 단위로 그룹핑 (기능별, 레이어별 등)
      3. 각 그룹별로 순서대로 커밋 (subject + body):
         - subject: `wip({이슈키}): {단위 요약}` (prefix 반드시 `wip({이슈키}):` 사용)
         - body:
           ```
           요구사항: {이 변경이 필요한 이유 / 요청된 내용}
           작업내용: {실제 변경 내용 (파일별로 간략히)}
           특이사항: {주요 결정, 트레이드오프, 제약사항 (없으면 생략)}
           ```
         Write("/tmp/wip_msg_{이슈키}.txt", "{subject}\n\n{body 전체}")
         그룹에 속한 파일만 개별 quote하여 stage 후 커밋:
         ```
         cd {worktree_path} && git add -- {shlex.quote(파일1)} {shlex.quote(파일2)} ... && git commit -F /tmp/wip_msg_{이슈키}.txt
         ```

    [커밋 메시지 제안]
    단일 Bash 호출로 MERGE_BASE + log 확보:
    ```bash
    cd '{worktree_path}' && \
      MERGE_BASE=$(git merge-base "origin/{피처브랜치}" HEAD 2>/dev/null || git merge-base "{피처브랜치}" HEAD 2>/dev/null) && \
      [ -n "$MERGE_BASE" ] && git log "$MERGE_BASE"..HEAD --oneline || echo "MERGE_BASE_NOT_FOUND"
    ```
    출력이 "MERGE_BASE_NOT_FOUND": skipped_issues에 추가 (경고 출력), 다음 이슈로
    그 외: WIP 커밋 목록 기반으로 `feat({이슈키}): {설명}` 제안 → proposed_messages[{이슈키}]에 보관

[GATE] STEP 4: 커밋 메시지 일괄 승인
  proposed_messages 표시:
  ```
  커밋 메시지 제안:
  1. feat(PLAT-101): {설명}
  2. feat(PLAT-102): {설명}
  ```
  AskUserQuestion("커밋 메시지를 확인하세요.\n수정: '1: 새메시지' 형식으로 입력\n승인: yes\n취소: no")
  응답 "yes": STEP 5 진행
  응답 "{번호}: {내용}": 해당 메시지 수정 후 재표시 → STEP 4 반복
  응답 "no": "머지 취소." [TERMINATE]

STEP 5: 순서대로 squash merge 실행
  merged_issues = []

  proposed_messages의 각 이슈에 대해 머지 순서대로:
    이슈키 = 현재 이슈
    커밋메시지 = proposed_messages[이슈키]

    Write("/tmp/merge_msg_{이슈키}.txt", "{커밋메시지 전체 내용}")
    실행:
    ```
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --issue {이슈키} --message "$(cat /tmp/merge_msg_{이슈키}.txt)"
    ```
    exit 0: merged_issues에 추가, 다음 이슈로
    exit 1: 오류 출력, 해당 이슈 건너뜀, 다음 이슈로
    exit 2 (충돌): 충돌 해결 프로세스 진입

    [충돌 해결 프로세스] — 충돌은 메인 리포(피처 브랜치)에 발생하므로 아래 명령은 cd prefix 없이 실행
      실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/show_conflicts.py`
      충돌 파일마다:
        [GATE] AskUserQuestion("충돌: {파일명}\n{diff}\n\n선택: [feature / base / 직접편집]")
        응답 "feature": `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py '{파일}' feature`
        응답 "base": `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py '{파일}' base`
        응답 "직접편집":
          [GATE] AskUserQuestion("편집 완료 후 'done' 입력")
          'done' 입력 시:
            `grep -c "^<<<<<<< " '{파일명}'` 실행
            exit 0 이면 (마커 존재): "충돌 마커(<<<<<<<)가 아직 남아있습니다. 파일을 다시 확인하세요." 출력 후 → [GATE] 반복
            exit 1 이면 (마커 없음): `git add -- '{파일명}'` 실행
      실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --issue {이슈키} --message "$(cat /tmp/merge_msg_{이슈키}.txt)" --continue`
      exit 0: merged_issues에 추가, 다음 이슈로
      exit 1: 오류 출력, 해당 이슈 건너뜀, 다음 이슈로

STEP 6: 정리
  merged_issues가 비어있으면: "머지된 이슈가 없습니다." [TERMINATE]

  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cleanup_worktrees.py {피처브랜치} --issues {merged_issues 공백 구분}`
  exit 0 (전체 성공):
    ```
    ┌──────────────────────────────────────────────────────────┐
    │ 전체 머지 완료                                            │
    │ 브랜치: {피처브랜치}                                      │
    │ 처리된 이슈: {merged_issues 목록}                         │
    │ WIP 보존 태그: archive/{피처}/{이슈키}-wip-{날짜} (각각)  │
    └──────────────────────────────────────────────────────────┘
    ```
  exit 1 (부분 실패): data.errors 내용을 사용자에게 출력 후 [STOP]
    (머지는 완료됐으나 워크트리/브랜치 정리 중 일부 실패 — 수동 정리 필요)

  skipped_issues가 있으면 아래 형식으로 출력:
  ```
  ⚠ 머지 실패 이슈 — 워크트리가 그대로 남아있습니다. 직접 처리하세요:
  {이슈키마다 한 줄씩}
    워크트리: {root_path}/.claude/worktrees/{이슈키}
    재시도:   /worktree-flow:merge {피처브랜치}  (해당 워크트리 세션에서 실행)
  ```

[TERMINATE]
