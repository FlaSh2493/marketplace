---
name: review-fix
description: (명시적 커맨드 실행 전용) /autopilot:review-fix 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# CodeRabbit 리뷰 자동 반영

`/autopilot:review-fix` — 활성 리뷰가 있으면 수정·push 후 CodeRabbit의 새 리뷰를 폴링한다. 지적이 없으면 자동 종료.

```
STEP 1  커스텀 지침 로드
STEP 2  초기화 (컨텍스트 확보)
        ↓
  ┌─── LOOP ─────────────────────────────────────────┐
  │  STEP 3  리뷰 수집 + 폴링 결정                    │
  │  STEP 4  요약 표시 + [GATE-A] 처리 방식 선택      │
  │  STEP 5  수정 → 검증 → 보고                       │
  │  STEP 6  [GATE-B] 커밋/Push → 루프 복귀           │
  └──────────────────────────────────────────────────┘
```

---

## STEP 1: 커스텀 지침 로드

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_custom_instructions.py review-fix
```

로드된 지침을 **반드시 준수**한다. 표준 절차를 왜곡하지 않는다.

---

## STEP 2: 초기화

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_worktree.py HEAD
```
→ `worktree_path`, `current_branch`, `issue` 보관. 실패 시 [STOP]

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_state_dir.py --issue {issue} --clear review-fix
```

```bash
gh auth status 2>&1
```
실패 시: "gh 인증이 필요합니다." [STOP]

```bash
gh api user -q '.login'
```
→ `my_login` 보관

```bash
gh repo view --json nameWithOwner -q '.nameWithOwner'
```
→ `owner_repo` 보관

```bash
gh pr list --head '{current_branch}' --state open --json number -q '.[0].number // empty'
```
비어있으면: "열린 PR이 없습니다." [STOP]
→ `pr_number` 보관

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/review-fix/scripts/review_fix_state.py load '{worktree_path}' '{issue}'
```
→ `iteration_count`, `pushed_at`, `env_cache`, `max_iterations` 보관

**이후 모든 Bash 명령은 `cd '{worktree_path}' && command` 형태로 실행한다.**

---

## STEP 3: 리뷰 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/review-fix/scripts/fetch_reviews.py \
  {owner_repo} {pr_number} {worktree_path} \
  [--pushed-at {pushed_at}]
```

반환 필드: `has_reviews`, `active_count`, `new_since_push`, `is_in_progress`, `comments` (각 코멘트에 `severity` 포함)

### 폴링 결정표

| 상황 | 조건 | 결과 |
|------|------|------|
| 최초: 리뷰 없음 | `pushed_at=null` · `has_reviews=false` | ⏳ 폴링 |
| 최초: 리뷰 진행 중 | `pushed_at=null` · `has_reviews=true` · `active=0` · `is_in_progress=true` | ⏳ 폴링 |
| 최초: 리뷰 완료, 지적 없음 | `pushed_at=null` · `has_reviews=true` · `active=0` · `is_in_progress=false` | ✅ STOP |
| 최초: 활성 코멘트 있음 | `pushed_at=null` · `active≥1` | → STEP 4 |
| Push 후: CodeRabbit 응답 없음 | `pushed_at≠null` · `new_since_push=false` | ⏳ 폴링 |
| Push 후: 리뷰 진행 중 | `pushed_at≠null` · `new_since_push=true` · `is_in_progress=true` | ⏳ 폴링 |
| Push 후: 리뷰 완료, 지적 없음 | `pushed_at≠null` · `new_since_push=true` · `is_in_progress=false` · `active=0` | ✅ STOP |
| Push 후: 활성 코멘트 있음 | `pushed_at≠null` · `new_since_push=true` · `is_in_progress=false` · `active≥1` | → STEP 4 |

### 폴링 인터벌 및 가드

| 조건 | 동작 |
|------|------|
| 1~5회차 | `sleep 30` |
| 6회차 이상 | `sleep 60` |
| 총 대기 30분 초과 | "대기 시간 초과" [STOP] |
| `iteration_count >= max_iterations` | [STOP] |

---

## STEP 4: 요약 표시 · [GATE-A]

### 요약 표시

심각도별 개수를 표시한다. (참조: [reference/severity-rules.md](reference/severity-rules.md))

```
[루프 {iteration_count}회차] 활성 리뷰 {active_count}건 발견:
  critical [!]: {n}건
  important [*]: {n}건
  suggestion [~]: {n}건
  nitpick [.]: {n}건
