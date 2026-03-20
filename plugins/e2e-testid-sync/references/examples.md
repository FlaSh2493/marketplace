# E2E Test-ID Injection Examples

## 1. 파싱 성공 (Parsed -> Actionable)

**요구사항 (requirements.md):**
- 로그인 화면의 '접속하기' 버튼에 `btn-signin` 추가

**코드 (src/pages/Login.tsx):**
```tsx
42: <button onClick={handleLogin}>접속하기</button>
```

**ListingItem:**
```json
{
  "id": "LST-001",
  "dataTestId": "btn-signin",
  "oldStr": "<button onClick={handleLogin}>접속하기</button>",
  "newStr": "<button onClick={handleLogin} data-testid=\"btn-signin\">접속하기</button>",
  "status": "actionable"
}
```

## 2. 애매한 상황 (Ambiguous)

**상황**: 동일한 버튼이 반복문 내에 존재하거나 다수 발견될 때

**요구사항**: '삭제' 버튼에 `btn-delete` 추가

**코드:**
```tsx
15: <button className="del">삭제</button>
28: <button className="del">삭제</button>
```

**리스팅 에이전트 생성 질문:**
```json
{
  "questions": [
    {
      "type": "single_select",
      "message": "src/components/List.tsx 내에 '삭제' 버튼이 2개 있습니다. 어떤 것에 id를 부여할까요?",
      "options": ["15라인 버튼", "28라인 버튼", "둘 다 (단일 ID 중복 위험)", "스킵"]
    }
  ]
}
```

## 3. aria-busy 바인딩 추론

**요구사항**: 사용자 목록 리스트에 로딩 상태 반영

**코드 탐색 결과**: `const { users, loading } = useUsers();` 발견

**TO-BE**:
```tsx
<ul data-testid="list-users" aria-busy={loading}>
```
