---
name: cruise-build
description: (명시적 커맨드 실행 전용) /cruise:build 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Build

plan.md의 미체크 요구사항을 구현하고, lint/type/test 검사와 요구사항 검증까지 한 스킬에서 수행한다.
직전 build 이후의 요청(추가·개정)은 **STEP 2.5 세미플랜**이 plan.md에 반영한 뒤 구현한다.
검증이 미구현으로 실패하면 인메모리로 재구현→재검증을 반복한다. **파일 산출물은 `summary.md` 하나만** 남긴다.

개정 절차의 단일 규약: `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/amend.md`

> **종료 규칙:** 어떤 STEP에서 종료하든 `{task_dir}/summary.md` 를 **덮어쓰기**(append 아님) 기록하고 [STOP]한다.
> `{task_dir}` = `context.py` 의 `task_path` 의 디렉토리 (리터럴 경로를 쓰지 않는다).
> - frontmatter 공통 5필드 + summary 전용 필드(검사 결과 흡수) 완비
> - `status`: completed | cancelled | failed (**cruise 생애주기 상태** — Jira 상태 아님)
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용
> - 검사·검증이 실패해도 summary.md는 **항상** 쓴다 (`check_result: fail` 로). 소비자(cruise:log·result)가 실패 사실을 봐야 하기 때문.
> - 종료 시 **상태 한 줄 + 산출물 링크**를 출력한다 (`summary.md` · 체크박스를 갱신했으면 `plan.md` 도)
> - 예외: 선행 조건(STEP 2) 미충족은 아직 요약할 변경이 없으므로 summary.md를 쓰지 않고 종료한다.

> **금지:**
> - 상태 한 줄 + 산출물 링크 외에 요약·다음 액션 추천·후속 작업 제안 일체 출력하지 않는다. 이 규칙은 **콘솔 출력**에 대한 것이며, STEP 8의 summary.md(파일 산출물) 작성과는 무관하다.
> - `as any` · `@ts-ignore` · 린트 비활성화 주석으로 검사 에러 우회
> - run_check.py 결과를 무시하고 직접 판단
> - 검사 레벨 Fix 3회 초과 시도 / 미구현 재구현 2회 초과 시도
> - 사용자가 명시적으로 요청하지 않은 어떤 액션도 수행하지 않는다
> - 다른 스킬을 자동으로 호출하지 않는다
> - `*.archive/` 디렉토리는 읽지 않는다 (사용자 참조 전용)
> - **요구사항·구현 방식의 변경을 plan.md 개정 없이 반영하지 않는다.** 대화에 그런 요청이 있으면
>   STEP 2.5에서 처리하거나, 세미플랜 범위를 넘으면 `/cruise:plan` 을 권한 뒤 [STOP]한다.
>   요구사항과 무관한 수정(오타·스타일·검사 에러)은 예외다.
> - **plan.md 본문을 수정하지 않는다.** build 가 만질 수 있는 것은 `## 요구사항` 체크박스와,
>   STEP 2.5 세미플랜이 amend 규약에 따라 선언한 부분뿐이다.

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

결과를 메모리에 보관: `root`, `branch`, `key`, `key_source`, `base_branch`, `base_source`, `repo`, `has_uncommitted`, `task_path`, `task_md_exists`, `plan_md_exists`, `summary_md_exists`.
`task_dir` = `task_path` 의 디렉토리. 이후 모든 산출물 경로는 `task_dir` 기준으로만 해석한다.

---

## STEP 2 — 선행 조건 확인

`task_md_exists == true && plan_md_exists == true` 이어야 한다.
둘 중 하나라도 false면 아직 요약할 변경이 없으므로 summary.md를 쓰지 않고 [STOP]한다.
콘솔에는 누락 파일과 함께 `/cruise:plan` 을 먼저 실행하라고 한 줄로 알린다 (기본 플랜 없이
세미플랜만으로 시작할 수는 없다).

---

## STEP 2.5 — 세미플랜 (직전 build 이후의 요청 반영)

`references/amend.md` 규약을 따른다. 목적은 **직전 build 이후에 들어온 추가·개정 요청을
plan.md에 적립한 뒤 그것만 구현**하는 것이다.

1. **경계 판정**(§1) — 인자 우선. 인자가 없으면 대화에서 마지막 `/cruise:build` 완료 출력 이후 발화.
   인자가 이슈 키 단독이면 확정 지시가 아니다.
2. **확정 지시만** 취한다. 질문·가정·탐색·미확정 비교는 제외하고 `### 미지수` 로 보낸다.
   판단이 애매하면 **막지 말고 진행**하고 `## 비고` 에 `plan 외 논의 있음` 을 남긴다.
