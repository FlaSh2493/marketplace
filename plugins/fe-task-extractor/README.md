# Frontend Task Extractor (fe-task-extractor)

기획서 및 요구사항 문서에서 프론트엔드 작업을 추출하고 Jira 티켓을 생성하는 플러그인입니다.

## 주요 기능
- **프론트엔드 작업 추출**: 문서에서 FE 영역만 식별하여 세분화된 작업 목록 생성
- **마크다운 문서화**: 추출된 작업을 `.docs/task/` 폴더에 저장
- **Jira 연동**: 각 작업을 Jira Story 티켓으로 자동 생성 (Atlassian MCP 필요)

## 명령어
- `/fe-task-extractor:extract`: 요구사항 분석 및 FE 작업 추출 시작
- `/fe-task-extractor:update`: 기존 작업 명세 수정 및 Jira 동기화
- `/fe-task-extractor:fetch`: Jira 이슈를 가져와서 명세서 생성/업데이트

## 설치
`plugins/fe-task-extractor` 폴더를 프로젝트에 포함시키면 Claude Code가 자동으로 인식합니다.
Jira 티켓 생성을 위해 Atlassian MCP 서버가 연결되어 있어야 합니다.
