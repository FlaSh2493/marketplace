---
name: autopilot-plan
description: 워크트리를 생성하고 이슈 명세를 로드하여 플랜 및 구현을 진행한다. 이슈는 여러 개 지정 가능하며 상호 영향을 고려한 통합 플랜을 수립한다. --no-spec 플래그를 사용하면 명세 로드 없이 사용자 요구사항 기반으로 작업한다. 추가 수정 요청 시 컨텍스트를 유지하며 반복한다.
---

# Worktree Plan

**실행 주체: Main Session**
`{이슈키}.md`의 `## 설명` 섹션 수정 절대 금지 — Jira 원본 보존. 추가 요구사항은 `## 추가 요구사항` 섹션에만 append.

## 사용법
```
/autopilot:plan {브랜치명} [이슈키1 이슈키2 ...] [--no-spec]
/autopilot:plan {이슈키1} [이슈키2 ...] [--no-spec]   ← 브랜치명 생략 가능
```
- 브랜치명 생략 규칙: 첫 번째 인수가 `[A-Z]+-[0-9]+` 패턴(이슈키)이면 브랜치명으로 보지 않고, `feat/{첫번째이슈키소문자}` 를 브랜치명으로 자동 생성한다. (예: `SPT-3711` → `feat/spt-3711`)
- 이슈키 필수. 생략 시 로컬 이슈 목록에서 선택
- `--no-spec` 없음: 이슈 명세 로드 후 플랜 수립
- `--no-spec` 있음: 명세 로드 없이 사용자 요구사항 기반으로 작업

---

## 전제조건 — 워크트리 진입 (완료 전까지 아래로 절대 넘어가지 않는다)

1. 이슈키가 없으면:
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/list_issues.py` 실행
   성공: 이슈 목록 출력 후 AskUserQuestion("작업할 이슈키를 선택하세요 (여러 개면 공백으로 구분):\n{목록}")
   실패 또는 목록 비어있음: AskUserQuestion("작업할 이슈키를 입력하세요 (여러 개면 공백으로 구분):")
   입력받은 값을 이슈키로 사용

2. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure_worktree.py {브랜치명} --issues {이슈키1} [이슈키2...]`
   성공: data.display를 사용자에게 그대로 출력. data.worktree_path, data.branch, data.issue_doc_root, data.base_branch, data.issues 보관
   실패: reason 출력 후 [STOP]
3. `cd {data.worktree_path} && pwd && git branch --show-current` 실행하여 경로·브랜치 확인

**경로 규칙** (Bash는 매 호출마다 새 셸 — 매번 cd prefix 필수):

| 작업 | 경로 |
|------|------|
| **이슈 문서** 읽기/수정 | `load_issue.py`가 반환한 `md_path` |
| **코드** Read/Edit/Write/Glob/Grep | `{data.worktree_path}/파일경로` |
| **Bash/git** 명령 | `cd {data.worktree_path} && command` |

**⚠ `data.issue_doc_root`는 이슈 문서 전용. 코드 파일에 사용하면 피처 브랜치에 직접 수정된다. 코드는 반드시 `{data.worktree_path}/`만 사용한다.**

---

## 이슈 로드

`--no-spec` 플래그가 있으면 이 섹션 전체 스킵 — 사용자가 다음 메시지로 요구사항을 전달할 때까지 대기.

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
`api`와 `states`는 이슈 문서에 별도 섹션이 없으므로 아래 순서로 코드베이스에서 자동 추출하여 플랜 컨텍스트에만 보관한다 (문서에 쓰지 않는다).

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
추출한 api/states 값을 플랜 작성 시 영향 범위 분석에 활용한다.
이슈 문서는 수정하지 않는다.

플랜 출력 시 아래 형식으로 "사용 API 목록" 섹션을 반드시 포함한다:
```
### 사용 API 목록
| 메서드 | 엔드포인트 | 호출 위치 |
|--------|-----------|----------|
| GET    | /api/cart | src/entities/cart/api.ts |
| POST   | /api/cart | src/entities/cart/api.ts |
```
추출된 API가 없으면 `(없음 — 신규 API 작성 필요)` 또는 `(해당 없음)` 으로 표기한다.

---

## 작업 규칙

### 플랜 작성 규칙

**1. 공통 컴포넌트 우선** — 새 컴포넌트 작성 전 `semantic_search_nodes_tool` 또는 Grep으로 기존 컴포넌트 탐색. 사용할 컴포넌트명·경로·활용 방식을 플랜에 명시.

**2. 파일 배치 계획** — 신규 파일마다 레이어와 경로를 플랜에 명시한다. 기준:

