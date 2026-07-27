---
summary: ""
branch: ""
repo: ""
status: completed
updated: ""
phases_count: 0
---

# Plan — {KEY}

## 요구사항

- [ ] R1: {원자 단위 요구사항}
- [ ] R2: {원자 단위 요구사항}
- [ ] R3: {암묵 요구사항 — 엣지케이스/에러 처리/빈·로딩 상태 등}

### 미지수

- {불명확하거나 가정이 필요한 항목. 없으면 이 하위 섹션 생략}

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

### Phase 2: {제목}

<!-- delegate: auto -->

- [ ] {작업 항목} (R2)

**생성/수정 파일**:

```
src/other.ts          (수정)
```

## 검증 방법

| 요구사항 | 검증 방법 | 도구/명령 |
|----------|----------|-----------|
| R1 | {무엇을 어떻게 확인} | `npm test path` |
| R2 | {수동 확인 절차} | 수동 |
| R3 | lint/type/test 통과 | check |
