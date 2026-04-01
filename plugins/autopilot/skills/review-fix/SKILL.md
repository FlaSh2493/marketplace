---
name: autopilot-review-fix
description: PR의 CodeRabbit 리뷰 코멘트를 루프 방식으로 자동 반영. 새 리뷰가 달릴 때마다 물어보고 수정한다. "리뷰 반영", "코드래빗 수정", "review fix" 등을 요청할 때 사용한다.
---

# CodeRabbit 리뷰 자동 반영 (loop)

## 사용법
`/autopilot:review-fix`

호출하면 loop을 시작합니다. 활성 리뷰가 있을 때마다 물어보고, 사용자 선택에 따라 수정 후 루프 계속 여부를 결정합니다. 활성 리뷰가 없으면 자동 종료.

---

## 전체 흐름

```
[LOOP START] iteration_count = 1, max_iterations = 10

STEP 1: 컨텍스트 확보 (worktree_path, branch, PR)
  └─ 실패 → [STOP]

STEP 2: 리뷰 코멘트 수집 + 필터링
  └─ 활성 0건 → [AUTO STOP] ("새 리뷰 없음. 루프 자동 종료.")
  └─ 활성 1건+ → STEP 3

STEP 3: 원문 표시 ("[루프 N회차]" 헤더)

[GATE-A] 적용 여부 확인 (PENDING)
  └─ "1"~"2" → 수정 실행
  └─ "3" → [STOP]

STEP 5: 수정 → 검증 → 보고
  └─ 검증 실패 → [STOP]
  └─ 수정 파일 없음 → [STOP]

[GATE-B] 커밋 확인 (PENDING)
  └─ "1" → 커밋 + push → +1 reaction → [GATE-C]
  └─ "2" → 커밋만 → [STOP]
  └─ "3" → 롤백 → [STOP]

[GATE-C] 루프 계속 여부 (NEW, PENDING)
  └─ "1" → iteration_count++ → max 초과 체크 → STEP 1로 복귀
  └─ "2" → [STOP]
```

---

## STEP 1: 컨텍스트 확보

```bash
git rev-parse --show-toplevel → worktree_path   # 실패 → [STOP]
git rev-parse --abbrev-ref HEAD → current_branch # HEAD → [STOP], develop|main → [STOP]
gh auth status 2>&1                              # 실패 → "gh 인증이 필요합니다." [STOP]
gh api user -q '.login' → my_login
gh repo view --json nameWithOwner -q '.nameWithOwner' → owner_repo
gh pr list --head '{current_branch}' --state open --json number -q '.[0].number // empty' → pr_number
# 비어있으면 → "열린 PR이 없습니다." [STOP]
```

**이후 모든 Bash 명령은 `cd '{worktree_path}' && command` 형태로 실행한다.**

## STEP 2: 리뷰 코멘트 수집

### 2-1. 전체 코멘트 1회 수집 (reactions 포함)

```bash
gh api repos/{owner_repo}/pulls/{pr_number}/comments \
  --paginate \
  --jq '[.[] | select(.user.login == "coderabbitai[bot]") | {
    id: .id,
    path: .path,
    line: (.line // .original_line),
    side: (.side // "RIGHT"),
    body: .body,
    in_reply_to_id: .in_reply_to_id,
    created_at: .created_at,
    diff_hunk: .diff_hunk,
    resolved: ((.reactions // {})."+1" // 0) > 0
  }]'
```

### 2-2. 필터링

수집 결과를 아래 기준으로 분류한다:

| 분류 | 조건 | 처리 |
|------|------|------|
| **처리 완료** | `resolved == true` (+1 reaction 존재) | 제외 |
| **outdated** | `cd '{worktree_path}' && git ls-files --error-unmatch '{path}'` 실패 (파일 미존재) | 제외 |
| **스레드 최초 코멘트** | `in_reply_to_id == null` | **수정 대상** |
| **스레드 후속 코멘트** | `in_reply_to_id != null` | 해당 스레드 최초 코멘트의 **보충 맥락**으로 합산 |

스레드 합산: 동일 `in_reply_to_id`를 가진 후속 코멘트의 body를 최초 코멘트에 `\n---\n` 구분자로 이어붙여 하나의 지시로 취급한다.

### 2-3. Review body — 맥락 참고용

```bash
gh api repos/{owner_repo}/pulls/{pr_number}/reviews \
  --jq '[.[] | select(.user.login == "coderabbitai[bot]" and .state == "CHANGES_REQUESTED") | {id: .id, body: .body}]'
```

- review body는 **수정 대상이 아닌 맥락 참고용**으로만 사용
- Walkthrough, Summary 섹션은 코드 수정 지시가 아님

### 2-4. 수집 결과 검증

- 활성 코멘트 0건:
  - **1회차 (iteration_count == 1)**: "활성 CodeRabbit 리뷰가 없습니다." → `[STOP]`
  - **N회차 (iteration_count > 1)**: "새 활성 리뷰가 없습니다. 루프 자동 종료. (push 후 CodeRabbit 리뷰가 생기면 /autopilot:review-fix를 다시 실행하세요)" → `[STOP]`
