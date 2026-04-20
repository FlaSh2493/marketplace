---
name: autopilot-review-fix
description: PR의 CodeRabbit 리뷰 코멘트를 루프 방식으로 자동 반영. 새 리뷰가 달릴 때마다 물어보고 수정한다. "리뷰 반영", "코드래빗 수정", "review fix" 등을 요청할 때 사용한다.
---

# CodeRabbit 리뷰 자동 반영 (loop)

## 사용법
`/autopilot:review-fix`

호출하면 loop을 시작합니다. 활성 리뷰가 있으면 수정·push 후 CodeRabbit이 새 리뷰를 올릴 때까지 자동 폴링합니다. CodeRabbit이 리뷰를 완료했는데 활성 코멘트가 없으면 자동 종료. 사용자가 종료를 선택하면 즉시 멈춥니다.

---

## STEP 0.5: 프로젝트 커스텀 지침 참조

[_shared/CUSTOM_INSTRUCTIONS.md](../_shared/CUSTOM_INSTRUCTIONS.md)에 따라 다음 명령을 실행하여 프로젝트 지침을 확인한다.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_custom_instructions.py review-fix
```

- **필수 참조**: 로드된 지침을 **반드시 준수**하며, 표준 절차를 왜곡하지 않고 행동한다.

---

## 전체 흐름

```
[LOOP START] iteration_count = 1, max_iterations = 20
             pushed_at = null  ← push 완료 시각. null이면 "최초 실행" 상태

STEP 1: 컨텍스트 확보 (worktree_path, branch, PR)
  └─ 실패 → [STOP]

STEP 2: 리뷰 수집 (fetch_reviews.py)
  pushed_at == null (최초 실행):
    └─ CodeRabbit 리뷰 미제출 → 30초 대기 → STEP 1 재시도 (최대 30분)
    └─ 리뷰 있음 + 활성 0건 → [AUTO STOP]
    └─ 리뷰 있음 + 활성 1건+ → STEP 3
  pushed_at != null (push 후 폴링 중):
    └─ new_since_push == false + 활성 0건 → [AUTO STOP]
    └─ new_since_push == false + 활성 1건+ → 30초 대기 → STEP 1 재시도
    └─ new_since_push == true + 활성 0건 → [AUTO STOP]
    └─ new_since_push == true + 활성 1건+ → STEP 3

STEP 3: 원문 표시

[GATE-A] 적용 여부 확인
  └─ "1" → 전체 적용 (review-fixer agent)
  └─ "2" → 코멘트별 선택 (메인에서 순차 처리)
  └─ "3" → [STOP]

STEP 5: 수정 → 검증 → 보고

[GATE-B] 커밋 확인
  └─ "1" → 커밋 + push → pushed_at 갱신 → +1 reaction → iteration_count++ → STEP 1 자동 복귀
  └─ "2" → 커밋만 → [STOP]
  └─ "3" → 롤백 → [STOP]
```

---

## STEP 1: 컨텍스트 확보

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_worktree.py HEAD → data 확보 (worktree_path, current_branch, issue)
# 실패 → [STOP]

gh auth status 2>&1                              # 실패 → "gh 인증이 필요합니다." [STOP]
# 상태 초기화:
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_state_dir.py --issue {data.issue} --clear review-fix
gh api user -q '.login' → my_login
gh repo view --json nameWithOwner -q '.nameWithOwner' → owner_repo
gh pr list --head '{data.branch}' --state open --json number -q '.[0].number // empty' → pr_number
# 비어있으면 → "열린 PR이 없습니다." [STOP]
```

**이후 모든 Bash 명령은 `cd '{worktree_path}' && command` 형태로 실행한다.**

---

## STEP 2: 리뷰 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/fetch_reviews.py \
  {owner_repo} {pr_number} {worktree_path} \
  [--pushed-at {pushed_at}]   # pushed_at != null 일 때만 추가
