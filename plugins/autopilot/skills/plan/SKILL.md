---
name: autopilot-plan
description: 워크트리를 생성하고 이슈 명세를 로드하여 플랜을 수립한 뒤 .docs/plan/{브랜치명}.plan.md 로 저장한다. 실제 구현은 별도 /autopilot:build 에서 수행한다. --no-spec 플래그를 사용하면 명세 로드 없이 사용자 요구사항 기반으로 플랜을 작성한다. --replan 플래그는 워크트리/이슈 로드를 재사용하고 plan.md 만 재생성한다.
---

# Worktree Plan

**실행 주체: Main Session**
`{이슈키}.md`의 `## 설명` 섹션 수정 절대 금지 — Jira 원본 보존. 추가 요구사항은 `## 추가 요구사항` 섹션에만 append.

이 스킬은 **플랜 수립까지만** 담당한다. 실제 코드 편집은 하지 않는다. 완료 시 `{issue_doc_root}/.docs/plan/{브랜치명}.plan.md` 를 생성하고 `/autopilot:build` 로 넘긴다.

## 사용법
```
/autopilot:plan [-b {브랜치명}] {이슈키}            ← 단일 이슈, -b로 브랜치명 지정 가능
/autopilot:plan {이슈키1} {이슈키2} ...             ← 다중 이슈, 워크트리 각각 생성
/autopilot:plan {브랜치명} [이슈키1 ...] [--no-spec] ← 브랜치명 직접 지정
/autopilot:plan {브랜치명} --replan                  ← plan.md 만 재생성
```

**인수 파싱 규칙:**
- `-b {브랜치명}` 플래그: 워크트리 브랜치명을 직접 지정 (이슈 1개일 때만 유효)
  - `-b` + 이슈 여러 개 → "에러: -b는 이슈 1개일 때만 사용 가능합니다" 출력 후 [STOP]
- 첫 번째 인수가 `[A-Z]+-[0-9]+` 패턴(이슈키)이면 브랜치명이 아닌 이슈키로 인식
  - 이슈 1개: `feat/{이슈키소문자}` 자동 생성 (단, `-b` 지정 시 그 값 사용)
  - 이슈 여러 개: 각 이슈마다 `feat/{이슈키소문자}` 자동 생성 → 워크트리 개별 생성
- 첫 번째 인수가 이슈키 패턴이 아니면 브랜치명으로 인식 (기존 동작 유지)
- `--no-spec`: 명세 로드 없이 사용자 요구사항 기반으로 플랜 작성
- `--replan`: 기존 워크트리를 재사용하여 plan.md 만 다시 작성

---

## 전제조건 — 워크트리 진입 (완료 전까지 아래로 절대 넘어가지 않는다)

1. 이슈키가 없으면:
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/list_issues.py` 실행
   성공: 이슈 목록 출력 후 AskUserQuestion("작업할 이슈키를 선택하세요 (여러 개면 공백으로 구분):\n{목록}")
   실패 또는 목록 비어있음: AskUserQuestion("작업할 이슈키를 입력하세요 (여러 개면 공백으로 구분):")
   입력받은 값을 이슈키로 사용

2. 워크트리 생성:

   **이슈 1개인 경우:**
   브랜치명 = `-b` 지정값 또는 `feat/{이슈키소문자, 특수문자→하이픈}`
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure_worktree.py {브랜치명} --issues {이슈키}` 실행
   성공: data.display를 사용자에게 그대로 출력. data.worktree_path, data.branch, data.issue_doc_root, data.base_branch, data.issues 보관
   실패: reason 출력 후 [STOP]

   **이슈 여러 개인 경우:**
   각 이슈키별로 순서대로:
     브랜치명 = `feat/{이슈키소문자, 특수문자→하이픈}`
     `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure_worktree.py {브랜치명} --issues {이슈키}` 실행
     성공: data 보관
     실패: reason 출력 후 [STOP]

   전체 생성 완료 후 요약 출력:
   ```
   ┌─────────────────────────────────────────────
   │ 워크트리 {N}개 생성 완료 (base: {현재브랜치})
   │ - {브랜치명1}  →  {경로1}
   │ - {브랜치명2}  →  {경로2}
   └─────────────────────────────────────────────
   ```

3. `cd {data.worktree_path} && pwd && git branch --show-current` 실행하여 경로·브랜치 확인 (이슈 1개인 경우)

**경로 규칙** (Bash는 매 호출마다 새 셸 — 매번 cd prefix 필수):

