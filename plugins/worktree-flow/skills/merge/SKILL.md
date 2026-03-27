---
name: merge
description: 현재 워크트리를 피처 브랜치에 squash merge로 통합하고 워크트리를 정리한다. 워크트리 브랜치는 태그로 보존된다.
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

STEP 1: 요구사항 동기화
  현재 대화 히스토리에서 요구사항 성격의 내용 추출:
  - 요구사항: 기능 추가/변경/조건/수정 요청
  - 제외: 단순 컨텍스트, 정보 제공, 질문

  추출된 요구사항이 있으면:
    1. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키}` 실행 → data.md_path 확보
    2. data.md_path 의 `## 추가 요구사항` 섹션 끝에 append (섹션 없으면 파일 끝에 생성)

STEP 2: WIP 커밋
  `cd {worktree_path} && git status --porcelain` 실행
  변경사항 없으면: 스킵
  변경사항 있으면:
    1. 전체 변경사항 파악:
       - `cd {worktree_path} && git diff HEAD` — staged + unstaged 전체 수정사항 (git diff만 쓰면 staged 누락)
       - `cd {worktree_path} && git ls-files --others --exclude-standard` — 신규 untracked 파일 목록
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
       Write 도구로 /tmp/wip_msg_{이슈키}.txt에 저장 (쉘 quoting·병렬 세션 충돌 방지):
       - Write("/tmp/wip_msg_{이슈키}.txt", "{subject}\n\n{body 전체}")
       그룹에 속한 파일만 개별 quote하여 stage 후 커밋:
       ```
       cd {worktree_path} && git add -- {shlex.quote(파일1)} {shlex.quote(파일2)} ... && git commit -F /tmp/wip_msg_{이슈키}.txt
       ```
       파일명에 공백이 있을 수 있으므로 각 경로를 반드시 따옴표로 감쌀 것. 전체 add(`git add -A`)는 금지 — 다른 그룹 파일이 섞임.
    최종 커밋 메시지(feat/fix 등)는 squash 시 결정

STEP 3: WIP 커밋 요약 및 커밋 메시지 제안
  merge-base + git log를 단일 Bash 호출로 실행 (변수가 다음 호출로 이어지지 않음):
  ```bash
  cd '{worktree_path}' && \
    MERGE_BASE=$(git merge-base "origin/{피처브랜치}" HEAD 2>/dev/null || git merge-base "{피처브랜치}" HEAD 2>/dev/null) && \
    [ -n "$MERGE_BASE" ] && git log "$MERGE_BASE"..HEAD --oneline || echo "MERGE_BASE_NOT_FOUND"
  ```
  출력이 "MERGE_BASE_NOT_FOUND" 이면 "머지 베이스를 찾을 수 없습니다." 출력 후 [STOP]
  그 외: WIP 커밋 목록 표시 후 변경 내용 요약하여 커밋 메시지 제안
  출력 형식:
  ```
  커밋 메시지 제안: feat({이슈키}): {설명}
  ```

[GATE] STEP 4: 커밋 메시지 승인
  AskUserQuestion("이 커밋 메시지로 진행할까요? (수정이 필요하면 내용을 입력하세요 / no: 취소)")
  [LOCK: 응답 전 머지 실행 금지]

  응답 "yes": STEP 5 진행
  응답 "수정 {내용}": 메시지 반영 후 재표시 → STEP 4 반복
  응답 "no": 출력 "머지 취소." [TERMINATE]

STEP 5: Squash merge 실행
  커밋메시지를 Write 도구로 /tmp/merge_msg_{이슈키}.txt에 저장 (쉘 quoting·병렬 세션 충돌 방지):
  - Write("/tmp/merge_msg_{이슈키}.txt", "{커밋메시지 전체 내용}")
  실행:
  ```
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --issue {이슈키} --message "$(cat /tmp/merge_msg_{이슈키}.txt)"
  ```
  성공 (exit 0): STEP 6 진행
  충돌 (exit 2): 충돌 해결 프로세스 진입

  [충돌 해결 프로세스] — 충돌은 메인 리포(피처 브랜치)에 발생하므로 아래 명령은 cd prefix 없이 실행
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/show_conflicts.py`
    충돌 파일마다:
      [GATE] AskUserQuestion("충돌: {파일명}\n{diff}\n\n선택: [feature / base / 직접편집]")
      응답 "feature": `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py '{파일}' feature`
      응답 "base": `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py '{파일}' base`
      응답 "직접편집":
        [GATE] AskUserQuestion("편집 완료 후 'done' 입력")
        사용자가 'done' 입력 시:
          `grep -c "^<<<<<<< " '{파일명}'` 실행
          exit 0 이면 (마커 존재): "충돌 마커(<<<<<<<)가 아직 남아있습니다. 파일을 다시 확인하세요." 출력 후 → [GATE] 반복
          exit 1 이면 (마커 없음): `git add -- '{파일명}'` 실행
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --issue {이슈키} --message "$(cat /tmp/merge_msg_{이슈키}.txt)" --continue`
    (--continue 시에는 /tmp/merge_msg_{이슈키}.txt가 이미 STEP 5에서 작성된 상태)

STEP 6: 정리
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cleanup_worktrees.py {피처브랜치} --issues {이슈키}`
  exit 0 (전체 성공):
    ```
    ┌───────────────────────────────────────────────┐
    │ 머지 완료                                      │
    │ 브랜치: {피처브랜치}                           │
    │ 처리된 이슈: {이슈키}                          │
    │ WIP 보존 태그: archive/{피처}/{이슈키}-wip-{날짜} │
    └───────────────────────────────────────────────┘
    ```
  exit 1 (부분 실패): data.errors 내용을 사용자에게 출력 후 [STOP]
    (머지는 완료됐으나 워크트리/브랜치 정리 중 일부 실패 — 수동 정리 필요)

[TERMINATE]
