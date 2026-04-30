---
name: pr
description: (명시적 커맨드 실행 전용) /autopilot:pr 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# PR 생성

## 사용법
`/autopilot:pr [{브랜치}]` — 브랜치 생략 시 현재 브랜치 또는 목록에서 선택

```
STEP 1  커스텀 지침 로드
STEP 2  컨텍스트 확보 및 초기화
STEP 3  사전 검증
STEP 4  도메인 라벨 추론
STEP 5  본인 계정 확보
STEP 6  PR 컨텐츠 분석 데이터 확보
STEP 7  PR 제목 및 본문 생성
STEP 8  [GATE] PR 내용 최종 확인
STEP 9  Push 및 상태 기록
STEP 10 PR 생성
STEP 11 완료 출력
```

---

## STEP 1: 커스텀 지침 로드

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_custom_instructions.py pr
```

로드된 지침과 [reference/pr-conventions.md](reference/pr-conventions.md) 규약을 **반드시 준수**한다.

---

## STEP 2: 컨텍스트 확보 및 초기화

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_worktree.py '{브랜치}' --infer-base-by-commit-count
```

- `status == "ok"` → `worktree_path`, `resolved_branch`, `base_branch`, `safe_branch`, `root_path`, `issue` 보관
- `status == "error"`:
  - `reason == "WORKTREE_NOT_FOUND"`: `list_worktrees.py` 실행 후 목록 제시, AskUserQuestion으로 선택. 선택된 브랜치로 재실행.
  - 그 외: reason 출력 후 [STOP]

**모드 결정:**
- **워크트리 모드**: `worktree_path ≠ root_path`
- **직접 모드**: `worktree_path`가 없거나 `root_path`와 같을 때 (`worktree_path = root_path`로 간주)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_state_dir.py --issue {data.issue} --clear pr review-fix && \
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/pr_state.py write --issue {data.issue} --phase init --branch {resolved_branch}
```

**이후 모든 Bash 명령은 `cd '{worktree_path}' && command` 형태로 실행한다.**

---

## STEP 3: 사전 검증

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/precheck_pr.py --worktree '{worktree_path}' --base {base_branch} --branch '{resolved_branch}'
```

- `status == "error"`: 에러 메시지 출력 후 [STOP]
- `status == "ok"`: `data.commit_count`, `data.over_limit` 확인

**[GATE] 커밋 개수 초과 시:**
`over_limit == true`이면 AskUserQuestion: "커밋이 {commit_count}개로 50개를 초과합니다. 베이스 브랜치({base_branch})가 올바른지 확인하세요. 계속 진행할까요? (yes/no)"
- "no" → [STOP]
- "yes" → 계속

---

## STEP 4: 도메인 라벨 추론

[reference/label-rules.md](reference/label-rules.md)를 참고한다.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/infer_labels.py '{worktree_path}' {base_branch}
```

→ `data.labels[]` 보관 (실제 리포지토리에 존재하는 라벨만 반환됨)

---

## STEP 5: 본인 계정 확보

```bash
gh api user -q .login
```

실패 시: "GitHub 사용자 정보를 가져올 수 없습니다." 출력 후 [STOP]
→ `login` 보관

---

## STEP 6: PR 컨텐츠 분석 데이터 확보

전체 diff 대신 요약된 통계와 커밋 로그만 확보하여 토큰 소비를 최소화한다.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/prepare_pr_content.py '{worktree_path}' {base_branch} '{resolved_branch}'
```

→ `commits`, `stats`, `major_areas`, `suggested_type`, `suggested_scope`, `issue_key`, `issue_keys` 확보

`issue_keys`: 브랜치명에서 먼저 추출, 없으면 커밋 메시지 전체에서 수집한 Jira 이슈키 배열 (중복 제거, 순서 유지)

---

## STEP 7: PR 제목 및 본문 생성

[templates/pr-title.md](templates/pr-title.md)와 [templates/pr-body.md](templates/pr-body.md)를 사용하여 STEP 6 데이터 기반으로 작성한다.

**이슈키 렌더링 규칙:**
- `{issue_keys}`: 배열을 `, `로 join (예: `PROJ-123, PROJ-456`)
- `{issue_keys_list}`: 각 이슈키를 한 줄씩 나열 (예: `- PROJ-123\n- PROJ-456`)
- `issue_keys`가 비어있으면 PR 제목의 `[{issue_keys}]`와 본문의 `## Related Issues` 섹션을 생략한다.

**저장:** `/tmp/pr_{safe_branch}_title.txt`, `/tmp/pr_{safe_branch}_body.txt`

---

## STEP 8: [GATE] PR 내용 최종 확인

사용자에게 제목, 본문, 라벨을 보여주고 확인을 요청한다.

AskUserQuestion: "위 내용으로 PR을 생성할까요? (yes / 수정사항 / no)"
**[응답 전 push/PR 생성 금지]**

- "yes" → STEP 9 진행
- "no" → "PR 생성 취소." [STOP]
- 그 외 → 수정 요청 반영 후 STEP 8 재실행

---

## STEP 9: Push 및 상태 기록

```bash
cd '{worktree_path}' && git push -u origin HEAD && \
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/pr_state.py write --issue {data.issue} --phase push_done --push-done true
```

실패 시: 오류 메시지 출력 후 [STOP]

---

## STEP 10: PR 생성

```bash
cd '{worktree_path}' && TITLE=$(cat '/tmp/pr_{safe_branch}_title.txt') && \
  gh pr create \
    --base {base_branch} \
    --assignee '{login}' \
    {각 라벨별 --label '{라벨}'} \
    --title "$TITLE" \
    --body-file '/tmp/pr_{safe_branch}_body.txt'
```

- 성공 시: `pr_url` 보관 및 상태 업데이트:
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/pr_state.py write --issue {data.issue} --phase completed
  ```
- 실패 시: 수동 생성 명령어 안내 후 [STOP]

---

## STEP 11: 완료 출력

```
┌───────────────────────────────────────────────┐
│ PR 생성 완료                                   │
│ URL: [{pr_url}]({pr_url})                      │
│ Base: {base_branch} ← {resolved_branch}        │
│ Labels: {labels}                               │
└───────────────────────────────────────────────┘
```

[reference/after-pr-menu.md](reference/after-pr-menu.md)에 따라 후속 선택지를 제시한다.

[STOP]