3. 확정 지시가 없으면 STEP 3으로 바로 진행 (세미플랜 스킵).
4. **판별 4분기**(§2) → 국소 계획: 요구사항 문장 · 작업 항목 · `생성/수정 파일` · **검증 방법**.
   추가된 R 주변의 암묵 요구사항(엣지·빈/로딩·에러·접근성)도 함께 끌어낸다.
5. **범위 판정** — 기존 Phase에 붙이거나 Phase 1개 추가까지가 세미플랜의 범위다.
   Phase 구조 재편·순서 변경·전체 재분해·명세 변경이 필요하면 amend하지 않고 `[plan으로]` 를 제시한다(§6).
6. **게이트**(§4) — `add`·미지수만이면 게이트 없이 진행. `revise`·`withdraw` 가 포함되면 승인받는다.
   Plan Mode면 ExitPlanMode 로 대체한다.
7. 승인 후 plan.md를 **부분 수정**한다 (amend.md §3): 개정한 R은 체크 해제, 신규 ID는 최대+1,
   철회는 접미 표기, `## 개정 이력` 에 근거 인용 포함 한 줄 append.

> **Plan Mode:** 승인 전에는 읽기만 한다. 세미플랜 결과 + 구현할 미체크 R + 예상 변경 파일을
> ExitPlanMode 본문으로 제시하고, 승인 후 STEP 3~8을 진행한다.
> 승인 전 실행 금지: plan.md 쓰기 · `run_check.py --auto-fix` · 구현 편집.

---

## STEP 3 — plan.md 파싱 · 타깃 결정

plan.md에서 세 가지를 읽어 메모리에 보관한다.

- `## 요구사항` — R-ID 별 **체크 상태**. `- [ ]` = 미구현·미검증, `- [x]` = 검증 통과,
  `(철회: …)` 접미 = 대상 아님 (CONTRACT §4a)
- `## 구현 계획` — 각 Phase의 메타(`<!-- delegate: -->`)와 작업 항목(끝의 R-ID 표기), `생성/수정 파일`
- `## 검증 방법` — 표의 각 행(요구사항 R-ID · 검증 방법 · 도구/명령)

### 타깃 결정 (결정적 — LLM 판단 없음)

```
타깃 R = 미체크 R (철회 제외)
```

| 상태 | 동작 |
|------|------|
| 타깃 R 있음 | STEP 4 진행 |
| 타깃 R 없음 + `has_uncommitted == false` | `변경 없음 (요구사항 모두 처리됨). 추가·수정 요청이 있다면 /cruise:plan 또는 /cruise:build <요청> 으로 알려주세요.` 출력 후 [STOP] (summary.md 쓰지 않음) |
| 타깃 R 없음 + `has_uncommitted == true` | **구현하지 않고** STEP 5(검사)·STEP 6(검증)만 수행. `## 비고` 에 `plan 외 변경 포함` 한 줄 |

**구현 범위**도 여기서 파생된다 — 타깃 R을 참조하는 작업 항목과 그 Phase의 `생성/수정 파일` 목록이
1차 범위다. 그 밖으로 번지는 부분(호출부·역참조)은 STEP 4가 실제 파일을 읽고 결정한다.

---

## STEP 4 — 구현 루프 (타깃 R 단위)

STEP 3의 타깃 R을 충족하는 작업 항목만 구현한다. **체크된 R의 코드는 읽지 않는다** —
"이미 반영됐나" 를 매번 추론하지 않는 것이 이 설계의 핵심이다 (진척은 체크박스가 진실 원천).

타깃 R을 포함하는 Phase마다:

1. 그 Phase의 작업 항목 중 **타깃 R을 참조하는 것만** 골라낸다
2. **구현 실행** (delegate 규칙)
   - `yes` → `agents/cruise-builder.md` 에이전트에 위임
   - `no` → 메인에서 직접 처리
   - `auto` (기본) → 변경 파일 ≥5개 또는 신규 파일 포함 시 에이전트 위임, 아니면 메인 처리

게이트 없음. 사용자가 중단하고 싶으면 직접 중단.

진행 상태는 plan.md 체크박스가 들고 있다 (STEP 8에서 갱신). 다음 build 호출 시 미체크 R만
다시 타깃이 되므로 자연 idempotent 하다.

---

## STEP 5 — 검사 실행 (lint → type → test)

앱 환경을 탐지한다.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/detect_commands.py {root}
```

탐지 실패 시 `check_tools` 를 모두 `skipped` 로 두고 STEP 6으로 진행한다 (검사 불가는 요약에 남기되 스킬을 죽이지 않는다).

앱 디렉토리별로 순서대로 실행한다.

**lint:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/run_check.py \
  lint "{config.lint}" --cwd {check_dir} --auto-fix
```

