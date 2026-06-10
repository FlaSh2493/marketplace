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

## 이미지·첨부파일

- 이슈의 **모든 첨부파일**을 `<KEY>/attachments/`에 다운로드한다.
- 본문에 박힌 이미지는 task.md에서 `![파일명](attachments/파일명)`으로 렌더링되어 IDE에서 바로 볼 수 있다.
- 이미지가 아닌 첨부(PDF·문서 등)는 `## Attachments` 섹션에 로컬 링크로 나열된다.
- 원본 이미지 ADF 노드는 `meta.json`의 `media_refs`에 보존되어, update 시 Jira에서 이미지가 그대로 유지된다.
- 파일명이 겹치면 `<id>_<파일명>`으로 저장해 충돌을 피한다.

## 결과 처리

- 스크립트 stdout(1줄 요약)을 사용자에게 보여준다.
- **raw.json, meta.json은 절대 Read하지 않는다.** 스크립트 전용 파일이다.
- task.md는 사용자가 IDE에서 직접 열어 편집한다. 에이전트가 기본으로 읽을 필요 없다.
- 편집 후 반영은 `/jsync:update <KEY>`.
