---
name: autopilot-merge
description: 현재 워크트리를 피처 브랜치에 머지하여 통합한다.
---

# Worktree Merge

**실행 주체: Merger 에이전트 전용**
git push 금지.

## 사용법
`/autopilot:merge {피처브랜치}`

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
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/show_conflicts.py`
    충돌 파일마다:
      [GATE] AskUserQuestion("충돌: {파일명}\n{diff}\n\n선택: [auto / feature / base / 직접편집]")
      응답 "auto":
        파일을 Read로 읽어 conflict marker(<<<<<<< / ======= / >>>>>>>)를 파악
        충돌 내용 요약 출력 (ours = 피처브랜치 / theirs = 워크트리브랜치 각각 무엇을 변경했는지)
        양쪽 변경 내용을 분석하여 적절히 병합:
          - 서로 다른 내용 추가 → 양쪽 모두 포함
          - 같은 부분을 다르게 수정 → 맥락상 더 적절한 쪽 선택 (이유 명시)
        Edit으로 conflict marker를 제거하고 병합 결과 적용
        `cd {root_path} && git diff -- '{파일명}'` 실행하여 병합 결과 diff 출력
        [GATE] AskUserQuestion("위 병합 결과를 확인하세요.\n\n확인: [ok / 직접편집]")
        응답 "ok": `cd {root_path} && git add -- '{파일명}'` 실행
        응답 "직접편집": 직접편집 흐름으로 이동
      응답 "feature": `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py '{파일}' feature`
      응답 "base": `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py '{파일}' base`
      응답 "직접편집":
        [GATE] AskUserQuestion("편집 완료 후 'done' 입력")
        사용자가 'done' 입력 시:
          `grep -Ec "^(<{7} |>{7} )" '{root_path}/{파일명}'` 실행
          exit 0 이면 (마커 존재): "충돌 마커가 아직 남아있습니다." 출력 후 → [GATE] 반복
          exit 1 이면 (마커 없음): `cd {root_path} && git add -- '{파일명}'` 실행

    [--continue 전 최종 마커 검사]
      `cd {root_path} && git diff --name-only --cached` 로 staged 파일 목록 확보
      각 파일에 대해: `grep -lE "^(<{7} |>{7} )" '{root_path}/{파일명}'`
      마커가 남은 파일이 있으면:
        "아직 충돌 마커가 남아있는 파일: {목록}" 출력
        [STOP]

    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --branch {current_branch} --continue`
    exit 0: 워크트리 동기화 후 STEP 5
    exit 2: 다음 충돌 — 충돌 해결 프로세스 반복
    exit 1: 오류 출력 후 [STOP]

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
