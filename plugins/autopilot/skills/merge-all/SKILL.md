---
name: autopilot-merge-all
description: 피처 브랜치의 모든 활성 워크트리를 충돌 수 기준으로 정렬하여 순차적으로 머지하고 워크트리를 동기화한다.
---

# Worktree Merge All

**실행 주체: 어느 세션에서든 실행 가능**
git push 금지.

## 사용법
`/autopilot:merge-all [{피처브랜치}]`
- 피처브랜치 생략 시 활성 워크트리의 `.autopilot`에서 공통 `base_branch` 자동 감지

---

## STEP 0.5: 프로젝트 커스텀 지침 참조

[_shared/CUSTOM_INSTRUCTIONS.md](../_shared/CUSTOM_INSTRUCTIONS.md)에 따라 다음 명령을 실행하여 프로젝트 지침을 확인한다.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_custom_instructions.py merge-all
```

- **필수 참조**: 로드된 지침을 **반드시 준수**하며, 표준 절차를 왜곡하지 않고 행동한다.

---

## STEP 0: 컨텍스트 확보 및 초기화
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/list_worktrees.py --require-autopilot --infer-common-base
  ```
  - `status == "ok"`:
    - `data`의 `main_root_path`, `main_root_branch` 보관.
    - `common_base_branch`가 있으면 `{피처브랜치}`로 확정.
    - 없으면 `base_branch_candidates` 목록으로 제시, AskUserQuestion으로 선택하여 `{피처브랜치}` 확정.
  - `status == "error"` → reason 출력 후 [STOP].

  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --dry-run`
  실패 (exit 1): reason 출력 후 [STOP]
  merge_order가 비어있으면: "머지할 워크트리가 없습니다." 출력 후 [STOP]

  각 워크트리(merge_order)마다 상태 초기화:
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_state_dir.py --issue {wt_issue} --clear merge merge-all pr review-fix
  ```

  결과 표시 (branch + issues 함께 표시):
  ```
  머지 순서 (충돌 적은 순):
  ┌──────┬──────────────────────────┬──────────────┬────────┬────────┐
  │ 순서 │ 브랜치                    │ 이슈          │ WIP수  │ 충돌   │
  ├──────┼──────────────────────────┼──────────────┼────────┼────────┤
  │  1   │ feat/filter               │ PLAT-101     │  3개   │  0개   │
  │  2   │ feat/export               │ PLAT-102,103 │  1개   │  2개   │
  └──────┴──────────────────────────┴──────────────┴────────┴────────┘
  ```

[GATE] STEP 2: 머지 계획 승인
  ⚡ 품질 검사를 아직 실행하지 않았다면 `/autopilot:check-all`로 먼저 검사를 권장합니다.
  AskUserQuestion("위 순서로 전체 머지를 진행할까요? (yes / no)")
  응답 "no": "머지 취소." [TERMINATE]
  응답 "yes": STEP 3 진행

STEP 3: 전체 워크트리 커밋 + 요구사항 동기화
  skipped_branches = []

  merge_order의 각 항목에 대해 순서대로:
    branch = merge_order[i].branch
    issues = merge_order[i].issues
    worktree_path = merge_order[i].path

    [미커밋 변경사항 커밋]
    `cd {worktree_path} && git status --porcelain` 실행
    변경사항 있으면:
      1. 전체 변경사항 파악:
         - `cd {worktree_path} && git diff HEAD`
         - `cd {worktree_path} && git ls-files --others --exclude-standard`
         신규 파일은 내용도 Read하여 분석에 포함
      2. 변경사항을 논리적 단위로 그룹핑
      3. scope 결정: issues[0]이 있으면 이슈키, 없으면 branch
      4. 각 그룹별로 순서대로 커밋 (subject + body):
         - subject: `{type}({scope}): {단위 요약}`
         - body:
           ```
           요구사항: {이 변경이 필요한 이유 / 요청된 내용}
           작업내용: {실제 변경 내용 (파일별로 간략히)}
           특이사항: {주요 결정, 트레이드오프, 제약사항 (없으면 생략)}
           ```
         Write("/tmp/commit_msg_{branch 슬래시를 _ 로 치환}.txt", "{subject}\n\n{body 전체}")
         그룹에 속한 파일만 개별 quote하여 stage 후 커밋:
         ```
         cd {worktree_path} && git add -- {shlex.quote(파일1)} ... && git commit -F /tmp/commit_msg_*.txt
         ```

    [피처브랜치 최신화 (rebase)]
    `cd {worktree_path} && git fetch origin {피처브랜치}` 실행
    origin/{피처브랜치} 존재 시:
      `cd {worktree_path} && git rebase origin/{피처브랜치}` 실행
      충돌 시:
        Read(`${CLAUDE_PLUGIN_ROOT}/skills/_shared/CONFLICT_RESOLUTION.md`) 후 절차를 따른다.
        변수: resolve_root={worktree_path}, 피처브랜치={피처브랜치}, branch={branch}
        충돌 해결 완료 후 `cd {worktree_path} && git rebase --continue`
        충돌 해결 실패 시: skipped_branches에 추가, 다음 브랜치로
      성공: 계속 진행
    origin/{피처브랜치} 없으면 (로컬 only): rebase 생략, 계속 진행

    [요구사항 동기화] (issues가 비어있으면 스킵)
    ```bash
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_requirements.py extract-log '{worktree_path}' '{피처브랜치}'
    ```
    - `status == "ok"`:
      - `data.requirements` 항목들에 대해 issues의 이슈키별로:
        ```bash
        python3 scripts/load_issue.py {이슈키}  → md_path 확보
        python3 scripts/extract_requirements.py upsert-doc {md_path} --req-items {requirements 목록}
        ```
    - `status == "error"`: 경고 출력 후 다음으로