| 작업 | 경로 |
|------|------|
| **이슈 문서** 읽기/수정 | `load_issue.py`가 반환한 `md_path` |
| **plan.md** 쓰기 | `{data.issue_doc_root}/.docs/plan/{data.branch 의 `/` → `-` 치환}.plan.md` |
| **코드** Read/Glob/Grep (탐색용) | `{data.worktree_path}/파일경로` |
| **Bash/git** 명령 | `cd {data.worktree_path} && command` |

**⚠ `data.issue_doc_root`는 이슈 문서/플랜 전용. 코드 파일에 사용하면 피처 브랜치에 직접 수정된다. 코드 탐색은 반드시 `{data.worktree_path}/`만 사용한다.**

**⚠ 이 스킬에서는 코드 파일을 Edit/Write 하지 않는다.** 탐색(Read/Glob/Grep/semantic_search)만 허용.

---

## 이슈 로드

`--no-spec` 플래그가 있으면 이 섹션 전체 스킵 — 사용자가 다음 메시지로 요구사항을 전달할 때까지 대기하고, 받은 원문을 plan.md "요구사항 요약" 에 그대로 기록.

`--no-spec` 없으면 `data.issues`의 각 이슈키별로 순차 실행:
```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키} --sections 목적,화면/디자인,컴포넌트 힌트,영향 범위,완료 조건,선행 이슈,추가 요구사항,사용 API 목록
```
성공: 내용을 컨텍스트로 보관
실패: reason 출력 후 [STOP]

이슈가 여러 개면 전체 명세를 합쳐 컨텍스트에 유지한다.

---

## 메타데이터 자동 보완

로드한 이슈의 `## 선행 이슈` 섹션이 비어있거나 `없음`이면 건너뛴다.
`api`와 `states`는 이슈 문서에 별도 섹션이 없으므로 아래 순서로 코드베이스에서 자동 추출하여 플랜 컨텍스트에만 보관한다 (이슈 문서에 쓰지 않는다).

### api / states 자동 추출
이슈 설명에서 도메인 키워드(명사, 기능명) 추출 후 스크립트 실행:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_metadata.py {data.worktree_path} --keywords {키워드1} {키워드2} ...
```
결과: `data.apis[]` (method, endpoint, file), `data.states[]` (store, state_name, file)

### deps 자동 추출
Jira 이슈 링크는 `load_issue.py` 결과에 포함되지 않으므로 deps는 자동 추출하지 않는다.
`없음`이면 그대로 유지.

### 추출 결과 반영
추출한 api/states 값을 plan.md "사용 API 목록" 및 영향 범위 분석에 활용한다.
이슈 문서는 수정하지 않는다.

---

## 플랜 작성 규칙

### 1. 공통 컴포넌트 우선
새 컴포넌트 작성 전 `semantic_search_nodes_tool` 또는 Grep으로 기존 컴포넌트 탐색. 사용할 컴포넌트명·경로·활용 방식을 plan.md "대상 파일" 에 명시.

### 2. 파일 배치 계획
신규 파일마다 레이어와 경로를 결정한다. 기준:

| 레이어 | 위치 | 해당 항목 |
|--------|------|-----------|
| `features/` | `src/features/{도메인}/` | 특정 도메인에만 쓰이는 컴포넌트·훅·핸들러·유틸 |
| `entities/` | `src/entities/{도메인}/` | 도메인 모델, API 호출 함수, 타입 정의 |
| `shared/` | `src/shared/` | 2개 이상 도메인에서 사용하는 컴포넌트·훅·유틸 |

- **훅**: 단일 도메인 전용 → `features/{도메인}/hooks/`, 범용 → `shared/hooks/`
- **핸들러**: 이벤트 핸들러는 컴포넌트와 같은 디렉토리 또는 `features/{도메인}/handlers/`
- **유틸**: 도메인 전용 → `features/{도메인}/utils/`, 범용 → `shared/utils/`
- 기존 프로젝트 구조가 다르면 `rg --files src/ | head -50`으로 실제 구조 확인 후 따른다.

### 3. 이미지 분석
로드한 이슈의 `## 화면/디자인` 섹션에 `![` 패턴이 있으면 Read로 이미지를 열어 아래 항목을 **구현에 바로 쓸 수 있는 수준**으로 분석하고, plan.md "화면 분석" 섹션에 기록한다. build 단계는 이 텍스트만 참조하고 이미지를 재분석하지 않는다.

```
### 화면 분석
- 레이아웃: 전체 구조 (예: 헤더 고정 + 본문 스크롤 + 하단 CTA full-width)
- 컴포넌트 목록:
  - [화면 요소] → <ComponentName prop="value"> (경로: src/shared/...)
- 상태별 UI:
  - [상태명]: [UI 변화 설명]
- spacing/color 토큰:
  - [수치/색상] → [토큰명] (예: 16px → gap-4, #3B82F6 → color.primary)
- 구현 시 주의사항: 놓치기 쉬운 디테일, 조건부 렌더링, 엣지케이스
```

