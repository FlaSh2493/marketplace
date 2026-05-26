---
name: cruise-plan
description: (명시적 커맨드 실행 전용) /cruise:plan 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Plan

> **종료 규칙:** 어떤 STEP에서 종료하든 Write 도구로
> `~/Documents/tasks/{KEY}/plan.md` 를 기록하고 [STOP]한다.
>
> - frontmatter 공통 10필드 + 스킬별 필드 완비
> - `status`: completed | cancelled | failed
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용

> **금지:**
>
> - 산출물 작성 후 요약·다음 액션 추천·후속 작업 제안 일체 출력하지 않는다 ("완료" 한 줄만)
> - 사용자가 명시적으로 요청하지 않은 어떤 액션도 수행하지 않는다
> - 다른 스킬을 자동으로 호출하지 않는다
> - Plan mode가 동시 활성화된 경우 `~/Documents/tasks/{KEY}/plan.md` 작성 후 ExitPlanMode 호출만 하고 [STOP]한다. 승인 후에도 구현으로 넘어가지 않는다.
> - 수정 요청 시 plan.md를 갱신하고 "완료"만 출력한다.

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

결과를 메모리에 보관: `root`, `branch`, `key`, `key_source`, `base_branch`, `task_path`.

---

## STEP 2 — task.md 처리

**있는 경우** (`task_path` 존재):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py \
  --key {KEY} \
  --sections "배경,목표,요구사항,완료 조건,참고,제약"
```

섹션 내용을 베이스 명세로 사용. STEP 3 진행.

**없는 경우** (task_path 없음):
현재 대화 컨텍스트에서 아래 구조로 task.md를 자동 추출한다:

```yaml
---
key: { KEY }
key_source: { key_source }
skill: task
summary: { 대화에서 추출한 한 줄 요약 }
branch: { branch }
repo: { repo }
head_sha: ""
status: completed
created: { UTC ISO8601 }
updated: { UTC ISO8601 }
source: cruise-inline
tags: []
---
```

본문: `## 배경`, `## 목표`, `## 요구사항`, `## 완료 조건` 섹션으로 구조화.
Write 도구로 `~/Documents/tasks/{KEY}/task.md` 저장 후 STEP 3 진행.

task.md는 이후 수정하지 않는다 (소스 오브 트루스 보존).
게이트 없음. 폴더명·명세 변경은 plan.md 완성 후 대화로 지시.

---

## STEP 3 — 코드베이스 영향 분석

베이스 명세 + 현재 대화의 추가 컨텍스트를 종합하여 영향 범위 파악.

**code-review-graph MCP가 있는 경우**:

1. `semantic_search_nodes_tool` — 이슈 명세 키워드로 관련 노드 검색
2. `get_impact_radius_tool` — 영향 파일 2-hop 추적

**없는 경우**: Glob/Grep fallback으로 직접 탐색.

---

## STEP 4 — plan.md 작성

`templates/plan.md` 형식을 따른다. Write 도구로 `~/Documents/tasks/{KEY}/plan.md` 저장.

frontmatter (공통 10필드 + 스킬별):

```yaml
---
key: { KEY }
key_source: { key_source }
skill: plan
summary: { task.md에서 상속, 없으면 브랜치명 추론 }
branch: { branch }
repo: { repo }
head_sha: { git rev-parse --short HEAD 결과 }
status: completed
created: { UTC ISO8601 }
updated: { UTC ISO8601 }
tags: []
phases_count: { Phase 수 정수 }
---
```

본문 구조:

- `# Plan — {KEY}` (H1)
- `## 배경` — 명세 배경
- `## 목표` — 명세 목표
- `## 요구사항` — 명세 요구사항
- `## 추가 컨텍스트 (대화)` — 대화의 추가 컨텍스트 (없으면 섹션 생략)
- `## 영향 범위` — 분석된 파일·모듈 목록
- `## 구현 계획` — Phase 단위 계획 (각 Phase에 `delegate: auto|yes|no` 메타 포함)
- `## 완료 조건` — 명세 완료 조건

---

## STEP 5 — 종료

"완료" 한 줄 출력 후 [STOP].
