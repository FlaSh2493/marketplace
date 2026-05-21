---
name: jsync-fetch
description: Jira 이슈를 로컬 디스크에 저장합니다. 프로젝트 키를 주면 활성 스프린트 × 본인 할당 전체를, 이슈 키를 주면 해당 이슈를 직접 가져옵니다. 저장 위치는 ~/Documents/jsync/<KEY>/task.md 입니다.
---

사용자가 이슈 fetch 또는 로컬 저장을 요청하면 아래 명령을 실행한다.

```
cd <plugin-root>/scripts && python fetch.py <ARGS>
```

## 인자 규칙

| 입력 예 | 설명 |
|--------|------|
| `MKT` | 프로젝트: 활성 스프린트 × 본인 할당 전체 |
| `MKT,ADX` | 다중 프로젝트 (콤마) |
| `MKT-142` | 이슈 키 직접 지정 (스프린트 제약 없음) |
| `MKT-142,ADX-77` | 다중 이슈 키 |
| `MKT --jql "status != Done"` | 추가 JQL 필터 (프로젝트 모드 전용) |

## 결과 처리

- 스크립트 stdout(1줄 요약)을 사용자에게 보여준다.
- **raw.json, meta.json은 절대 Read하지 않는다.** 스크립트 전용 파일이다.
- task.md는 사용자가 IDE에서 직접 열어 편집한다. 에이전트가 기본으로 읽을 필요 없다.
- 편집 후 반영은 `/jsync:update <KEY>`.