- gh api 실패: 에러 메시지 출력 → `[STOP]`

## STEP 3: 원문 표시

### 3-0. 루프 회차 헤더 표시

```
[루프 {iteration_count}회차] 새 리뷰 확인 중...
```

### 3-1. 심각도 분류

| 심각도 | 기준 | 표시 |
|--------|------|------|
| **critical** | 버그, 보안 취약점, 데이터 손실 가능성 | `[!]` |
| **important** | 로직 오류, 성능 문제, 타입 불일치 | `[*]` |
| **suggestion** | 리팩토링, 네이밍, 코드 스타일 개선 | `[~]` |
| **nitpick** | 포맷팅, 사소한 선호도 차이 | `[.]` |

### 3-2. 원문 표시

critical → important → suggestion → nitpick 순으로, 각 코멘트를 원문 그대로 표시한다:

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

| 응답 | 처리 |
|------|------|
| "1" | 전체 수정 (nitpick dismiss) |
| "2" | 코멘트별 선택 모드 (아래) |
| "3" | `[STOP]` |

### nitpick/스킵 대상 dismiss

수정하지 않는 코멘트에는 PR 코멘트로 답글을 달아 CodeRabbit에게 resolve 시그널을 보낸다:

```bash
gh api repos/{owner_repo}/pulls/{pr_number}/comments/{comment_id}/replies \
  -f body="Acknowledged — skipping this as a style preference. Thanks for the suggestion!"
```

### 코멘트별 선택 모드 ("2" 선택 시)

각 코멘트를 critical → important → suggestion → nitpick 순으로:

```
[{심각도}] {파일명}:{line}
━━━━━━━━━━━━━━━━━━━━━━━━━━
{코멘트 body 원문}
━━━━━━━━━━━━━━━━━━━━━━━━━━
→ 적용 / 스킵 / 중단?
```

## STEP 5: 수정 → 검증 → 커밋 → push

### 5-1. 수정 원칙

