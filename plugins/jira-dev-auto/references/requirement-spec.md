# requirement-spec

**목적**: Jira 티켓을 7항목 요구사항 규격으로 변환하고 모호한 항목 질문을 트리거한다.

## 7항목 템플릿

```yaml
ticket: {KEY}
domain: {domain}
version: 1

objective:        # WHY — 비즈니스 목표
  goal: ""
  success_criteria: []

scope:            # WHAT — 포함/제외 범위
  included: []
  excluded: []

technical_spec:   # HOW — 구현 상세
  files: []       # 수정할 파일 경로 목록
  apis: []        # API 엔드포인트 or 함수 시그니처
  models: []      # 데이터 모델/타입
  config: []      # 환경변수, 설정값

constraints:      # GUARD — 비기능 요건
  performance: ""
  security: ""
  compatibility: ""

verification:     # CHECK — 테스트 기준
  unit: []
  integration: []
  edge_cases: []

dependencies:     # LINK — 연관 티켓
  upstream: []    # 이 티켓이 의존하는 것
  downstream: []  # 이 티켓에 의존하는 것

open_questions: [] # ASK — 아직 미결인 항목
```

## 질문 트리거 (open_questions 생성 조건)

1. **수치 미명시** → "재시도 횟수 / 타임아웃 / 임계값은 얼마로 설정할까요?"
2. **구현 방식 2가지 이상** → "A 방식과 B 방식 중 어느 쪽으로 구현할까요?"
3. **범위 경계 모호** → "X 기능은 이번 티켓 범위에 포함되나요?"
4. **파일 공유 충돌** → "{file}을 {KEY-A}와 {KEY-B}가 모두 수정합니다. 우선순위는?"
5. **테스트 수준 미명시** → "유닛만 작성할까요, E2E까지 필요한가요?"

## 변환 규칙

- Jira description의 `Acceptance Criteria` 섹션 → `verification` 항목
- `linkedIssues` (blocks/is blocked by) → `dependencies`
- 수치·기술 선택·범위가 명확하지 않으면 반드시 `open_questions`에 추가
- `open_questions`가 빈 배열이 될 때까지 사용자 질문 루프 반복
