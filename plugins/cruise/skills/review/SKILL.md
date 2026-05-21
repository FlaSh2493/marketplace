---
name: cruise-review
description: (명시적 커맨드 실행 전용) /cruise:review 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Review

> **종료 규칙:** 어떤 STEP에서 종료하든 Write 도구로
> `~/Documents/tasks/{KEY}/review.md` 를 기록하고 [STOP]한다.
> - 신규: 새 파일 생성. 재호출: `iterations[]` 에 append.
> - frontmatter 공통 10필드 + 스킬별 필드 완비
> - `status`: completed | cancelled | failed
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용

> **절대 금지:**
> - force-push / `pull --rebase`
> - 산출물 작성 후 요약·다음 액션 추천 일체 출력하지 않는다 ("완료" 한 줄만)
> - 다른 스킬을 자동으로 호출하지 않는다

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

`has_pr` 가 false면:
- status=failed 로 review.md 기록 ("PR이 없습니다.")
- [STOP]

---

## STEP 2 — 리뷰 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/fetch_reviews.py \
  {repo} {pr_number} {root}
```

결과: `has_reviews`, `active_count`, `is_in_progress`, `comments[]`

---

## STEP 3 — 폴링 결정

- `active_count >= 1` → STEP 4
- 리뷰 완료 + `active_count == 0` + `!is_in_progress` → status=completed 로 review.md 기록 후 [STOP]
- 그 외 (없음 / 진행 중 / 응답 대기):
  - sleep 30~60초
  - **안전망**: 30분 초과 또는 5회 초과 → status=cancelled 로 review.md 기록 ("타임아웃") 후 [STOP]
  - STEP 2 복귀

---

## STEP 4 — [GATE] 처리 방식 선택

`AskUserQuestion`: "리뷰 코멘트 {active_count}건을 어떻게 처리할까요?"

1. **전체 적용** → STEP 5
2. **코멘트별 선택** → severity 순으로 각 코멘트 표시 → 적용/건너뜀 선택 → STEP 5
3. **종료** → status=cancelled 로 review.md 기록 후 [STOP]

---

## STEP 5 — 코드 수정

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/detect_env.py {root}
```

환경 정보 확보 후 `agents/cruise-reviewer.md` 에이전트에 위임:
- 입력: 처리할 comments[], 환경 정보, 컨텍스트 요약
- 결과: 수정된 파일 목록

---

## STEP 6 — 검증

check 스킬과 동일한 로직으로 lint → type → test 실행:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/detect_commands.py {root}
# 각 도구 run_check.py 실행
```

실패 시 `AskUserQuestion`:
1. **재수정** → STEP 5 복귀
2. **종료** → status=failed 로 review.md 기록 후 [STOP]

---

## STEP 7 — [GATE] 커밋·Push 방식

`AskUserQuestion`: "수정된 파일을 어떻게 처리할까요?"

1. **커밋 + Push**:
   ```bash
   git add -A
   git commit -m "review: address CodeRabbit feedback"
   git push
   ```
   - non-ff 실패 시: status=failed 로 review.md 기록 후 [STOP] (force 사용 안 함)
   - 성공 시: `add_reactions.py` 로 처리한 코멘트에 +1 반응 추가
2. **커밋만**: `git add -A && git commit -m "..."` 후 [STOP]
3. **롤백**: `git checkout -- .` 후 status=cancelled 로 review.md 기록 후 [STOP]

---

## STEP 8 — review.md 저장

기존 review.md 가 있으면 `iterations[]` 에 append. 없으면 신규 생성.

frontmatter (공통 10필드 + 스킬별):
```yaml
---
key: {KEY}
key_source: {key_source}
skill: review
summary: {task.md에서 상속, 없으면 ""}
branch: {branch}
repo: {repo}
head_sha: {git rev-parse --short HEAD}
status: completed
created: {최초 생성 UTC, 재호출 시 유지}
updated: {UTC ISO8601}
tags: []
pr_number: {n}
iterations:
  - n: 1
    at: {UTC ISO8601}
    reviews_processed: {n}
    validation: pass
    pushed_sha: {sha or ""}
---
```

본문:
- `# Review — {KEY}` (H1)
- `## 이터레이션 이력` — iterations 테이블

STEP 9 복귀 (다음 iteration).
