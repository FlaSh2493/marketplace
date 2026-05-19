---
name: review-fix
description: (명시적 커맨드 실행 전용) /autopilot:review-fix 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# 리뷰 반영

> **금지:** force push (사용자 확인 없이) / `max_iterations` 초과 후 계속 실행 / 검증 실패 후 자동 추가 수정 시도

> **종료 규칙:** 어떤 이유로든 [STOP]할 때는 `~/Documents/autopilot/{issue}/review.md`에 중단 시점(STEP)과 이유를 append한다 (기존 이터레이션 이력과 같은 파일). issue 미확보(STEP 2 resolve_worktree 실패) 시 `{current_branch 또는 HEAD}` fallback.

활성 리뷰 수집 → 수정 → push → 재폴링 루프.

## 흐름 개요

```
STEP 1  커스텀 지침 로드
STEP 2  초기화
        ↓
  ┌─── LOOP ──────────────────────────────────────┐
  │  STEP 3  리뷰 수집 + 폴링 결정                 │
  │  STEP 4  [GATE] 처리 방식 선택                 │
  │  STEP 5  수정 → 검증 → 보고                    │
  │  STEP 6  [GATE] 커밋 · Push → 루프 복귀        │
  └───────────────────────────────────────────────┘
```

---

## STEP 1: 커스텀 지침 로드

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_custom_instructions.py review-fix
```

---

## STEP 2: 초기화

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_worktree.py HEAD
```
→ `worktree_path`, `current_branch`, `issue` 보관. 실패 시 [STOP]

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_state_dir.py --issue {issue} --clear review-fix
gh auth status 2>&1 || { echo "gh 인증 필요"; exit 1; }
gh api user -q '.login'          # → my_login
gh repo view --json nameWithOwner -q '.nameWithOwner'  # → owner_repo
gh pr list --head '{current_branch}' --state open --json number -q '.[0].number // empty'  # → pr_number (없으면 STOP)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/review-fix/scripts/review_fix_state.py load '{issue}'
```
→ `iteration_count`, `pushed_at`, `env_cache`, `max_iterations` 보관

---

## STEP 3: 리뷰 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/review-fix/scripts/fetch_reviews.py \
  {owner_repo} {pr_number} {worktree_path} [--pushed-at {pushed_at}]
```

반환: `has_reviews`, `active_count`, `new_since_push`, `is_in_progress`, `comments` (severity 포함)

**폴링 결정:**

| 조건 | 결과 |
|---|---|
| `active≥1` | → STEP 4 |
| 리뷰 완료 + `active=0` + `is_in_progress=false` | ✅ STOP |
| 그 외 (리뷰 없음 / 진행 중 / push 후 응답 없음) | ⏳ 폴링 |

**폴링 인터벌:** 1~5회 `sleep 30`, 6회+ `sleep 60`. 30분 초과 또는 `iteration_count >= max_iterations` → [STOP]

---

## STEP 4: [GATE] 처리 방식 선택

심각도별 개수 표시 (`critical/important/suggestion/nitpick`).

AskUserQuestion: "리뷰를 어떻게 처리하시겠습니까? 1) 전체 적용 2) 코멘트별 선택 3) 상세 내용 보기 4) 종료"

- **3 선택:** 활성 코멘트 원문 표시 후 [GATE-A] 복귀
- **4 선택:** [STOP]

---

## STEP 5: 수정 · 검증 · 보고

### 전체 적용 (1)

1. `env_cache=null`인 경우:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/review-fix/scripts/detect_env.py '{worktree_path}'
   ```
2. 현재 맥락 3줄 이내 요약 → `context_summary`
3. `agents/review-fixer.md` 호출 (입력: `comments` nitpick 제외, `dismiss_ids`, `env_cache`, `context_summary`)
4. `check_result.failed` 있으면 `templates/verification-failure.md` 형식 출력 후 [STOP]

### 코멘트별 선택 (2)

심각도 순으로 각 코멘트 제시 → 적용/스킵/중단 선택. 적용 시 Read → Edit (최소 범위).
전체 처리 후 `agents/checker.md`로 검증. 실패 시 [STOP].

### 보고

`templates/fix-report.md` 형식으로 결과 요약.

---

## STEP 6: [GATE] 커밋 · Push

수정 파일 없으면 [STOP].

AskUserQuestion: "수정 결과를 어떻게 처리하시겠습니까? 1) 커밋 + Push 2) 커밋만 3) 롤백"

| 선택 | 동작 |
|---|---|
| 커밋 + Push | 커밋 → `git push` → add_reactions.py → pushed_at/iteration_count 저장 → STEP 3 복귀 |
| 커밋만 | 커밋 후 [STOP] |
| 롤백 | `git checkout -- .` 후 [STOP] |

push Non-fast-forward 실패 시: `pull --rebase` 여부 확인. 충돌 시 `rebase --abort` 후 [STOP].

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/review-fix/scripts/add_reactions.py {owner_repo} '{comment_ids_json}' '+1'
python3 ${CLAUDE_PLUGIN_ROOT}/skills/review-fix/scripts/review_fix_state.py save '{issue}' --iteration {iteration_count} --pushed-at {iso_now}
```

---

