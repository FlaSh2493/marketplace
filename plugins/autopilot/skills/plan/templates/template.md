# {제목}

**Date**: {YYYY-MM-DD}  
**Issue**: {Issue Key}
**Scope**: {1줄 요약}

## 배경
> 이슈의 "배경(Why)" 섹션을 1-2문장으로 압축.

## 목표
- 이 plan으로 달성할 것 (불릿 2-4개)

## 현재 상태
> 탐색한 5-10개 파일을 3-5문장으로 압축.

{현재 구조를 산문 3-5문장으로}

**핵심 파일**: `path/to/a.ts`, `path/to/b.ts`

## 접근 방식

**선택**: {방식 A}
- 영향 범위: {파일 N개, 변경 성격}
- 트레이드오프: {리스크/복잡도/성능}

**기각**: {방식 B}
- 이유: {...}

## Phase 의존성

```
Phase 1 ─┬─► Phase 3
Phase 2 ─┘
```

> 실제 의존 관계에 맞게 작성. 형식: `Phase N ──► Phase M` (화살표 표기 고정).

## 단계

### Phase 1: {제목}

| meta | value |
|------|-------|
| depends_on | [] |
| scope | medium |
| output_shape | interface |

- **대상 파일**: `path/to/a.ts`, `path/to/b.ts`

1. **{작업명 1}**
   - 변경: {Before → After. 예: "`fetchUser()`가 `Promise<User>` 반환 → `Result<User, Err>` 반환"}
   - 검증: {이 단계의 빠른 확인. 예: "타입체크 통과, 빌드 성공"}

2. **{작업명 2}**
   - 변경: {Before → After}
   - 검증: {빠른 확인}

### Phase 2: {제목}

| meta | value |
|------|-------|
| depends_on | [Phase 1] |
| scope | small |
| output_shape | detail |

- **대상 파일**: `path/to/c.ts`

1. **{작업명}**
   - 변경: {Before → After}
   - 검증: {빠른 확인}

## 테스트
> 단계의 "검증"은 빌드·타입체크 수준의 빠른 확인. 이 섹션은 신규 테스트 코드 작성 계획.

- 신규: {테스트 파일/케이스}
- 기존 영향: {깨질 수 있는 테스트 및 확인 방안}

## 리스크
- {리스크 1} → mitigation: {...}
- {리스크 2} → mitigation: {...}

## Out of Scope
- 이번에 안 하는 것 (불릿)

## Build 제약
- 출력 형식: 코드만 출력. 설명 금지. 변경 파일은 전체 내용을 출력한다.
- 범위 이탈 금지: 계획에 없는 리팩토링·import 정리·시그니처 변경·주석 추가를 하지 않는다.
