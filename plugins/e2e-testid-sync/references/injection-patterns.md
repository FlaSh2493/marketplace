# Injection Patterns Reference

React(TSX/JSX) 요소에 `data-testid` 및 `aria-busy`를 삽입할 때의 표준 패턴입니다.

## 1. 기본 삽입 (data-testid)

### 버튼 및 일반 요소
**AS-IS:**
```tsx
<button type="submit" className="btn-primary">
```
**TO-BE:**
```tsx
<button type="submit" className="btn-primary" data-testid="btn-login-submit">
```

### Self-closing 요소
**AS-IS:**
```tsx
<input type="text" className="search" />
```
**TO-BE:**
```tsx
<input type="text" className="search" data-testid="input-global-search" />
```

## 2. 상태 바인딩 (aria-busy)

`aria-busy`는 해당 요소가 로딩 중일 때 테스트 에이전트가 대기할 수 있도록 돕습니다.

**AS-IS:**
```tsx
<div className="table-wrapper">
```
**TO-BE (isLoading 상태가 존재하는 경우):**
```tsx
<div className="table-wrapper" data-testid="tbl-main-data" aria-busy={isLoading}>
```

## 3. 주의사항

### 중복 방지
- 동일한 `data-testid`가 한 페이지 내에 존재하지 않도록 합니다.
- 리스팅 단계에서 `grep`을 통해 이미 존재하는 ID를 확인해야 합니다.

### 유일한 문자열 (Unique old_str)
- `str_replace`를 사용할 때 `old_str`이 유일해야 합니다.
- 만약 동일한 태그가 여러 번 등장한다면, 부모 요소나 주변 속성을 추가로 포함하여 `old_str`을 구성합니다.

### 라인 밀림 방지
- 한 파일에 여러 속성을 주입할 때는 반드시 **코드 하단에서 상단 방향(역순)**으로 작업을 진행합니다.
- 삽입 전후에 `view`를 통해 정확한 라인과 내용을 대조합니다.
