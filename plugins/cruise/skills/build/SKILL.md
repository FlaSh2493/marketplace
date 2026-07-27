---
name: cruise-build
description: (명시적 커맨드 실행 전용) /cruise:build 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Build

plan.md의 Phase를 구현하고, lint/type/test 검사와 요구사항 검증까지 한 스킬에서 수행한다.
검증이 미구현으로 실패하면 인메모리로 재구현→재검증을 반복한다. **파일 산출물은 `summary.md` 하나만** 남긴다.

> **종료 규칙:** 어떤 STEP에서 종료하든 Write 도구로 `~/Documents/tasks/{KEY}/summary.md` 를
> **덮어쓰기**(append 아님) 기록하고 [STOP]한다.
> - frontmatter 공통 9필드 + summary 전용 필드(검사 결과 흡수) 완비
> - `status`: completed | cancelled | failed (**cruise 생애주기 상태** — Jira 상태 아님)
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용
> - 검사·검증이 실패해도 summary.md는 **항상** 쓴다 (`check_result: fail` 로). 소비자(jsync:log·result)가 실패 사실을 봐야 하기 때문.
> - 예외: 선행 조건(STEP 2) 미충족은 아직 요약할 변경이 없으므로 summary.md를 쓰지 않고 종료한다.

> **금지:**
> - 산출물 작성 후 요약·다음 액션 추천·후속 작업 제안 일체 출력하지 않는다 ("완료" 한 줄만). 이 규칙은 **콘솔 출력**에 대한 것이며, STEP 8의 summary.md(파일 산출물) 작성과는 무관하다.
> - `as any` · `@ts-ignore` · 린트 비활성화 주석으로 검사 에러 우회
> - run_check.py 결과를 무시하고 직접 판단
> - 검사 레벨 Fix 3회 초과 시도 / 미구현 재구현 2회 초과 시도
> - 사용자가 명시적으로 요청하지 않은 어떤 액션도 수행하지 않는다
> - 다른 스킬을 자동으로 호출하지 않는다
> - `*.archive/` 디렉토리는 읽지 않는다 (사용자 참조 전용)

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

결과를 메모리에 보관: `root`, `branch`, `key`, `key_source`, `base_branch`, `base_source`, `repo`, `has_uncommitted`, `task_path`, `task_md_exists`, `plan_md_exists`, `summary_md_exists`.

---

## STEP 2 — 선행 조건 확인

`task_md_exists == true && plan_md_exists == true` 이어야 한다.
둘 중 하나라도 false면 아직 요약할 변경이 없으므로 summary.md를 쓰지 않고, 콘솔에 누락 파일(어떤 boolean이 false인지)만 한 줄로 알리고 [STOP].

---

## STEP 3 — plan.md 파싱 (구현 계획 + 검증 방법)

plan.md에서 두 섹션을 읽어 메모리에 보관한다.

- `## 구현 계획` — 각 Phase의 메타(`<!-- delegate: -->`)와 본문(요구 상태, 작업 내용, 작업 항목의 요구사항 R-ID 표기).
- `## 검증 방법` — 표의 각 행(요구사항 R-ID · 검증 방법 · 도구/명령). STEP 6 요구사항 검증에서 집행한다.

---

## STEP 4 — Phase 단위 구현 루프

각 Phase 처리 순서:

1. **코드 반영 여부 판단**
   - Phase 명세가 요구하는 상태가 현재 코드에 이미 반영되어 있는지 LLM이 판단 (필요 시 관련 파일 Read/Grep).
   - **재구현 타깃 우선 (STEP 7 재진입 시)**: 이 Phase의 작업 항목이 **재구현 타깃 R-ID**(직전 검증에서 미구현으로 fail 판정된 R-ID)를 충족하거나 타깃 파일을 건드리면, "이미 반영됨"으로 skip하지 말고 **강제로 재구현/수정** 대상으로 삼는다.
   - 결과:
     - (타깃 아님) 이미 반영됨 → skip, 다음 Phase
     - (타깃) 강제 재구현 → 2단계 진행
     - 미반영 → 2단계 진행

2. **구현 실행** (delegate 규칙)
   - `yes` → `agents/cruise-builder.md` 에이전트에 위임
   - `no` → 메인에서 직접 처리
   - `auto` (기본) → 변경 파일 ≥5개 또는 신규 파일 포함 시 에이전트 위임, 아니면 메인 처리

게이트 없음. 사용자가 중단하고 싶으면 직접 중단.

진행 상태는 파일에 저장하지 않는다. 다음 build 호출 시 동일한 "코드 반영 여부 판단"으로 자연 idempotent 동작.

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

STEP 3에서 읽은 `## 검증 방법` 표의 각 행을 처리한다.

- **자동 명령 항목** (`도구/명령` 에 실행 가능한 명령): 명령을 실행해 통과/실패 판정.
- **lint/type/test 로 덮이는 항목** (`도구/명령` 이 "check" 등): STEP 5 결과로 충족 처리 (재실행 불필요).
- **수동 항목** (`도구/명령` 이 "수동"): 코드·산출물 근거로 충족 여부를 **판단만** 한다. 자신 있게 확정 못 하면 `manual`(사용자 확인 필요)로 표시 — fail로 단정하지 않는다.

