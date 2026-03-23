# change-impact

**목적**: Jira 티켓 필드 변경을 ignore / warn / halt 세 등급으로 분류한다.

## 분류 기준

### ignore (자동 무시, 로그만 기록)
변경이 개발 작업에 영향 없음.
- `labels` 변경
- `assignee` 변경
- status가 진행 방향으로만 변경 (예: To Do → In Progress → Done)
- `fixVersions` 변경
- `watchers` 변경

### warn (사용자 알림 후 결정 요청)
개발 작업에 영향 가능성 있음.
- `priority` 상향 (Low→Medium, Medium→High 등)
- `linkedIssues` 신규 추가 (의존성 추가)
- `comments`에 요구사항 관련 키워드 포함:
  - 키워드: `변경`, `수정`, `추가`, `제거`, `change`, `update`, `add`, `remove`, `modify`, `revise`
- `dueDate` 단축
- `components` 변경

### halt (즉시 작업 중단, 검토 필수)
요구사항 자체가 변경됨.
- `summary` 변경
- `description` 변경
- `acceptance_criteria` 변경 (description 내 포함 시 포함)
- `subtasks` 추가/삭제
- `linkedIssues` 삭제 (기존 의존성 제거)
- `priority` 최고 등급으로 변경 (→ Critical/Blocker)

## 판별 절차 (CLI, 토큰 0)

```bash
# snapshot.json vs latest.json 필드별 sha256 비교
jq -r '.content_hash | to_entries[] | "\(.key) \(.value)"' snapshot.json > /tmp/snap.txt
# latest.json 각 필드 sha256 계산 후 비교
# 변경된 필드 목록 → 위 분류표에서 등급 결정
```

## 최종 등급 결정

여러 필드가 변경된 경우: **가장 높은 등급 적용**
예: labels(ignore) + description(halt) → **halt**
