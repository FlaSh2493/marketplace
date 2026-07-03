---
name: cruise-check
description: (명시적 커맨드 실행 전용) /cruise:check 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Check

> **종료 규칙:** 어떤 STEP에서 종료하든 Write 도구로
> `~/Documents/tasks/{KEY}/check.md` 를 기록하고 [STOP]한다.
> - frontmatter 공통 9필드 + 스킬별 필드 완비
> - `status`: completed | cancelled | failed
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용

> **금지:**
> - `as any` · `@ts-ignore` · 린트 비활성화 주석으로 에러 우회
> - run_check.py 결과 무시하고 직접 판단
> - Fix 3회 초과 시도
> - 산출물 작성 후 요약·다음 액션 추천 일체 출력하지 않는다 ("완료" 한 줄만)
> - 다른 스킬을 자동으로 호출하지 않는다

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

결과를 메모리에 보관: `root`, `branch`, `key`, `task_md_exists`, `plan_md_exists`, `build_md_exists`, `check_md_exists`.

---

## STEP 2 — 앱 환경 탐지

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/detect_commands.py {root}
```

앱 디렉토리별 lint/check-types/test 명령어 목록 확보.
탐지 실패 시 check.md에 `status: failed` 기록 후 [STOP].

---

## STEP 3 — 순차 실행 (lint → type → test)

각 앱 디렉토리에서 순서대로 실행한다.

**lint:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/run_check.py \
  lint "{config.lint}" --cwd {check_dir} --auto-fix
```

**check-types:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/run_check.py \
  check-types "{config.check-types}" --cwd {check_dir}
```

**test:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/run_check.py \
  test "{config.test}" --cwd {check_dir}
```

모든 단계 통과 → STEP 5.
실패 → STEP 4.

---

## STEP 4 — 자동 Fix 루프 (최대 3회)

**카운터**: fix_attempts (0에서 시작)

1. 에러 분석: run_check.py 출력의 `errors` 배열과 해당 파일을 읽고 수정 적용
   - lint: `--auto-fix` 가 이미 실행됨. 잔여 에러를 파일 단위 수정
   - check-types / test: 에러 메시지 분석 후 파일 수정
2. fix_attempts += 1
3. 실패했던 단계부터 재실행
4. 통과 → STEP 5
5. fix_attempts >= 3 → check.md에 `status: failed` 기록 후 [STOP]

---

## STEP 4.5 — 요구사항 검증 (plan.md `## 검증 방법` 집행)

`plan_md_exists == false` 면 이 STEP을 건너뛴다 (요구사항 검증 없이 STEP 5).

`plan_md_exists == true` 면 plan.md의 `## 검증 방법` 표를 읽어 각 행(요구사항 R-ID · 검증 방법 · 도구/명령)을 처리한다:

- **자동 명령 항목** (`도구/명령` 에 실행 가능한 명령이 있음): 해당 명령을 실행해 통과/실패 판정.
- **lint/type/test 로 덮이는 항목** (`도구/명령` 이 "check 스킬" 등): STEP 3 결과로 충족 처리 (재실행 불필요).
- **수동 항목** (`도구/명령` 이 "수동"): 코드·산출물을 근거로 충족 여부를 **판단만** 한다. 자신 있게 확정 못 하면 `manual`(사용자 확인 필요)로 표시 — fail로 단정하지 않는다.

> **경계 — check는 구현하지 않는다.** 요구사항이 *기능 미구현*으로 실패하면 그것은 build의 몫이다.
> 해당 R-ID를 `fail`로 기록하고 STEP 5(check.md)·STEP 5.5(build.md 피드백)로 넘긴다.
> STEP 4 Fix 루프는 **검사 레벨 에러(lint/type/test)** 전용이며, 미구현 기능을 여기서 구현하지 않는다.

각 R-ID 결과(`pass` | `fail` | `manual`)와 **진단**(무엇이 왜 문제인지 — 기대 vs 실제, 실패 테스트·파일·라인, 누락 처리)을 메모리에 보관해 STEP 5에 기록한다.

