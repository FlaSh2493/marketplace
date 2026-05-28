---
name: cruise-build
description: (명시적 커맨드 실행 전용) /cruise:build 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Build

> **종료 규칙:** 어떤 STEP에서 종료하든 Write 도구로
> `~/Documents/tasks/{KEY}/build.md` 를 기록하고 [STOP]한다.
> - frontmatter 공통 10필드 + 스킬별 필드 완비
> - `status`: completed | cancelled | failed
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용

> **금지:**
> - 산출물 작성 후 요약·다음 액션 추천·후속 작업 제안 일체 출력하지 않는다 ("완료" 한 줄만)
> - 사용자가 명시적으로 요청하지 않은 어떤 액션도 수행하지 않는다
> - 다른 스킬을 자동으로 호출하지 않는다

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

결과를 메모리에 보관: `root`, `branch`, `key`, `task_path`.

---

## STEP 2 — 선행 조건 확인

`~/Documents/tasks/{KEY}/task.md` 와 `~/Documents/tasks/{KEY}/plan.md` 가 모두 존재해야 한다.
둘 중 하나라도 없으면:
- status=failed 로 build.md 기록 (본문에 누락 파일 명시)
- [STOP]

---

## STEP 3 — 분기: 신규 실행 vs 재호출

`~/Documents/tasks/{KEY}/build.md` 존재 여부 확인.

**없음 → STEP 4 (신규 실행)**

**있음 → STEP 3a (재호출 모드)**

### STEP 3a — 재호출 모드 (후속 조정 자동 감지)

1. build.md의 frontmatter `head_sha` 읽기
2. `git rev-parse --short HEAD` 와 비교:
   - **동일** → 새 변경 없음. status=completed 유지, "완료" 후 [STOP]
   - **다름** → `git diff {build_head_sha}..HEAD --name-only` 로 변경 파일 추출
     - build.md 의 `## 후속 조정` 섹션에 아래 블록 append:
       ```
       ### 후속 조정 {n} — {UTC ISO8601}
       - head: {현재 HEAD sha}
       - 변경 파일: {파일 목록}
       - 커밋: {git log --oneline {build_head_sha}..HEAD}
       ```
     - frontmatter `updated`, `head_sha`, `commits`, `files_changed` 갱신
3. plan.md 에 신규 Phase 추가 여부 확인 → 있으면 STEP 4 Phase 루프 진입
4. 변경만 있고 신규 Phase 없으면 "완료" 후 [STOP]

---

## STEP 4 — plan.md Phase 파싱 및 실행 순서 결정

plan.md 의 `## 구현 계획` 섹션 읽기.
재호출 모드면 미완료 Phase만 처리.

---

## STEP 5 — Phase 단위 구현 루프

각 Phase 처리:

1. Phase 메타 `delegate` 확인:
   - `yes` → `agents/cruise-builder.md` 에이전트에 위임
   - `no` → 메인에서 직접 처리
   - `auto` (기본) → 변경 파일 ≥5개 또는 신규 파일 포함 시 에이전트 위임, 아니면 메인 처리

2. Phase 완료 후 build.md 갱신:
   - Phase 진행 표 누적 업데이트 (완료 체크)
   - frontmatter `updated`, `phases_completed` 갱신

게이트 없음. 사용자가 중단하고 싶으면 직접 중단.

**후속 조정 정책**: 1~2줄 사소한 수정은 build.md에 기록하지 않는다.
실질적 변경 후 `/cruise:build` 재호출 시 자동 감지·기록된다.

---

## STEP 6 — 완료

모든 Phase 완료 후 build.md 최종 저장:

frontmatter (공통 10필드 + 스킬별):
```yaml
---
key: {KEY}
key_source: {key_source}
skill: build
summary: {task.md에서 상속}
branch: {branch}
repo: {repo}
head_sha: {git rev-parse --short HEAD}
status: completed
created: {최초 생성 시각 UTC}
updated: {UTC ISO8601}
tags: []
phases_completed: {완료된 Phase 수}
phases_total: {전체 Phase 수}
files_changed: {변경된 파일 수}
commits:
  - {sha}
---
```

본문 구조:
- `# Build — {KEY}` (H1)
- `## Phase 진행` — 체크박스 표
- `## 구현 메모` — Phase별 주요 결정사항
- `## 후속 조정` — 재호출 시 append되는 블록들

"완료" 한 줄 출력 후 [STOP].
