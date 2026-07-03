---
key: ""
key_source: issue
skill: plan
summary: ""
branch: ""
repo: ""
status: completed
created: ""
updated: ""
tags: []
phases_count: 0
---

# Plan — {KEY}

## 배경

{task.md 배경 섹션}

## 목표

{task.md 목표 섹션}

## 요구사항

- [ ] R1: {원자 단위 요구사항}
- [ ] R2: {원자 단위 요구사항}
- [ ] R3: {암묵 요구사항 — 엣지케이스/에러 처리/빈·로딩 상태 등}

### 미지수

- {불명확하거나 가정이 필요한 항목. 없으면 이 하위 섹션 생략}

## 영향 범위

| 파일 | 변경 유형 | 비고 |
|------|----------|------|
| `path/to/file.ts` | 수정 | |

## 아키텍처 / 기술 설계

- **흐름**: {예: `Page → useXxx hook → api/client → server`}
- **모듈 경계**: {어디서 무엇을 책임지는지}
- **기술 선택**: {도입/변경 기술 — because {이유}}
- **재사용**: `path/to/existing-util.ts` 의 `fn()` 활용 (새로 만들지 않음)

## 구현 계획

### Phase 1: {제목}

<!-- delegate: auto -->

- [ ] {작업 항목} (R1, R2)
- [ ] {작업 항목} (R3)

**생성/수정 파일**:

```
src/feature/
├── index.ts          (new)
└── Foo.tsx           (수정)
```

**샘플 코드**:

```ts
// src/feature/index.ts — 골격 (시그니처·핵심 로직 위주)
export function foo(input: Input): Output {
  // ...
}
```

### Phase 2: {제목}

<!-- delegate: auto -->

- [ ] {작업 항목} (R2)

**생성/수정 파일**:

```
src/other.ts          (수정)
```

**샘플 코드**:

```ts
// src/other.ts — 변경 골격
```

## 검증 방법

| 요구사항 | 검증 방법 | 도구/명령 |
|----------|----------|-----------|
| R1 | {무엇을 어떻게 확인} | `npm test path` |
| R2 | {수동 확인 절차} | 수동 |
| R3 | lint/type/test 통과 | check 스킬 |

## 완료 조건

{task.md 완료 조건 섹션}
