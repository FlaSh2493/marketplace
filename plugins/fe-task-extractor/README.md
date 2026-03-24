# Frontend Task Extractor (fe-task-extractor)

기획서 및 요구사항 문서에서 **프론트엔드 작업(FE Task)만 정교하게 추출**하여 작업 명세를 생성하고 Jira 티켓을 자동화하는 플러그인입니다.

여기서 생성된 작업 명세는 `worktree-flow` 플러그인의 **컨텍스트 로딩(`:start`) 및 AI 기반 커밋 정리의 핵심 기반 데이터**로 활용됩니다.

## 주요 기능
- **FE 전용 작업 추출**: 문서 내 백엔드/디자인 작업과 분리하여 FE 영역만 식별 및 세분화
- **작업 명세 자동화**: 추출된 결과를 `.docs/task/` 폴더에 마크다운 파일로 저장
- **Jira Story 자동 생성**: Atlassian MCP를 연동하여 추출된 각 태스크를 Jira Story로 즉시 등록
- **Key 동기화**: 생성된 Jira Key를 로컬 마크다운 문서와 자동으로 동기화

## 워크플로우 (Workflow)
1. **요구사항 분석**: 기획서나 텍스트를 입력으로 제공
2. **명세서 생성**: `/fe-task-extractor:extract` 명령으로 `.docs/task/` 하위에 태스크 파일 생성
3. **Jira 등록**: 사용자 승인 후 각 태스크를 Jira Story로 등록 (담당자는 자동 본인 지정)
4. **작업 시작**: `worktree-flow` 플러그인을 사용하여 생성된 태스크 단위로 워크트리 구성 및 개발 시작

## 명령어
- `/fe-task-extractor:init`: 기능명을 기반으로 작업 디렉토리 및 파일 초기화
- `/fe-task-extractor:extract`: 요구사항 문서에서 FE 태스크를 분석 및 추출
- `/fe-task-extractor:fetch`: 이미 생성된 Jira 이슈들을 가져와 로컬 명세서 생성
- `/fe-task-extractor:update`: 작업 명세 수정 사항을 로컬과 Jira에 동시 반영

## 주의사항
- **Atlassian MCP**: Jira 티켓 생성을 위해 반드시 Atlassian MCP 서버가 연동되어 있어야 합니다.
- **저장 경로**: 모든 태스크 명세는 프로젝트 루트의 `.docs/task/` 폴더에 저장됩니다.
