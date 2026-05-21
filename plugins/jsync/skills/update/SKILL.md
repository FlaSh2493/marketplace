---
name: jsync-update
description: 로컬에서 편집한 task.md를 Jira에 반영합니다. ~/Documents/jsync/<KEY>/task.md를 수정한 후 실행하면 변경된 필드만 PUT합니다. "Jira에 반영해줘", "업데이트해줘", "task.md 저장했어" 같은 요청에 자동 실행됩니다.
---

사용자가 task.md 수정 후 Jira 반영을 요청하면 아래 명령을 실행한다.

```
cd <plugin-root>/scripts && python update.py <KEY>
```

## 동작 규칙

- 단건만 지원. `KEY`는 `MKT-142` 형태.
- 스크립트가 내부적으로 diff를 수행하고 변경된 필드만 PUT한다.
- **raw.json, meta.json을 직접 Read하지 않는다.**
- 성공 시 stdout 1줄: `updated MKT-142: summary, labels (2 changed)`
- 변경 없으면: `no changes  MKT-142`
- 실패 시 1줄 에러 + 상세 로그는 `~/Documents/jsync/<KEY>/.log`

## 특수 필드 처리

- `status` 변경 → `/transitions` 자동 호출
- `## New Comment` 섹션에 내용 있으면 → 댓글 POST 후 섹션 초기화
- `add_worklog` 채워져 있으면 → worklog POST 후 초기화
- `links` 변경 → 추가/삭제 자동 처리