---

## STEP 5 — check.md 저장

frontmatter (공통 9필드 + 스킬별):
```yaml
---
key: {KEY}
key_source: {key_source}
skill: check
summary: {task_md_exists == true 면 task.md 에서 상속, 아니면 ""}
branch: {branch}
repo: {repo}
status: completed  # 또는 failed
created: {UTC ISO8601}
updated: {UTC ISO8601}
tags: []
result: pass  # 또는 fail
tools:
  lint: pass    # pass | fail | skipped
  type: pass
  test: pass
fix_attempts: 0
requirements_checked: 0   # plan.md 검증 방법에서 처리한 요구사항 수 (plan 없으면 0)
---
```

> **check.md 역할 — 최신 검증 스냅샷 (이력 로그 아님).** "지금 이 코드가 통과하는가 + 최신 진단"을 담는다.
> 매 check마다 **덮어쓰기**하며 append/archive하지 않는다 (스냅샷은 최신 1개면 충분). 회차별 이력은
> build.md `## Check Feedback`(append)이 맡는다.

- `result`: lint/type/test 가 모두 pass 이고, 요구사항 검증에 `fail` 이 하나도 없으면 `pass`. 그 외 `fail`.
  `manual`(사용자 확인 필요) 항목만 남은 경우는 `result: pass` 로 두되 본문에 미확인으로 표시한다.

본문:
- `# Check — {KEY}` (H1)
- `## 결과` — 각 도구별 통과/실패 요약
- `## 요구사항 검증` — plan.md 기반 (plan 없으면 "- plan.md 없음 — 건너뜀"). 표: `| 요구사항 | 검증 방법 | 결과 | 진단 |`.
  - **검증 방법**: 실제로 무엇을 실행/확인했는지(명령·절차).
  - **결과**: `pass` | `fail` | `manual`.
  - **진단** (`fail`/`manual` 행 필수): 무엇이 왜 문제인지 구체적으로 — 기대 vs 실제, 실패 테스트·파일·라인, 누락 처리. build가 어디를 고칠지 알 수 있을 만큼 구체적으로. (`fail` 행은 "구현 필요 → `/cruise:build`" 명시)
- `## 에러 (실패 시)` — lint/type/test 미해결 에러 원문 목록

`result == pass` 면 여기서 "완료" 한 줄 출력 후 [STOP]. `result == fail` 이면 STEP 5.5 진행.

---

## STEP 5.5 — 실패 시 build.md에 피드백 기록

`result == fail` 이고 `build_md_exists == true` 인 경우에만 수행한다.
(`build_md_exists == false` — 아직 build를 안 했으면, 기록 대상이 없으므로 생략하고 그냥 [STOP].)

build.md **끝에** `## Check Feedback {ts}` 섹션을 **append** 한다. `{ts}` 는 UTC ISO8601.
기존 `## Run` 섹션이나 이전 피드백은 **절대 수정하지 않는다** (append-only).

```markdown
## Check Feedback {ts}
- result: fail
- 미해결 요구사항: R3, R5
  - R3: {핵심 진단 한 줄 + 고칠 위치, 예: 빈 목록 시 스피너 미제거 `List.tsx:42`} → 구현 필요
  - R5: {…}
- 미해결 검사 에러(참고): {lint/type/test 중 fix 루프로 못 푼 것, 파일 경로} (없으면 생략)
- 상세 진단: check.md `## 요구사항 검증` 참조
```

- 내용은 check.md `## 요구사항 검증`의 진단을 **발췌·요약**한 것이다 (진단 원본은 check.md). build가 한 줄로 어디를 고칠지 알 정도로만 적는다.
- 이 섹션은 **build가 읽는 인박스**다. build는 가장 최근 `## Run` 보다 뒤에 있는 `## Check Feedback` 을 "미소비 피드백"으로 보고 해당 R-ID를 강제 재구현한다.

"완료" 한 줄 출력 후 [STOP].