```

결과 필드: `has_reviews`, `active_count`, `new_since_push`, `review_bodies`, `comments`

**pushed_at == null (최초 실행):**

- `has_reviews == false`:
  ```
  ⏳ CodeRabbit 리뷰 대기 중... (경과: {elapsed}초)
  ```
  30초 대기(`sleep 30`) → STEP 1 재시도
  총 대기 30분 초과 시 → [STOP]
- `has_reviews == true + active_count == 0`:
  완료 마커:
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/state_manager.py mark review-fix --issue {data.issue}
  ```
  "✅ CodeRabbit 리뷰 완료. 활성 코멘트 없음. 자동 종료합니다." → [STOP]
- `has_reviews == true + active_count >= 1`: STEP 3으로

**pushed_at != null (push 후 폴링 중):**

- `new_since_push == false + active_count == 0`:
  완료 마커:
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/state_manager.py mark review-fix --issue {data.issue}
  ```
  "✅ 활성 코멘트 없음. 자동 종료합니다." → [STOP]
- `new_since_push == false + active_count >= 1`:
  ```
  ⏳ CodeRabbit 리뷰 대기 중... (push: {pushed_at}, 경과: {elapsed}초)
  ```
  30초 대기 → STEP 1 재시도 (30분 초과 시 [STOP])
- `new_since_push == true + active_count == 0`:
  완료 마커:
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/state_manager.py mark review-fix --issue {data.issue}
  ```
  "✅ CodeRabbit 리뷰 완료. 활성 코멘트 없음. 자동 종료합니다." → [STOP]
- `new_since_push == true + active_count >= 1`: STEP 3으로
- `status == "error"`: 에러 메시지 출력 → [STOP]

---

## STEP 3: 원문 표시

### 3-1. 심각도 분류

| 심각도 | 기준 | 표시 |
|--------|------|------|
| **critical** | 버그, 보안 취약점, 데이터 손실 가능성 | `[!]` |
| **important** | 로직 오류, 성능 문제, 타입 불일치 | `[*]` |
| **suggestion** | 리팩토링, 네이밍, 코드 스타일 개선 | `[~]` |
| **nitpick** | 포맷팅, 사소한 선호도 차이 | `[.]` |

### 3-2. 원문 표시

critical → important → suggestion → nitpick 순으로:

```
[루프 {iteration_count}회차] CodeRabbit 리뷰 {active_count}건 (전체 {total_count}건 중 활성):

━━━━━━━━━━━━━━━━━━━━━━━━━━
[!] {파일명}:{line}
{코멘트 body 원문}
━━━━━━━━━━━━━━━━━━━━━━━━━━
[*] {파일명}:{line}
{코멘트 body 원문}
━━━━━━━━━━━━━━━━━━━━━━━━━━
...
```

---

## STEP 4 → GATE-A: 적용 여부 확인

```
[GATE-A] AskUserQuestion (PENDING — 파일 수정 금지):
"위 리뷰를 적용하겠습니까?
1. 전체 적용 (nitpick은 dismiss) ← 권장
2. 코멘트별 선택
3. 종료
"
[LOCK: 응답 전 파일 수정 금지]
```

---

## STEP 5: 수정 → 검증 → 보고

### "1. 전체 적용" 선택 시 — review-fixer agent

현재 세션 대화에서 구현 맥락 요약 생성 (핵심 결정·제약 2~5줄).

환경 탐지:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/detect_env.py {worktree_path}
```

**review-fixer agent 호출**:
```
입력:
  worktree_path: {worktree_path}
  comments:      active_count >= 1인 코멘트 중 nitpick 제외 대상
  dismiss_ids:   nitpick 코멘트 id 목록
  owner_repo:    {owner_repo}
  pr_number:     {pr_number}
  context_summary: {생성한 맥락 요약}
  env:           detect_env.py 결과 (첫 번째 앱)
```

결과 수신: `{ applied, skipped, dismissed, fixed_files, check_result }`

검증 실패 시 (check_result.failed 있음):
```
❌ 검증 미통과 — 루프를 중단합니다.
실패 검사: {검사명}
시도: {attempt}회
남은 에러:
{last_error}

