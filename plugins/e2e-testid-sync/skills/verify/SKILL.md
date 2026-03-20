---
name: e2e-testid-verify
description: >
  삽입된 data-testid를 PDF 원본 요구사항과 1:1 대조하여
  summary.md와 result.json을 생성하는 검증 스킬.
  다음과 같은 상황에서 트리거:
  "삽입 결과 검증", "testid 대조", "요구사항 비교",
  "summary 만들어줘", "결과 정리해줘", "삽입 확인해줘"
---

# E2E Test-ID Verify Workflow

삽입 완료 후, PDF 원본 요구사항과 실제 코드를 1:1 대조하여
`result.json`과 `summary.md`를 생성합니다.

## 0. 입력 (Input)

- `.docs/e2e/{YYYYMMDD}/parsed-requirements.json` (Phase 1 산출물)
- `.docs/e2e/{YYYYMMDD}/` 내 원본 PDF 파일
- 실제 코드베이스 (apps/data-center/src/)

## 1. 단계별 워크플로우

### Phase 1: 원본 요구사항 수집

1. PDF 원본을 직접 읽어 **4장 테이블의 모든 행**을 순번(001~)으로 넘버링한다.
2. `parsed-requirements.json`의 items와 대조하여 누락/추가 여부를 확인한다.
3. **원본 PDF의 테이블 행 수가 정본**이다. `parsed-requirements.json`의 `meta.totalItems`가 다르면 PDF 기준으로 보정한다.

### Phase 2: 코드베이스 스캔

각 요구사항에 대해 실제 코드에서 삽입 상태를 확인한다.

1. `grep -r "data-testid"` 로 프로젝트 내 모든 `data-testid`를 수집한다.
2. 요구사항의 `testId`가 **정적**이면: 정확히 일치하는 `testId`가 코드에 있는지 확인.
3. 요구사항의 `testId`가 **동적** (`${...}` 포함)이면: 패턴의 정적 prefix가 코드에 있는지 확인.
4. 요구사항의 `testId`가 코드에 없지만, **동일 기능을 수행하는 다른 testId**로 삽입된 경우를 탐지한다.

### Phase 3: 분류 기준

각 요구사항을 다음 중 하나로 분류한다:

#### ✅ 일치
- 요구 `testId`와 삽입된 `testId`가 동일 (동적 패턴의 변수명 차이는 무시 — 런타임 값이 같으면 일치)

#### ⚠️ 이름 다름 (삽입됨)
- 해당 UI 요소에 `data-testid`가 삽입되어 있으나, 요구사항과 `testId` 이름이 다른 경우
- **반드시 실제 렌더링되는 값을 명시**한다
- 공통 동적 패턴으로 통합된 경우 (예: ToolBox `dc-toolbox-${tool.key}`, 컬럼 메뉴 `dc-column-menu-${id}`):
  - 해당 `tool.key` 또는 `id`의 **실제 상수값**을 코드에서 찾아 기재한다
  - 상수 정의 파일(`constants/`)을 반드시 확인한다

#### 🔘 스킵
- 코드에 삽입할 수 없는 경우만 해당
- 사유를 구체적으로 기재 (컴포넌트 미지원, UI 비활성화, 구조적 제약 등)

### Phase 4: 동적 패턴 비교 규칙

동적 `testId` 비교 시 다음 규칙을 따른다:

1. **변수명이 다르더라도 런타임 값이 같으면 ✅ 일치**
   - 예: `${id}` vs `${row.id}` → 같은 ID 값이 들어감 → ✅
   - 예: `${index}` vs `${currentIndex}` → 같은 인덱스 값 → ✅
   
2. **런타임 값의 의미가 다를 수 있으면 ⚠️ 표시**
   - 예: `${accountName}` vs `${tableName}` → 계정명 vs 테이블명, 다를 수 있음 → ⚠️

3. **공통 동적 패턴으로 통합된 경우**: 개별 요구사항마다 실제 렌더링 값을 기재
   - ToolBox: `dc-toolbox-${tool.key}` → 실제 key 값 확인 (`constants/modal.ts` 등)
   - 컬럼 메뉴: `dc-column-menu-${id}` → 실제 id 값 확인 (`constants/gird.ts` 등)

### Phase 5: 산출물 생성

#### result.json

```json
{
  "meta": {
    "generatedAt": "YYYY-MM-DD",
    "totalRequirements": N,
    "injected": N,
    "injectedExact": N,
    "injectedRenamed": N,
    "skipped": N,
    "errors": 0,
    "filesModified": N
  },
  "injectedItems": [
    {
      "id": "LST-001",
      "reqTestId": "요구사항의 testId (다를 때만)",
      "testId": "실제 삽입된 testId 또는 렌더링되는 값",
      "renderedAs": "동적 패턴 (동적일 때만)",
      "sharedWith": "공유 패턴의 원본 LST ID (공유일 때만)",
      "dynamic": true,
      "ariaBusy": true,
      "file": "상대경로",
      "note": "특이사항 (필요시)"
    }
  ],
  "skippedItems": [
    {
      "id": "LST-023",
      "reqTestId": "요구사항의 testId",
      "reason": "구체적 스킵 사유"
    }
  ],
  "notesForE2E": ["E2E 작성자를 위한 참고사항"]
}
```

#### summary.md
다음 구조로 생성한다:

- **Results** — 전체 집계 테이블
- **1:1 Comparison Table** — PDF 섹션(4.1, 4.2, ...)별로 그룹화한 전체 대조표
  - 모든 항목을 빠짐없이 나열
  - 각 행: #, 요구 testId, 삽입 testId, 상태
- **Summary** — 상태별 건수
- **⚠️ 이름 다른 항목** — 카테고리별 상세 (ToolBox / 컬럼 메뉴 / 동적 변수 차이)
- **🔘 스킵 항목** — 사유 포함
- **aria-busy Bindings** — 바인딩 상태값 목록
- **Known Limitations** — E2E 작성 시 주의사항

## 2. 절대 규칙
- **PDF 원본이 정본**: `parsed-requirements.json`이 아닌 PDF 테이블 기준으로 카운트한다.
- **전수 대조**: 한 건도 빠뜨리지 않는다. 총 건수 = ✅ + ⚠️ + 🔘 이어야 한다.
- **실제 코드 확인 필수**: `grep`으로 실제 삽입 여부를 반드시 확인한다. `result.json`이나 `listing.json`만 믿지 않는다.
- **상수값 추적 필수**: 동적 패턴의 실제 렌더링 값을 확인할 때 상수 정의 파일을 반드시 읽는다.
- **산출물 경로**: `.docs/e2e/{YYYYMMDD}/result.json`, `.docs/e2e/{YYYYMMDD}/summary.md`

## 3. 서브에이전트
`e2e-verifier` 서브에이전트를 사용하여 코드 스캔 및 대조를 수행한다.