- 코멘트가 가리키는 파일을 Read로 읽고 Edit으로 **최소 범위만** 수정
- suggestion 블록(` ```suggestion `)이 있으면:
  - 블록 안의 코드가 해당 `line` 범위의 대체 코드임
  - 원본 diff_hunk에서 해당 라인을 찾아 suggestion 코드로 교체
  - 주변 코드와의 일관성(import, 변수명 등) 확인
- **동일 파일 다중 코멘트**: 파일별로 코멘트를 모아 라인 역순(아래→위)으로 수정하여 라인 번호 밀림 방지
- **코멘트 간 수정 범위 충돌 시**: 심각도 높은 쪽 우선 적용, 충돌하는 낮은 쪽은 스킵
- 판단이 애매한 코멘트 → 수정하지 않고 스킵 목록에 사유와 함께 표시
- 경로: Read/Edit/Glob/Grep은 `{worktree_path}/파일경로` 절대경로, Bash는 `cd '{worktree_path}' && command`

### 5-2. 검증 (lint → type-check → test 루프)

수정 완료 후, `/autopilot:check`와 동일한 순차 검증 루프를 실행한다.

#### 5-2-1. 환경 탐지

`{worktree_path}`에서 `package.json` 탐색 → 패키지 매니저 판별 → run_cmd 확보.
`package.json`의 scripts에서 검사 명령어 매핑:

| 검사 | 후보 스크립트명 (우선순위순) |
|------|----------------------------|
| lint | `lint`, `eslint` |
| check-types | `check-types`, `type-check`, `typecheck`, `tsc` |
| test | `test`, `jest`, `vitest` |

`node_modules`가 없으면 install 실행. 3개 모두 스킵이면 검증 단계 자체를 스킵.

#### 5-2-2. 순차 실행 + 자동 수정 루프

검사 순서: **lint → check-types → test**

각 검사에 대해:

1. **실행**: `cd '{worktree_path}' && {run_cmd} {script} 2>&1` (timeout 300초)
2. **통과** (exit 0) → 다음 검사로
3. **실패** → 자동 수정 루프 (최대 3회):
   - 에러 출력에서 `파일경로:라인번호` 파싱 → 파일 Read → 수정 → 재실행
   - lint: eslint면 `--fix`, biome이면 `--fix` 시도 후 나머지 직접 Edit
   - check-types: TS 에러 메시지 기반 코드 수정
   - test: expect/actual 비교 → **구현 코드 수정** (테스트는 스펙)
   - 파싱 불가 (환경 에러 등): 자동 수정 불가 → 실패 확정
4. **3회 실패** → 해당 검사 실패 확정

**선행 검사 재검증**: 다음 검사로 넘어가기 전, 직전 검사에서 코드 수정이 있었으면 이미 통과한 검사를 순서대로 재실행. 재검증은 전체에서 최대 1회.

**검사 실패 시**: 같은 프로젝트의 이후 검사는 실행하지 않는다.

#### 5-2-3. 검증 실패 시

검사 실패가 남은 채로 루프가 종료되면, 남은 에러를 보고하고 `[STOP]`. 롤백하지 않는다 — 수정 자체는 리뷰 반영이므로 유지하고, 사용자가 잔여 에러를 직접 해결한다. **루프는 즉시 종료된다** (GATE-C 없음).

```
❌ 검증 미통과 — 루프를 중단합니다.
실패 검사: {검사명}
시도: {attempt}회
남은 에러:
{마지막 에러 출력}

잔여 에러 해결 후 /autopilot:check 또는 /autopilot:review-fix를 재실행하세요.
```

### 5-3. 보고

```
## 수정 결과

### 적용 ({n}건)
| 파일 | 라인 | 심각도 | 변경 요약 |
|------|------|--------|----------|
| {파일} | {line} | {심각도} | {1줄 요약} |

### 스킵 ({n}건)
| 파일 | 라인 | 심각도 | 스킵 사유 |
|------|------|--------|----------|
| {파일} | {line} | {심각도} | {사유} |

### dismiss ({n}건)
| 파일 | 라인 | 심각도 | 사유 |
|------|------|--------|------|
| {파일} | {line} | {심각도} | nitpick/사용자 스킵 |
```

### 5-4. 커밋 확인 → GATE-B

수정된 파일이 없으면 → "적용할 수정사항이 없었습니다." `[STOP]`

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
| "1" | 커밋 → push → +1 reaction | GATE-C |
| "2" | 커밋 (반응 없음) | `[STOP]` |
| "3" | `cd '{worktree_path}' && git checkout -- {modified_files}` | `[STOP]` |

**참고 (응답 "2" 선택 시):**
push가 없으므로 +1 reaction은 추가되지 않습니다. 다음 루프 회차에서 동일 리뷰가 다시 나타날 수 있습니다. push를 완료한 후 /autopilot:review-fix를 재실행하는 것을 권장합니다.

### 5-5. 커밋

```bash
cd '{worktree_path}' && git add {modified_files}
cd '{worktree_path}' && git commit -m "$(cat <<'EOF'
fix: apply CodeRabbit review feedback

{변경 요약 (bullet list, 심각도 포함)}

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

### 5-6. Push (GATE-B 응답 "1" 선택 시)

```bash
cd '{worktree_path}' && git push
```

**push 실패 시:**

```bash
cd '{worktree_path}' && git pull --rebase && git push
```

- rebase 충돌 시: `cd '{worktree_path}' && git rebase --abort` 후 안내
  ```
  "push 실패: remote에 충돌하는 변경이 있습니다.
  1. /autopilot:merge로 머지 후 재시도
  2. 수동으로 해결
  "
  ```
  **루프: 충돌 시 GATE-C 없이 즉시 [STOP]**
- 기타 실패: 에러 메시지 출력 → `[STOP]` (루프 종료, +1 reaction 없음)

### 5-7. 처리 완료 표시 (+1 reaction)

GATE-B 선택에 따라:
- "1" (커밋 + push) 성공 시: `+1` reaction 추가
- "2" (커밋만) 선택 시: `+1` reaction 추가하지 않음 (push 미완료)
- "3" (롤백) 선택 시: `+1` reaction 추가하지 않음

**+1 reaction 추가 (push 성공 시만):**

```bash
gh api repos/{owner_repo}/pulls/comments/{comment_id}/reactions \
  -f content="+1" --silent
```

- reaction 추가 실패 시 무시 (수정 자체는 이미 push됨)
- push 실패 시에는 reaction을 추가하지 않는다 — 다음 실행 시 해당 코멘트를 다시 처리하기 위함

### 5-8. 완료 후 GATE-C로 진행

수정 + 커밋(+push) 완료 후, **GATE-C로 진행** (루프 계속 여부 확인).
GATE-C는 push 성공 후에만 도달한다. 건너뛰기/종료 선택 시에는 GATE-C 없이 즉시 [STOP].

---

## STEP 6 → GATE-C: 루프 계속 여부 (NEW)

```
[GATE-C] AskUserQuestion (PENDING — 루프 대기):
"완료. 계속하시겠습니까?
1. 루프 계속 — STEP 1로 돌아가 새 리뷰 확인 (지금 바로)
2. 종료
"
```

| 응답 | 동작 |
|------|------|
| "1" | `iteration_count++` → max 초과 체크 → STEP 1로 복귀 |
| "2" | `[STOP]` |

### 6-1. 루프 상태 업데이트

GATE-C "1" 선택 시:

```
iteration_count = iteration_count + 1
if iteration_count > max_iterations (= 10):
  "[STOP] 루프 {max_iterations}회 초과. 무한 루프 방지를 위해 자동 종료합니다. 반복되는 리뷰가 있다면 수동 확인을 권장합니다."
else:
  → STEP 1로 복귀 ("$[루프 {iteration_count}회차] 리뷰 확인 중..." 헤더 표시)
```

### 6-2. 무한 루프 안전장치

`max_iterations = 10`으로 설정. iteration_count > 10이면 경고 후 [STOP].

```
⚠️ 루프 10회 초과. 무한 루프 방지를 위해 자동 종료합니다.
반복되는 리뷰가 있다면 /autopilot:review-fix를 수동 확인 후 재실행하세요.
```