**check-types:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/run_check.py \
  check-types "{config.check-types}" --cwd {check_dir}
```

**test:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/run_check.py \
  test "{config.test}" --cwd {check_dir}
```

각 도구의 pass/fail/skipped 를 메모리에 기록(`check_tools`).

### 검사 레벨 자동 Fix 루프 (최대 3회)

**카운터**: `fix_attempts` (0에서 시작)

1. 에러 분석: run_check.py 출력의 `errors` 배열과 해당 파일을 읽고 수정 적용
   - lint: `--auto-fix` 가 이미 실행됨. 잔여 에러를 파일 단위 수정
   - check-types / test: 에러 메시지 분석 후 파일 수정
2. `fix_attempts += 1`
3. 실패했던 단계부터 재실행
4. 모두 통과 → STEP 6
5. `fix_attempts >= 3` → 해당 도구를 `fail` 로 확정하고 STEP 6 진행 (`check_tools` 에 `fail` 기록. 에러 원문은 summary.md에 담지 않는다 — frontmatter 신호로 충분)

> **경계:** 이 Fix 루프는 **검사 레벨 에러(lint/type/test)** 전용이다. *기능 미구현*은 여기서 고치지 않는다 — STEP 6·7에서 처리한다.

---

## STEP 6 — 요구사항 검증 (plan.md `## 검증 방법` 집행)

### 검증 대상 (범위 축소)

전수 재실행은 비싸므로 아래로 한정한다. 그래도 회귀는 잡힌다 — 만진 파일이 깨뜨릴 수 있는 R은 모두 포함되므로.

```
검증 대상 = 타깃 R  ∪  { 이번에 만진 파일과 `생성/수정 파일` 이 겹치는 R }
```

- 겹침 판정은 plan.md의 파일 목록으로 하므로 **결정적**이다
- 철회된 R은 제외한다
- 같은 명령이 여러 R에 걸리면 **한 번만 실행**한다 (dedupe)

### 처리

- **자동 명령 항목** (`도구/명령` 에 실행 가능한 명령): 명령을 실행해 통과/실패 판정.
- **lint/type/test 로 덮이는 항목** (`도구/명령` 이 "check" 등): STEP 5 결과로 충족 처리 (재실행 불필요).
- **수동 항목** (`도구/명령` 이 "수동"): 코드·산출물 근거로 충족 여부를 **판단만** 한다. 자신 있게 확정 못 하면 `manual`(사용자 확인 필요)로 표시 — fail로 단정하지 않는다.

각 R-ID 결과(`pass` | `fail` | `manual`)와 **진단**(무엇이 왜 문제인지 — 기대 vs 실제, 실패 테스트·파일·라인, 누락 처리, **고칠 위치**)을 메모리에 보관한다. 진단은 STEP 4 재구현이 어디를 고칠지 알 수 있을 만큼 구체적으로 쓴다.

> **체크된 R이 fail이면** 그 R을 **재구현 타깃에 추가**한다 (회귀 감지 → 자기 치유).
> STEP 8에서 그 R의 체크를 `[ ]` 로 되돌린다.

---

## STEP 7 — 인메모리 재구현 루프

요구사항이 **기능 미구현**으로 `fail` 인 경우(검사 레벨 에러가 아니라):

**카운터**: `rebuild_attempts` (0에서 시작)

1. fail 판정된 R-ID 집합 + 진단이 지목한 파일을 **재구현 타깃**으로 메모리에 보관
   (직전에 `[x]` 였던 R도 포함 — 회귀).
2. STEP 4로 돌아가 타깃 R-ID를 재구현.
3. `rebuild_attempts += 1`
4. STEP 5(검사) → STEP 6(검증) 재실행.
5. 모든 요구사항 pass/manual → STEP 8.
6. `rebuild_attempts >= 2` → 남은 fail 을 `check_result: fail` 로 확정하고 STEP 8 진행.

파일에 피드백을 쓰지 않는다. 재구현 신호는 전부 메모리 안에서만 오간다.

---

## STEP 8 — 체크박스 갱신 · summary.md 작성

### 8a. plan.md 체크박스 갱신 (본문은 건드리지 않는다)

STEP 6 결과대로 `## 요구사항` 의 체크박스만 수정한다 (CONTRACT §4a — 체크박스는 build 소유).

| 결과 | 표기 |
|------|------|
| `pass` | `- [x] Rn: …` |
| `manual` | `- [x] Rn: … (수동확인)` |
| `fail` (재구현 한도 초과) | `- [ ] Rn: …` (미체크로 유지·복귀) |

체크박스 외의 어떤 줄도 수정하지 않는다.

### 8b. summary.md 작성 (유일 파일 산출물, 매번 덮어쓰기)