[GATE] STEP 4: 머지 승인
  각 브랜치의 커밋 목록 표시 (STEP 3에서 수집한 log)
  AskUserQuestion("위 커밋들을 {피처브랜치}에 머지할까요? (yes / no)")
  응답 "no": "머지 취소." [TERMINATE]
  응답 "yes": STEP 5 진행

STEP 5: 순서대로 머지 실행
  merged_branches = []

  merge_order의 각 항목에 대해 순서대로 (skipped_branches 제외):
    branch = 현재 브랜치
    worktree_path = merge_order[i].path

    실행:
    ```
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --branch {branch}
    ```
    exit 0: 워크트리 동기화 → merged_branches에 추가, 다음으로
    exit 1: 오류 출력, 해당 브랜치 건너뜀, 다음으로
    exit 2 (충돌): 충돌 해결 프로세스 진입

    [워크트리 동기화] — 머지 성공 시 (충돌 해결 후 포함)
      ```
      cd {main_root_path} && git checkout {main_root_branch}
      cd {worktree_path} && git merge --ff-only {피처브랜치}
      ```

    [충돌 해결 프로세스] — 머지 충돌은 main_root_path(피처 브랜치 체크아웃 상태)에서 발생
      Read(`${CLAUDE_PLUGIN_ROOT}/skills/_shared/CONFLICT_RESOLUTION.md`) 후 절차를 따른다.
      변수: resolve_root={main_root_path}, 피처브랜치={피처브랜치}, branch={branch}

      충돌 해결 실패 시 (exit 1):
        해당 브랜치 건너뜀 (skipped_branches에 추가), 다음으로

      충돌 해결 완료 후:
      실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --branch {branch} --continue`
      exit 0: 워크트리 동기화 → merged_branches에 추가, 다음으로
      exit 2: 다음 충돌 — 충돌 해결 프로세스 반복
      exit 1: 오류 출력, 해당 브랜치 건너뜀, 다음으로

STEP 6: 완료 출력
  merged_branches가 비어있으면: "머지된 워크트리가 없습니다." [TERMINATE]

  ```
  ┌──────────────────────────────────────────────────────────┐
  │ 전체 머지 완료                                            │
  │ 브랜치: {피처브랜치}                                      │
  │ 처리된 워크트리: {merged_branches 목록}                   │
  └──────────────────────────────────────────────────────────┘
  ```

  skipped_branches가 있으면 아래 형식으로 출력:
  ```
  ⚠ 머지 실패 워크트리:
  {브랜치마다 한 줄씩}
    재시도: /autopilot:merge {워크트리브랜치}  (메인 세션에서 실행)
  ```

  이후 AskUserQuestion으로 다음 선택지 제시:
  ```
  머지가 완료되었습니다. 다음 중 선택하세요:
  1. `/autopilot:pr` — PR 생성
  2. `/autopilot:cleanup` — 머지 완료된 워크트리 정리
  3. 추가 작업 계속
  ```

[TERMINATE]
