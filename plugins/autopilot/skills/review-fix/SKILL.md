---
name: review-fix
description: (명시적 커맨드 실행 전용) /autopilot:review-fix 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# CodeRabbit 리뷰 자동 반영 (loop)

## 사용법
`/autopilot:review-fix`

호출하면 loop을 시작합니다. 활성 리뷰가 있으면 수정·push 후 CodeRabbit이 새 리뷰를 올릴 때까지 자동 폴링합니다. CodeRabbit이 리뷰를 완료했는데 활성 코멘트가 없으면 자동 종료. 사용자가 종료를 선택하면 즉시 멈춥니다.

---

## STEP 0.5: 프로젝트 커스텀 지침 참조

[scripts/load_custom_instructions.py](scripts/load_custom_instructions.py)를 실행하여 프로젝트 지침을 확인한다.

```bash
python3 ../../scripts/load_custom_instructions.py review-fix
```

- **필수 참조**: 로드된 지침을 **반드시 준수**하며, 표준 절차를 왜곡하지 않고 행동한다.

---

## STEP 0: 컨텍스트 확보 및 초기화

```bash
python3 ../../scripts/resolve_worktree.py HEAD
```
- `status == "ok"` → `data`의 `worktree_path`, `current_branch`, `issue` 보관.
- `status == "error"` → reason 출력 후 [STOP]

```bash
python3 ../../scripts/init_state_dir.py --issue {data.issue} --clear review-fix
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
gh pr list --head '{data.branch}' --state open --json number -q '.[0].number // empty'
```
비어있으면 → "열린 PR이 없습니다." [STOP]
→ `pr_number` 보관

**상태 로드:**
```bash
python3 scripts/review_fix_state.py load '{worktree_path}' '{data.issue}'
```
→ `iteration_count`, `pushed_at`, `env_cache`, `max_iterations` 보관.

**이후 모든 Bash 명령은 `cd '{worktree_path}' && command` 형태로 실행한다.**

---

## 전체 흐름

```
[LOOP START] 
  iteration_count (default 1)
  max_iterations (default 20)
  pushed_at (null or ISO8601)

STEP 1: 리뷰 수집 (fetch_reviews.py)
  - 심각도 분류(critical, important, suggestion, nitpick) 포함

STEP 2: 요약 표시 및 상세 선택
  - [GATE-A] 적용 여부 및 상세 확인

STEP 3: 수정 → 검증 → 보고
  - review-fixer agent (서브에이전트 위임)
  - checker agent (검증)

STEP 4: 커밋 및 Push 확인
  - [GATE-B] 커밋/Push 여부

STEP 5: 상태 업데이트 및 폴링 루프 복귀
```

---

## STEP 1: 리뷰 수집

```bash
python3 scripts/fetch_reviews.py \
  {owner_repo} {pr_number} {worktree_path} \
  [--pushed-at {pushed_at}]
```

결과 필드: `has_reviews`, `active_count`, `new_since_push`, `comments` (각 코멘트에 `severity` 포함)

**폴링 로직 (pushed_at 기준):**

1. **pushed_at == null (최초 실행):**
   - `has_reviews == false`: ⏳ 대기 (아래 폴링 인터벌 참조) → STEP 1 재시도
   - `has_reviews == true + active_count == 0`: "✅ 활성 코멘트 없음." → [STOP]
   - `active_count >= 1`: STEP 2로 이동

2. **pushed_at != null (Push 후 폴링):**
   - `new_since_push == false`:
     - `active_count == 0`: "✅ 활성 코멘트 없음." → [STOP]
     - `active_count >= 1`: ⏳ 대기 (아희 폴링 인터벌 참조) → STEP 1 재시도
   - `new_since_push == true`:
     - `active_count == 0`: "✅ 활성 코멘트 없음." → [STOP]
     - `active_count >= 1`: STEP 2로 이동

**폴링 인터벌 및 가드:**
- 1~5회차 시도: 30초 대기 (`sleep 30`)
- 6회차 이상 시도: 60초 대기 (`sleep 60`)
- 총 대기 시간 30분 초과 시 → "대기 시간 초과" [STOP]
- `iteration_count >= max_iterations` 도달 시 → [STOP]

---

## STEP 2: 요약 표시 및 상세 선택