잔여 에러 해결 후 /autopilot:check 또는 /autopilot:review-fix를 재실행하세요.
```
→ [STOP]

수정된 파일 없으면 → "적용할 수정사항이 없었습니다." [STOP]

---

### "2. 코멘트별 선택" 선택 시 — 메인에서 순차 처리

각 코멘트를 critical → important → suggestion → nitpick 순으로:

```
[{심각도}] {파일명}:{line}
━━━━━━━━━━━━━━━━━━━━━━━━━━
{코멘트 body 원문}
━━━━━━━━━━━━━━━━━━━━━━━━━━
→ 적용 / 스킵 / 중단?
```

- 적용: 해당 파일 `{worktree_path}/파일경로` Read → Edit (최소 범위, 라인 역순 처리)
- 스킵: 스킵 목록에 추가
- 중단: [STOP]

**nitpick/스킵 dismiss**:
```bash
gh api repos/{owner_repo}/pulls/{pr_number}/comments/{comment_id}/replies \
  -f body="Acknowledged — skipping this as a style preference. Thanks for the suggestion!"
```

모든 코멘트 처리 완료 후 **checker agent 호출** (검증, 1회):
```
입력:
  check_dir: detect_env.py 결과의 첫 번째 앱 check_dir
  run_cmd:   run_cmd
  checks:    checks
```

검증 실패 시:
```
❌ 검증 미통과 — 루프를 중단합니다.
실패 검사: {검사명}
시도: {attempt}회
남은 에러:
{last_error}

잔여 에러 해결 후 /autopilot:check 또는 /autopilot:review-fix를 재실행하세요.
```
→ [STOP]

수정된 파일 없으면 → "적용할 수정사항이 없었습니다." [STOP]

---

### 5-3. 보고

```
## 수정 결과

### 적용 ({n}건)
| 파일 | 라인 | 심각도 | 변경 요약 |
|------|------|--------|----------|

### 스킵 ({n}건)
| 파일 | 라인 | 심각도 | 스킵 사유 |

### dismiss ({n}건)
| 파일 | 라인 | 심각도 | 사유 |
```

---

### 5-4. GATE-B: 커밋 확인

수정된 파일 없으면 → "적용할 수정사항이 없었습니다." [STOP]

```
[GATE-B] AskUserQuestion (PENDING):
"위 수정 결과를 확인하세요. 처리하시겠습니까?
1. 커밋 + push
2. 커밋만 (push 안 함)
3. 롤백 후 종료
"
```

| 응답 | 동작 | 다음 |
|------|------|------|
| "1" | 커밋 → push → +1 reaction | 5-5 → 폴링 루프 자동 진행 |
| "2" | 커밋만 | [STOP] |
| "3" | `cd '{worktree_path}' && git checkout -- {modified_files}` | [STOP] |

---

### 5-5. 커밋

```bash
cd '{worktree_path}' && git add {modified_files}
cd '{worktree_path}' && git commit -m "$(cat <<'EOF'
fix: apply CodeRabbit review feedback

{변경 요약 (bullet list, 심각도 포함)}

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

### 5-6. Push (GATE-B "1" 선택 시)

```bash
cd '{worktree_path}' && git push
```

실패 시:
```bash
cd '{worktree_path}' && git pull --rebase && git push
```

rebase 충돌 시: `git rebase --abort` 후 안내 → [STOP]

### 5-7. +1 reaction (push 성공 시만)

```bash
gh api repos/{owner_repo}/pulls/comments/{comment_id}/reactions \
  -f content="+1" --silent
```

실패 시 무시 (수정은 이미 push됨)

### 5-8. Push 후 폴링 루프 진입

push 성공 후:
1. `pushed_at` = 현재 시각 (ISO 8601, UTC)
2. `iteration_count++`
3. max_iterations(= 20) 초과 시 → [STOP]
4. **사용자에게 묻지 않고** 즉시 STEP 1으로 복귀
   [LOCK: 폴링 계속 여부, 다음 회차 진행 여부 등 어떤 확인도 금지]
