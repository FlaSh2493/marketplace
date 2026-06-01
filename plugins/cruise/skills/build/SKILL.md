---
name: cruise-build
description: (명시적 커맨드 실행 전용) /cruise:build 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Build

> **종료 규칙:** 어떤 STEP에서 종료하든 Write 도구로
> `~/Documents/tasks/{KEY}/build.md` 를 기록하고 [STOP]한다.
> - frontmatter 공통 9필드 + 스킬별 필드 완비
> - `status`: completed | cancelled | failed
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용
> - 정상 종료(STEP 5까지 도달) 시 STEP 6에서 `~/Documents/tasks/{KEY}/summary.md` 도 매번 덮어쓴다.

> **금지:**
> - 산출물 작성 후 요약·다음 액션 추천·후속 작업 제안 일체 출력하지 않는다 ("완료" 한 줄만). 이 규칙은 **콘솔 출력**에 대한 것이며, STEP 6의 summary.md(파일 산출물) 작성과는 무관하다.
> - 사용자가 명시적으로 요청하지 않은 어떤 액션도 수행하지 않는다
> - 다른 스킬을 자동으로 호출하지 않는다
> - plan.archive / build.archive / summary.archive 디렉토리는 읽지 않는다 (사용자 참조 전용)

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

결과를 메모리에 보관: `root`, `branch`, `key`, `key_source`, `base_branch`, `base_source`, `repo`, `has_uncommitted`, `task_path`, `task_md_exists`, `plan_md_exists`, `build_md_exists`.

---

## STEP 2 — 선행 조건 확인

`task_md_exists == true && plan_md_exists == true` 이어야 한다.
둘 중 하나라도 false면:
- status=failed 로 build.md 기록 (본문에 누락 파일 명시 — 어떤 boolean이 false인지 기재)
- [STOP]

---

## STEP 3 — plan.md Phase 파싱

plan.md 의 `## 구현 계획` 섹션을 읽어 Phase 목록을 추출한다. 각 Phase의 메타(`delegate`)와 본문(요구 상태, 작업 내용)을 메모리에 보관.

---

## STEP 4 — Phase 단위 실행 루프

`{ts}` 생성 (UTC ISO8601). build.md 끝에 추가될 새 `## Run {ts}` 섹션을 메모리에 누적한다.

각 Phase 처리 순서:

1. **코드 반영 여부 판단**
   - Phase 명세가 요구하는 상태가 현재 코드에 이미 반영되어 있는지 LLM이 판단
   - 필요 시 관련 파일을 Read/Grep으로 확인
   - 결과:
     - 이미 반영됨 → Run 섹션에 `- {Phase title}: skipped (이미 반영)` 한 줄 추가, 다음 Phase
     - 미반영 → 2단계 진행

2. **구현 실행** (delegate 규칙)
   - `yes` → `agents/cruise-builder.md` 에이전트에 위임
   - `no` → 메인에서 직접 처리
   - `auto` (기본) → 변경 파일 ≥5개 또는 신규 파일 포함 시 에이전트 위임, 아니면 메인 처리

3. **결과 기록**: Run 섹션에 `- {Phase title}: executed` + 변경 파일 목록 한두 줄 append.

게이트 없음. 사용자가 중단하고 싶으면 직접 중단.

build.md에 진행 상태(`phases_completed` 등)는 저장하지 않는다. 다음 build 호출 시 동일한 "코드 반영 여부 판단"으로 자연 idempotent 동작.

---

## STEP 5 — build.md 저장

`build_md_exists == false` 면 신규 생성, true면 끝에 새 Run 섹션을 **append** 한다.

frontmatter (공통 9필드 + 스킬별):
```yaml
---
key: {KEY}
key_source: {key_source}
skill: build
summary: {task.md에서 상속}
branch: {branch}
repo: {repo}
status: completed
created: {최초 생성 시각 UTC, 신규 생성 시만 새로 기록 / 기존 파일이면 보존}
updated: {UTC ISO8601}
tags: []
runs_count: {append 누적 Run 섹션 수}
---
```

본문 구조 (append-only):
- `# Build — {KEY}` (H1, 신규 생성 시만)
- `## Run {ts}` — 매 호출마다 끝에 추가되는 섹션
  - `- head: {sha}`
  - Phase 처리 결과 목록 (skipped / executed)
  - 필요한 구현 메모

이전 Run 섹션은 절대 수정하지 않는다. 새 plan으로 전환되면 plan 스킬이 build.md 전체를 archive로 이동시킨다.

선행 조건 미충족(STEP 2) 등으로 여기서 종료하는 경우 summary.md는 작성하지 않고 [STOP]. 정상 경로면 STEP 6 진행.

---

## STEP 6 — summary.md 작성 (전체 변경 요약, 매번 덮어쓰기)

build.md(이번 실행에서 한 일의 append 로그)와 달리, summary.md는 **브랜치 전체(base 대비)의 변경**을 종합한 요약 1개를 **매 빌드마다 전체 덮어써서** 항상 최신 상태로 유지한다.

변경 통계 수집 (base 분기점부터 커밋 + 미커밋 전체):

```bash
TASK_DIR=~/Documents/tasks/{KEY}
BASE=$(git merge-base {base_branch} HEAD)
git diff --stat "$BASE"          # 파일별 +/- 및 합계
git diff --name-status "$BASE"   # 파일별 변경 유형(A/M/D)
```

`base_source == unknown` 등으로 base_branch를 신뢰할 수 없으면 통계 수집을 생략하고 본문 `## 변경 통계` 에 사유 한 줄만 기재한다.

Write 도구로 `~/Documents/tasks/{KEY}/summary.md` 를 **항상 덮어쓰기**(append 아님) 저장한다.

frontmatter (공통 9필드 + 스킬별):

```yaml
---
key: {KEY}
key_source: {key_source}
skill: summary
summary: {task.md에서 상속}
branch: {branch}
repo: {repo}
status: completed
created: {summary.md 기존 존재 시 보존, 없으면 신규 UTC ISO8601}
updated: {UTC ISO8601}
tags: []
base_branch: {base_branch}
files_changed: {정수}
insertions: {정수}
deletions: {정수}
---
```

본문 구조:

- `# Summary — {KEY}` (H1)
- `## 개요` — 이 브랜치가 무엇을 달성했는지 산문 요약 (task.md summary + plan.md `## 목표` 기반)
- `## 변경 통계` — files_changed, +insertions / -deletions
- `## 변경 파일` — 도메인/모듈별 그룹, 파일당 한 줄로 "무엇이 왜 바뀌었나" 설명 (name-status 의 A/M/D 반영)
- `## 구현 현황` — plan.md Phase별 완료/스킵 상태
- `## 비고` — `has_uncommitted == true` 면 "미커밋 변경 포함" 명시

summary.md는 누적하지 않고 매번 전체 재작성한다 (항상 최신 전체 요약 1개 유지). summary 작성에는 plan.md와 git diff 결과만 입력으로 사용한다.

"완료" 한 줄 출력 후 [STOP].