| 레이어 | 위치 | 해당 항목 |
|--------|------|-----------|
| `features/` | `src/features/{도메인}/` | 특정 도메인에만 쓰이는 컴포넌트·훅·핸들러·유틸 |
| `entities/` | `src/entities/{도메인}/` | 도메인 모델, API 호출 함수, 타입 정의 |
| `shared/` | `src/shared/` | 2개 이상 도메인에서 사용하는 컴포넌트·훅·유틸 |

- **훅**: 단일 도메인 전용 → `features/{도메인}/hooks/`, 범용 → `shared/hooks/`
- **핸들러**: 이벤트 핸들러는 컴포넌트와 같은 디렉토리 또는 `features/{도메인}/handlers/`
- **유틸**: 도메인 전용 → `features/{도메인}/utils/`, 범용 → `shared/utils/`
- 기존 프로젝트 구조가 다르면 `rg --files src/ | head -50`으로 실제 구조 확인 후 따른다.

각 파일에 대해 플랜에 아래 형식으로 명시:
```
- src/features/cart/hooks/useCartSubmit.ts  (신규) — 장바구니 제출 로직
- src/entities/cart/api.ts                  (수정) — POST /api/cart 엔드포인트 추가
- src/shared/hooks/useDebounce.ts           (재사용) — 기존 훅 그대로 사용
```

**3. 이미지 분석** — 로드한 이슈의 `## 화면/디자인` 섹션에 `![` 패턴이 있으면:
Read로 이미지를 직접 열어 아래 항목을 **구현에 바로 쓸 수 있는 수준**으로 상세하게 분석한 뒤, 플랜에 "### 화면 분석" 섹션으로 반드시 포함한다. 구현 중엔 이 텍스트만 참고하고 이미지를 다시 열지 않는다.

```
### 화면 분석
- 레이아웃: 전체 구조 (예: 헤더 고정 + 본문 스크롤 + 하단 CTA full-width)
- 컴포넌트 목록:
  - [화면 요소] → <ComponentName prop="value"> (경로: src/shared/...)
  - ...
- 상태별 UI:
  - [상태명]: [UI 변화 설명]
  - ...
- spacing/color 토큰:
  - [수치/색상] → [토큰명] (예: 16px → gap-4, #3B82F6 → color.primary)
- 구현 시 주의사항: 놓치기 쉬운 디테일, 조건부 렌더링, 엣지케이스
```

`## 화면/디자인` 섹션이 없거나 이미지가 없으면 스킵.

**4. 파일 충돌 명시** (이슈 여러 개인 경우) — 동일 파일을 수정하는 이슈가 있으면 통합 처리 또는 순서 분리 방안을 플랜에 명시.

**5. 구현 순서** — 이슈 간 의존 관계가 있으면 선행 이슈 먼저 구현하도록 순서 명시.

**영향 범위 분석** (플랜 작성 시):
1. 이슈 명세 또는 요구사항에서 키워드 추출 → `semantic_search_nodes_tool` (limit: 10)
2. 결과 있으면 `get_impact_radius_tool` (changed_files: 위 결과, max_depth: 2)
3. 결과 없으면 fallback: `cd {data.worktree_path} && rg {패턴}`

관련 파일 Read 시 반드시 `{data.worktree_path}/파일경로` 사용 (도구 결과가 메인 경로를 반환해도 워크트리 경로로 치환).

**커밋**: 구현 중 WIP 커밋하지 않는다. 커밋은 merge 단계에서 처리한다.

**구현 완료 후 이미지 재확인** — 이슈 문서에 이미지(`![`)가 1개 이상 있으면:
1. 이슈 문서의 모든 이미지를 Read로 다시 확인
2. 각 이미지와 구현된 코드를 대조하여 아래 항목 검토:
   - 레이아웃·구조 일치 여부
   - 컴포넌트 구성 누락 여부
   - 텍스트·라벨·상태값 일치 여부
3. 불일치 항목이 있으면 해당 부분 재작업 → 완료 후 이미지와 다시 대조. 모두 일치할 때까지 반복.
   일치하면 "✅ 이미지 대조 완료 — 일치" 출력 후 진행.
이미지가 없으면 이 단계 스킵.

**구현 완료 후**: AskUserQuestion에 다음 선택지를 제시:
```
구현이 완료되었습니다. 다음 중 선택하세요:
1. `/autopilot:check` — lint, type-check, test 검사 실행 (오류 시 자동 수정)
2. `/autopilot:merge {피처브랜치}` — 이 워크트리만 피처 브랜치에 머지
3. `/autopilot:merge-all {피처브랜치}` — 모든 활성 워크트리를 한번에 머지
4. 추가 작업 계속
```
