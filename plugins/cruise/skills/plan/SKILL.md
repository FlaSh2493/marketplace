---
name: cruise-plan
description: (명시적 커맨드 실행 전용) /cruise:plan 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Plan

> **종료 규칙:** 어떤 STEP에서 종료하든 Write 도구로
> `~/Documents/tasks/{KEY}/plan.md` 를 기록하고 [STOP]한다.
>
> - frontmatter 공통 9필드 + 스킬별 필드 완비
> - `status`: completed | cancelled | failed
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용

> **금지:**
>
> - 산출물 작성 후 요약·다음 액션 추천·후속 작업 제안 일체 출력하지 않는다 ("완료" 한 줄만)
> - 사용자가 명시적으로 요청하지 않은 어떤 액션도 수행하지 않는다
> - 다른 스킬을 자동으로 호출하지 않는다
> - Plan mode가 동시 활성화된 경우 `~/Documents/tasks/{KEY}/plan.md` 작성 후 ExitPlanMode 호출만 하고 [STOP]한다. 승인 후에도 구현으로 넘어가지 않는다.
> - 수정 요청 시 plan.md를 갱신하고 "완료"만 출력한다. (이전 plan/build는 STEP 3.5에서 자동 archive)
> - build.md는 읽지 않는다. plan은 task.md와 대화 컨텍스트만 입력으로 사용한다.

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

결과를 메모리에 보관: `root`, `branch`, `key`, `key_source`, `base_branch`, `task_path`, `task_md_exists`, `plan_md_exists`, `build_md_exists`.

---

## STEP 2 — task.md 처리

**있는 경우** (`task_md_exists == true`):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py \
  --key {KEY} \
  --sections "배경,목표,요구사항,완료 조건,참고,제약"
```

섹션 내용을 베이스 명세로 사용. STEP 3 진행.

**없는 경우** (`task_md_exists == false`):
현재 대화 컨텍스트에서 아래 구조로 task.md를 자동 추출한다:

```yaml
---
key: { KEY }
key_source: { key_source }
skill: task
summary: { 대화에서 추출한 한 줄 요약 }
branch: { branch }
repo: { repo }
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

## STEP 2.5 — 요구사항 빠짐없이 분석

베이스 명세 + 대화 컨텍스트를 종합하여 요구사항을 **원자 단위로 분해**한다.

- 각 요구사항에 `R1`, `R2`, … ID를 부여한다. 이 ID는 `## 구현 계획`의 작업 항목·`## 검증 방법` 표, 그리고 이후 check·build 피드백이 일관되게 역참조하는 **추적 키**다 (요구사항↔구현↔검증).
- **명시 요구사항**(명세에 적힌 것)뿐 아니라 **암묵 요구사항**도 끌어낸다: 엣지케이스, 에러 처리, 빈/로딩 상태, 권한·인증, 하위 호환성, 접근성 등.
- 불명확하거나 가정이 필요한 항목은 임의로 단정하지 말고 **미지수**로 따로 모은다 (plan.md `## 요구사항` 하단 `### 미지수`).

---

## STEP 3 — 코드베이스 영향 분석 + 아키텍처 설계

분해된 요구사항(R1, R2, …) + 현재 대화의 추가 컨텍스트를 기준으로 영향 범위를 파악한다.

**code-review-graph MCP가 있는 경우**:

1. `semantic_search_nodes_tool` — 요구사항 키워드로 관련 노드 검색
2. `get_impact_radius_tool` — 영향 파일 2-hop 추적

**없는 경우**: Glob/Grep fallback으로 직접 탐색.

분석 결과로 **기술 설계 결정**을 종합한다 (plan.md `## 아키텍처 / 기술 설계` 에 기록):

- 데이터/제어 흐름, 주요 모듈 간 경계와 관계
- 도입·변경하는 기술과 그 **이유**
- 재사용할 **기존 함수·유틸·패턴**의 경로 (새로 만들지 말고 우선 재사용)

> **자기검증:** 영향 범위에 빠진 곳이 없는지 1회 자문한다 — 변경 대상의 호출부·역참조(backlink)까지 포함되었는가.

---

## STEP 3.5 — 기존 plan/build archive

`plan_md_exists == true` 인 경우에만 수행. 새 plan을 쓰기 전에 이전 산출물을 아카이브한다.

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
TASK_DIR=~/Documents/tasks/{KEY}
mkdir -p "$TASK_DIR/plan.archive" "$TASK_DIR/build.archive" "$TASK_DIR/summary.archive"
mv "$TASK_DIR/plan.md" "$TASK_DIR/plan.archive/plan-$TS.md"
[ -f "$TASK_DIR/build.md" ]   && mv "$TASK_DIR/build.md"   "$TASK_DIR/build.archive/build-$TS.md"
[ -f "$TASK_DIR/summary.md" ] && mv "$TASK_DIR/summary.md" "$TASK_DIR/summary.archive/summary-$TS.md"
```

- 같은 `{ts}` 로 plan / build / summary를 짝지어 archive (대응 관계 보존)
- build.md · summary.md 없으면 해당 archive는 생략
- archive 파일은 이후 어떤 스킬도 읽지 않는다 (사용자 참조 전용)

---

## STEP 4 — plan.md 작성

`templates/plan.md` 형식을 따른다. Write 도구로 `~/Documents/tasks/{KEY}/plan.md` 저장.

frontmatter (공통 9필드 + 스킬별):

```yaml
---
key: { KEY }
key_source: { key_source }
skill: plan
summary: { task.md에서 상속, 없으면 브랜치명 추론 }
branch: { branch }
repo: { repo }
status: completed
created: { UTC ISO8601 }
updated: { UTC ISO8601 }
tags: []
phases_count: { Phase 수 정수 }
---
```

본문 구조 (헤딩 순서·텍스트 고정):

- `# Plan — {KEY}` (H1)
- `## 배경` — 명세 배경
- `## 목표` — 명세 목표
- `## 요구사항` — STEP 2.5에서 분해한 `- [ ] R1: …` 체크리스트. 하단에 `### 미지수`(불명확/가정, 없으면 생략).
- `## 추가 컨텍스트 (대화)` — 대화의 추가 컨텍스트 (없으면 섹션 생략)
- `## 영향 범위` — 분석된 파일·모듈 표
- `## 아키텍처 / 기술 설계` — 데이터/제어 흐름(텍스트 다이어그램 `A → B → C`), 모듈 경계, 기술 선택과 이유, 재사용할 기존 함수·유틸 경로
- `## 구현 계획` — Phase 단위 계획. 각 Phase에 **반드시 포함**:
  - `<!-- delegate: auto|yes|no -->` 메타
  - 작업 항목 체크리스트 — 각 항목 끝에 충족하는 요구사항 ID 표기 (예: `- [ ] … (R1, R3)`)
  - `**생성/수정 파일**` — 트리 또는 목록으로 폴더구조·파일 경로 명시 (신규는 `(new)` 표기)
  - `**샘플 코드**` — 핵심 파일의 골격을 코드펜스로. 시그니처·주요 함수·핵심 로직 위주 (전체 구현 아님). 프로젝트 언어·컨벤션에 맞춘다.
- `## 검증 방법` — 요구사항↔검증 추적 표 (`| 요구사항 | 검증 방법 | 도구/명령 |`). 자동 검증 불가 항목은 수동 절차를 명시. lint/type/test로 덮이는 항목은 check 스킬로 표기.
- `## 완료 조건` — 명세 완료 조건

---

## STEP 5 — 종료

"완료" 한 줄 출력 후 [STOP].
