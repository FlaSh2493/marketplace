# commit-convention

**목적**: Conventional Commits 규칙에 Jira 키를 연결하는 커밋 메시지 형식을 정의한다.

## 기본 형식

```
{type}({scope}): {description} [{KEY}]

[optional body]

[optional footer]
```

## 타입 목록

| type | 사용 상황 |
|---|---|
| `feat` | 새 기능 추가 |
| `fix` | 버그 수정 |
| `refactor` | 기능 변경 없는 코드 개선 |
| `test` | 테스트 추가/수정 |
| `chore` | 빌드, 패키지, 설정 변경 |
| `docs` | 문서 변경만 |
| `style` | 포맷, 세미콜론 등 |
| `perf` | 성능 개선 |
| `ci` | CI/CD 설정 변경 |

## scope

도메인명 또는 수정한 모듈명 사용.
예: `auth`, `payment`, `api`, `user`

## 규칙

1. `description`: 영어 소문자, 명령형, 끝에 마침표 없음
2. `{KEY}`: 반드시 포함 — `[PROJ-123]`
3. 제목 전체 72자 이내
4. body: 변경 이유, 접근 방식 (선택)
5. footer: `Closes PROJ-123` (병합 커밋에만)

## 예시

```
feat(auth): add refresh token rotation [PROJ-123]

Implement sliding window refresh token strategy to improve
security without disrupting user sessions.
```

```
fix(payment): handle timeout on retry request [PROJ-456]
```

```
merge: PROJ-456 payment retry feature

Closes PROJ-456
```
