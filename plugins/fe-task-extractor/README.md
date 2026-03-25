# Frontend Task Extractor (fe-task-extractor)

기획서·요구사항 문서에서 **프론트엔드 작업(FE Task)만 추출**하거나 **Jira 이슈를 로컬 문서로 가져와** 작업 명세를 관리하는 플러그인입니다.

생성된 작업 명세는 `worktree-flow` 플러그인의 `/worktree-flow:plan` 스킬에서 이슈 컨텍스트로 활용됩니다.

## 주요 기능

- **FE 전용 작업 추출**: 기획서에서 BE/디자인/기획 작업을 제외하고 FE 영역만 식별하여 세분화합니다.
- **Jira 이슈 로컬화**: Jira에 이미 생성된 이슈를 로컬 마크다운 문서로 가져옵니다.
- **Jira Story 자동 생성**: 로컬 문서를 검증하고 Atlassian MCP를 통해 Jira Story로 등록합니다.
- **양방향 동기화**: 로컬 문서 수정 내용을 Jira 이슈에 반영합니다.

## 워크플로우

### A. 기획서에서 신규 생성

```
/fe-task-extractor:init      # 작업 디렉토리 초기화
→ (기획서 제공 후)
/fe-task-extractor:extract   # FE 작업 추출 및 로컬 문서 생성
→ /fe-task-extractor:publish # 로컬 문서 검증 후 Jira Story 생성
```

### B. Jira 이슈를 로컬로 가져오기

```
/fe-task-extractor:fetch     # 내 Jira 이슈 조회 및 선택 → Writer 에이전트가 로컬 문서 작성
→ /worktree-flow:plan {이슈키}  # 워크트리 생성 및 구현 시작
```

## 명령어

| 명령어 | 실행 주체 | 설명 |
|--------|----------|------|
| `/fe-task-extractor:init` | Main Session | 현재 브랜치 기반으로 작업 디렉토리 초기화 |
| `/fe-task-extractor:extract` | Writer 에이전트 | 기획서에서 FE 작업 추출 및 로컬 문서 생성 |
| `/fe-task-extractor:fetch` | Main Session | Jira 이슈 조회·선택 후 Writer 에이전트에 문서 작성 위임 |
| `/fe-task-extractor:write` | Writer 에이전트 | fetch에서 선택된 Jira 이슈를 로컬 마크다운으로 변환 |
| `/fe-task-extractor:publish` | Main Session | 로컬 문서 검증 후 Jira Story 생성 및 파일명 동기화 |
| `/fe-task-extractor:update` | Writer 에이전트 | 로컬 수정 내용을 Jira 이슈에 반영 |

## 주의사항

- **Atlassian MCP**: Jira 연동 기능 사용 시 Atlassian MCP 서버가 연동되어 있어야 합니다.
- **SSOT**: 모든 명세는 `templates/fe-task-template.md` 포맷을 준수해야 합니다. 필드 순서 변경 시 스크립트가 오동작할 수 있습니다.
- **스크립트 경유**: 디렉토리 초기화·키 업데이트는 `scripts/` 내 Python 스크립트를 통해 수행합니다.
- **저장 경로**: 모든 태스크 명세는 `.docs/task/{브랜치명}/`에 저장됩니다.