이미지 경로는 "이미지 목록" 섹션에도 열거한다. build 완료 후 이미지 재확인 단계에서 사용된다.

`## 화면/디자인` 섹션이 없거나 이미지가 없으면 두 섹션 모두 생략.

### 4. 파일 충돌 명시 (이슈 여러 개인 경우)
동일 파일을 수정하는 이슈가 있으면 통합 처리 또는 순서 분리 방안을 "파일 충돌/의존" 섹션에 명시.

### 5. 구현 순서
이슈 간 의존 관계가 있으면 선행 이슈 먼저 구현하도록 순서 명시.

### 영향 범위 분석
1. 이슈 명세 또는 요구사항에서 키워드 추출 → `semantic_search_nodes_tool` (limit: 10)
2. 결과 있으면 `get_impact_radius_tool` (changed_files: 위 결과, max_depth: 2)
3. 결과 없으면 fallback: `cd {data.worktree_path} && rg {패턴}`

관련 파일 Read 시 반드시 `{data.worktree_path}/파일경로` 사용 (도구 결과가 메인 경로를 반환해도 워크트리 경로로 치환).

---

## plan.md 출력

**파일 경로**: `{data.issue_doc_root}/.docs/plan/{data.branch 의 "/" → "-" 치환}.plan.md`
예) `data.branch = feat/spt-3711` → `{issue_doc_root}/.docs/plan/feat-spt-3711.plan.md`
디렉토리가 없으면 생성: `mkdir -p {data.issue_doc_root}/.docs/plan`

**포맷** (아래 템플릿을 Write 로 생성. 해당 없는 섹션은 생략):

```markdown
---
branch: {data.branch}
issues: [{data.issues 쉼표 구분}]
base_branch: {data.base_branch}
worktree_path: {data.worktree_path}
issue_doc_root: {data.issue_doc_root}
spec_mode: full | no-spec
generated_at: {ISO-8601 KST}
---

## 요구사항 요약
(이슈 명세에서 구현에 필요한 내용만 정제. `--no-spec` 모드에서는 사용자 원문을 그대로 기록.)

## 화면 분석
(이미지 기반 분석. 이미지 없으면 섹션 생략.)

## 이미지 목록
- {이미지 경로 1}
- {이미지 경로 2}

## 사용 API 목록
| 메서드 | 엔드포인트 | 호출 위치 |
|--------|-----------|----------|
| GET    | /api/cart | src/entities/cart/api.ts |

추출된 API가 없으면 `(없음 — 신규 API 작성 필요)` 또는 `(해당 없음)` 으로 표기한다.

## 대상 파일
- src/features/cart/hooks/useCartSubmit.ts  (신규) — 장바구니 제출 로직
- src/entities/cart/api.ts                  (수정) — POST /api/cart 엔드포인트 추가
- src/shared/hooks/useDebounce.ts           (재사용) — 기존 훅 그대로 사용

## 구현 순서
1. entities/cart/api.ts 에 POST 추가
2. features/cart/hooks/useCartSubmit.ts 신설
3. ...

## 파일 충돌/의존
(이슈가 1개이거나 충돌 없으면 섹션 생략.)
```

plan.md 는 피처 브랜치의 `issue_doc_root` 아래에 저장되므로 **피처 브랜치에 커밋 대상이 된다**. 이는 의도된 동작(리뷰·이력화)이며 gitignore 하지 않는다. 단, 이 스킬은 커밋하지 않는다 — merge 단계에서 처리.

---

## 완료 안내

**이슈 1개인 경우:**
plan.md Write 후 사용자에게 아래 문구를 출력하고 스킬 종료:

```
✅ 플랜이 {plan.md 절대경로} 에 저장되었습니다.

검토 후 구현을 진행하려면:
  /autopilot:build {data.branch}

플랜 수정이 필요하면:
  - plan.md 를 직접 편집 (간단한 수정)
  - /autopilot:plan {data.branch} --replan (재탐색 포함 재생성)
```

**이슈 여러 개인 경우:**
모든 워크트리의 plan.md 생성 완료 후 아래 문구를 출력하고 스킬 종료:

```
✅ 플랜 {N}개 저장 완료

각 워크트리별 구현 명령어:
  /autopilot:build {브랜치명1}
  /autopilot:build {브랜치명2}
  ...

전체 머지:
  /autopilot:merge-all
```

**이 스킬에서는 구현·커밋·merge 를 수행하지 않는다.** 후속 단계는 반드시 `/autopilot:build` 로 넘긴다.