summary.md는 **브랜치 전체(base 대비)의 변경 요약** + **이번 검사·요구사항 검증 결과**를 담는 최신 스냅샷 1개다. 매 build마다 전체 덮어쓴다. `summary.archive/` 는 만들지 않는다 (v11).

변경 통계 수집 (base 분기점부터 커밋 + 미커밋 전체):

```bash
BASE=$(git merge-base {base_branch} HEAD)
git diff --stat "$BASE"          # 파일별 +/- 및 합계
git diff --name-status "$BASE"   # 파일별 변경 유형(A/M/D)
```

`base_source == unknown` 등으로 base_branch를 신뢰할 수 없으면 통계 수집을 생략하고 frontmatter 통계를 0으로 두며 `## 비고` 에 사유 한 줄을 남긴다.

`check_result` 도출:
- lint/type/test 가 모두 `pass`(또는 `skipped`)이고, 요구사항 검증에 `fail` 이 하나도 없으면 `pass`. 그 외 `fail`.
- `manual`(사용자 확인 필요) 항목만 남은 경우는 `pass` 로 두되 본문에 미확인으로 표시한다.

`{task_dir}/summary.md` 를 **항상 덮어쓰기** 저장한다.

frontmatter (공통 5필드 + summary 전용):

```yaml
---
summary: {task.md에서 상속}
branch: {branch}
repo: {repo}
status: completed          # completed | cancelled | failed (cruise 생애주기)
updated: {UTC ISO8601}
base_branch: {base_branch}
files_changed: {정수}
insertions: {정수}
deletions: {정수}
check_result: pass         # pass | fail
check_tools:
  lint: pass               # pass | fail | skipped
  type: pass
  test: pass
requirements_checked: {정수}   # 이번에 검증한 요구사항 수
fix_attempts: {정수}           # 검사 레벨 Fix 시도 횟수
---
```

본문 구조 — **사람이 30초 안에 "이 브랜치가 뭘 했나"를 파악하는 요약**이 목적이다. 검사 원문·전체 표 같은 기계·디버그 material은 담지 않는다.

- `# Summary — {KEY}` (H1)
- `## 개요` — 이 브랜치가 무엇을 달성했는지 산문 요약 (task.md summary + task.md `## 목표` 기반)
- `## 변경 파일` — 작업단위(도메인/모듈)별로 `### 그룹명` 서브헤딩을 붙이고, 그 아래 파일당 한 줄로 "무엇이 왜 바뀌었나" (name-status의 A/M/D 반영). 예:
  ```
  ### GA4 이벤트 큐 워커
  - workers/ga4-queue.ts (신규) — 큐 처리 워커 본체
  - lib/retry.ts (신규) — 실패 시 지수 백오프 재시도
  ```
- `## 구현 현황` — 요구사항 체크 상태 요약 (`R1~R6 완료 · R7 미해결 · R4 철회`)
- `## 검증` — **압축 요약만**. plan에 검증 방법이 없으면 "- 검증 방법 없음".
  - 검사 한 줄: `- 검사: lint PASS · type PASS · test PASS` (skipped 포함)
  - 요구사항 한 줄: `- 요구사항 6건 중 5 pass · 1 fail` (검증 안 했으면 생략)
  - **fail·manual 항목만** 한 줄씩 진단: `- R3 fail: 빈 목록 시 스피너 미제거 (List.tsx:42)`. pass 항목은 나열하지 않는다. 에러 원문은 담지 않는다.
- `## 비고` — `has_uncommitted == true` 면 "미커밋 변경 포함", `plan 외 변경 포함`, `plan 외 논의 있음`, base 통계 미수집 사유 등 (없으면 생략)

변경 통계 수치(files_changed 등)는 frontmatter에만 두고 본문에는 반복하지 않는다. summary.md는 누적하지 않고 매번 전체 재작성한다. 입력은 plan.md · git diff · 대화 컨텍스트·인자(STEP 2.5) · 이번 실행의 검사/검증 결과다.

---

## STEP 9 — 종료

**상태 한 줄 + 산출물 링크**를 출력하고 [STOP].

```
완료: 추가 R6 / 개정 R1
[summary.md](file://{task_dir}/summary.md) · [plan.md](file://{task_dir}/plan.md)
```

- 세미플랜이 없었으면 `완료` 만
- 반영하지 않은 항목이 있으면: `완료: 추가 R6 / 미반영 2건 (태블릿 열 수, 접근성)`
- 검사·검증 실패가 있으면: `완료 (검사 실패)` — 상세는 summary.md
- 체크박스를 갱신하지 않았으면 `plan.md` 링크는 생략
- 경로는 `~` 가 아니라 **절대경로**로 낸다