### 2-1. 요약 표시
활성 코멘트의 심각도별 개수를 요약하여 표시한다. (참조: [reference/severity-rules.md](reference/severity-rules.md))

```
[루프 {iteration_count}회차] 활성 리뷰 {active_count}건 발견:
- critical [!]: {n}건
- important [*]: {n}건
- suggestion [~]: {n}건
- nitpick [.]: {n}건
```

### [GATE-A] 적용 여부 확인
```
[GATE-A] AskUserQuestion:
"리뷰를 어떻게 처리하시겠습니까?
1. 전체 적용 (review-fixer 위임)
2. 코멘트별 선택 (메인 세션)
3. 상세 내용 보기
4. 종료
"
```

- **"3. 상세 내용 보기" 선택 시:**
  모든 활성 코멘트의 원문을 심각도 순으로 표시한 후 다시 **[GATE-A]**로 복귀한다.
  (참조: [reference/codereabbit-conventions.md](reference/codereabbit-conventions.md))

---

## STEP 3: 수정 → 검증 → 보고

### "1. 전체 적용" 선택 시 (서브에이전트 위임)

1. **환경 탐지 (캐시 확인):**
   `env_cache`가 null인 경우만 실행하고 결과를 저장한다.
   ```bash
   python3 scripts/detect_env.py '{worktree_path}'
   ```
   → `env_cache`에 보관.

2. **맥락 요약 생성:**
   현재 대화 맥락을 3줄 이내로 요약한다.

3. **review-fixer agent 호출:**
   `skills/review-fix/agents/review-fixer.md` 지침에 따라 서브에이전트를 호출한다.
   - 입력: `comments` (nitpick 제외), `dismiss_ids` (nitpick), `env_cache`, `context_summary` 등.

4. **결과 수신 및 검증:**
   `check_result.failed`가 있으면 [[templates/verification-failure.md]]를 사용하여 출력 후 [STOP].

---

### "2. 코멘트별 선택" 선택 시 (메인 세션)

1. 각 코멘트를 심각도 순으로 제시하며 적용/스킵/중단을 묻는다.
2. 적용 시 `Read` → `Edit` (최소 범위) 수행.
3. 모든 처리 완료 후 **checker agent** (`skills/review-fix/agents/checker.md`)를 호출하여 검증한다.
4. 검증 실패 시 [STOP].

---

### 3-3. 보고
[[templates/fix-report.md]] 형식을 사용하여 결과를 요약 보고한다.

---

## GATE-B: 커밋 및 Push 확인

수정된 파일이 없으면 [STOP].

```
[GATE-B] AskUserQuestion:
"수정 결과를 커밋/Push 하시겠습니까?
1. 커밋 + Push
2. 커밋만
3. 롤백 후 종료
"
```

- **"1. 커밋 + Push" 선택 시:**
  1. **커밋:** `fix: apply CodeRabbit review feedback` 메시지로 커밋.
  2. **Push:** `git push` 실행.
     - **Push 실패 시 (Non-fast-forward):**
       사용자에게 `pull --rebase` 진행 여부를 묻는다. 승인 시 진행, 충돌 시 `rebase --abort` 후 [STOP].
  3. **Reaction:** `scripts/add_reactions.py`를 사용하여 처리된 모든 코멘트에 `+1` 추가.
  4. **상태 저장 및 루프 진행:**
     `pushed_at`을 현재 시각으로 갱신, `iteration_count++` 후 `scripts/review_fix_state.py save` 실행.
     **사용자 확인 없이 즉시 STEP 1으로 자동 복귀.**

- **"2. 커밋만" 선택 시:** 커밋 후 [STOP].
- **"3. 롤백" 선택 시:** `git checkout -- .` 실행 후 [STOP].

---

## 행동 규율

1. `fetch_reviews.py`가 분류한 `severity`를 임의로 변경하지 않는다.
2. 사용자가 "3. 상세 내용 보기"를 요청하기 전에는 코멘트 원문 전체를 표시하지 않는다.
3. 검증 실패 시 자동으로 추가 수정을 시도하지 않고 즉시 [STOP] 한다.
4. Push 충돌 시 사용자 확인 없이 `force push` 하거나 강제로 `rebase` 하지 않는다.
5. `iteration_count >= max_iterations` 도달 시 무조건 [STOP] 한다.