각 R-ID 결과(`pass` | `fail` | `manual`)와 **진단**(무엇이 왜 문제인지 — 기대 vs 실제, 실패 테스트·파일·라인, 누락 처리, **고칠 위치**)을 메모리에 보관한다. 진단은 STEP 4 재구현이 어디를 고칠지 알 수 있을 만큼 구체적으로 쓴다.

---

## STEP 7 — 인메모리 재구현 루프

요구사항이 **기능 미구현**으로 `fail` 인 경우(검사 레벨 에러가 아니라):

**카운터**: `rebuild_attempts` (0에서 시작)

1. fail 판정된 R-ID 집합 + 진단이 지목한 파일을 **재구현 타깃**으로 메모리에 보관.
2. STEP 4로 돌아가 타깃 R-ID를 강제 재구현.
3. `rebuild_attempts += 1`
4. STEP 5(검사) → STEP 6(검증) 재실행.
5. 모든 요구사항 pass/manual → STEP 8.
6. `rebuild_attempts >= 2` → 남은 fail 을 `check_result: fail` 로 확정하고 STEP 8 진행.

파일에 피드백을 쓰지 않는다. 재구현 신호는 전부 메모리 안에서만 오간다.

---

## STEP 8 — summary.md 작성 (유일 산출물, 매번 덮어쓰기)

summary.md는 **브랜치 전체(base 대비)의 변경 요약** + **이번 검사·요구사항 검증 결과**를 담는 최신 스냅샷 1개다. 매 build마다 전체 덮어쓴다.

변경 통계 수집 (base 분기점부터 커밋 + 미커밋 전체):

```bash
TASK_DIR=~/Documents/tasks/{KEY}
BASE=$(git merge-base {base_branch} HEAD)
git diff --stat "$BASE"          # 파일별 +/- 및 합계
git diff --name-status "$BASE"   # 파일별 변경 유형(A/M/D)
```

`base_source == unknown` 등으로 base_branch를 신뢰할 수 없으면 통계 수집을 생략하고 frontmatter 통계를 0으로 두며 `## 비고` 에 사유 한 줄을 남긴다.

`check_result` 도출:
- lint/type/test 가 모두 `pass`(또는 `skipped`)이고, 요구사항 검증에 `fail` 이 하나도 없으면 `pass`. 그 외 `fail`.
- `manual`(사용자 확인 필요) 항목만 남은 경우는 `pass` 로 두되 본문에 미확인으로 표시한다.

Write 도구로 `~/Documents/tasks/{KEY}/summary.md` 를 **항상 덮어쓰기** 저장한다.

frontmatter (공통 9필드 + summary 전용):

```yaml
---
key: {KEY}
key_source: {key_source}
skill: summary
summary: {task.md에서 상속}
branch: {branch}
repo: {repo}
status: completed          # completed | cancelled | failed (cruise 생애주기)
created: {summary.md 기존 존재 시 보존, 없으면 신규 UTC ISO8601}
updated: {UTC ISO8601}
tags: []
base_branch: {base_branch}
files_changed: {정수}
insertions: {정수}
deletions: {정수}
check_result: pass         # pass | fail
check_tools:
  lint: pass               # pass | fail | skipped
  type: pass
  test: pass
requirements_checked: {정수}   # plan.md 검증 방법에서 처리한 요구사항 수
fix_attempts: {정수}           # 검사 레벨 Fix 시도 횟수
---
```

본문 구조 — **사람이 30초 안에 "이 브랜치가 뭘 했나"를 파악하는 요약**이 목적이다. 검사 원문·전체 표 같은 기계·디버그 material은 담지 않는다.

- `# Summary — {KEY}` (H1)
- `## 개요` — 이 브랜치가 무엇을 달성했는지 산문 요약 (task.md summary + plan.md `## 목표` 기반)
- `## 변경 파일` — 도메인/모듈별 그룹, 파일당 한 줄로 "무엇이 왜 바뀌었나" (name-status의 A/M/D 반영)
- `## 구현 현황` — plan.md Phase별 완료/스킵 상태
- `## 검증` — **압축 요약만**. plan에 검증 방법이 없으면 "- 검증 방법 없음".
  - 검사 한 줄: `- 검사: lint PASS · type PASS · test PASS` (skipped 포함)
  - 요구사항 한 줄: `- 요구사항 6건 중 5 pass · 1 fail` (검증 안 했으면 생략)
  - **fail·manual 항목만** 한 줄씩 진단: `- R3 fail: 빈 목록 시 스피너 미제거 (List.tsx:42)`. pass 항목은 나열하지 않는다. 에러 원문은 담지 않는다.
- `## 비고` — `has_uncommitted == true` 면 "미커밋 변경 포함", base 통계 미수집 사유 등 (없으면 생략)

변경 통계 수치(files_changed 등)는 frontmatter에만 두고 본문에는 반복하지 않는다. summary.md는 누적하지 않고 매번 전체 재작성한다. 입력은 plan.md · git diff · 이번 실행의 검사/검증 결과다.

"완료" 한 줄 출력 후 [STOP].
