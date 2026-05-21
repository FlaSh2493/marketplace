# PR 제목 생성 가이드

형식: `{type}({scope}): {subject}`

## 규칙

- `type`: feat | fix | refactor | chore | docs | style | test | perf
- `scope`: 주요 변경 영역 (optional, 한 단어)
- `subject`: 명령형 동사로 시작, 현재 시제, 소문자, 마침표 없음
- 전체 72자 이내

## 예시

```
feat(auth): add OAuth2 login flow
fix(report): correct date range filter logic
refactor(api): extract pagination helper
```

이슈 키가 있으면 subject 끝에 추가:
```
feat(filter): add date range picker for report [PLAT-101]
```