```

### [GATE-A] 처리 방식 선택

```
AskUserQuestion:
"리뷰를 어떻게 처리하시겠습니까?
1. 전체 적용 (review-fixer 위임)
2. 코멘트별 선택 (메인 세션)
3. 상세 내용 보기
4. 종료"
```

- **3 선택 시:** 활성 코멘트 원문을 심각도 순으로 표시 후 [GATE-A]로 복귀. (참조: [reference/codereabbit-conventions.md](reference/codereabbit-conventions.md))
- **4 선택 시:** [STOP]

---

## STEP 5: 수정 · 검증 · 보고

### "1. 전체 적용" — review-fixer 서브에이전트 위임

1. **환경 탐지** (`env_cache=null`인 경우만):
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/review-fix/scripts/detect_env.py '{worktree_path}'
   ```
   → `env_cache` 보관

2. **맥락 요약:** 현재 대화 맥락을 3줄 이내로 요약한다.

3. **review-fixer agent 호출:** `skills/review-fix/agents/review-fixer.md` 지침에 따라 호출한다.
   - 입력: `comments` (nitpick 제외), `dismiss_ids` (nitpick id 목록), `env_cache`, `context_summary`

4. **결과 검증:** `check_result.failed`가 있으면 [templates/verification-failure.md](templates/verification-failure.md) 형식으로 출력 후 [STOP]

### "2. 코멘트별 선택" — 메인 세션 직접 처리

1. 코멘트를 심각도 순으로 제시하며 적용/스킵/중단을 묻는다.
2. 적용 시 `Read` → `Edit` (최소 범위) 수행.
3. 모든 처리 완료 후 **checker agent** (`skills/review-fix/agents/checker.md`)로 검증한다.
4. 검증 실패 시 [STOP]

### 보고

[templates/fix-report.md](templates/fix-report.md) 형식으로 결과를 요약 보고한다.

---

## STEP 6: 커밋 · Push · [GATE-B]

수정된 파일이 없으면 [STOP].

```
[GATE-B] AskUserQuestion:
"수정 결과를 커밋/Push 하시겠습니까?
1. 커밋 + Push
2. 커밋만
3. 롤백 후 종료"
```

| 선택 | 동작 |
|------|------|
| **1. 커밋 + Push** | 아래 순서 참조 |
| **2. 커밋만** | 커밋 후 [STOP] |
| **3. 롤백** | `git checkout -- .` 후 [STOP] |

**"1. 커밋 + Push" 처리 순서:**

1. **커밋:** `fix: apply CodeRabbit review feedback`
2. **Push:** `git push`
   - Non-fast-forward 실패 시: `pull --rebase` 진행 여부를 묻는다. 충돌 시 `rebase --abort` 후 [STOP]
3. **Reaction:** `add_reactions.py`로 처리된 모든 코멘트에 `+1` 추가
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/review-fix/scripts/add_reactions.py {owner_repo} '{comment_ids_json}' '+1'
   ```
4. **상태 저장 및 루프 복귀:** `pushed_at` = 현재 시각, `iteration_count++` 저장 후 즉시 STEP 3으로 복귀
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/review-fix/scripts/review_fix_state.py save ...
   ```

---

## 행동 규율

1. `fetch_reviews.py`가 분류한 `severity`를 임의로 변경하지 않는다.
2. 사용자가 "3. 상세 내용 보기"를 선택하기 전에는 코멘트 원문 전체를 표시하지 않는다.
3. 검증 실패 시 자동으로 추가 수정을 시도하지 않고 즉시 [STOP]한다.
4. Push 충돌 시 사용자 확인 없이 `force push`하거나 강제 `rebase`하지 않는다.
5. `iteration_count >= max_iterations` 도달 시 무조건 [STOP]한다.
