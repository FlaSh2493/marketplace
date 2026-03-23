---
name: fe-task-extractor-fetch
description: Jira에 이미 등록된 이슈들을 가져와서 프론트엔드 작업 명세(.docs/task/ 하위 md 파일)로 생성하거나 업데이트하는 스킬. "지라 이슈 가져와줘", "기존 티켓 불러와", "지라 기준으로 명세서 만들어" 등을 요청할 때 사용한다. Jira의 summary와 description을 파싱하여 FE-XX 형식의 마크다운으로 변환한다.
---

# Frontend Task Fetch (Jira to Markdown)

Jira에 등록된 작업들을 불러와서 표준화된 프론트엔드 작업 명세 형식으로 변환하여 저장하는 스킬이다.

---

## 1. 대상 이슈 식별

사용자에게 다음 중 하나를 요청한다:
- **Project Key**: 해당 프로젝트의 최근 Story 티켓들
- **Epic Key**: 특정 에픽 하위의 모든 Story 티켓들
- **Issue Keys**: 특정 이슈 번호 리스트 (예: PROJ-101, PROJ-102)

---

## 2. 데이터 수집 및 변환

### Step 1: Jira 데이터 조회
Atlassian MCP(`jiraGetIssue` 또는 `jiraGetIssues`)를 사용하여 대상 이슈들의 정보를 가져온다.

### Step 2: 마크다운 변환
Jira 이슈의 필드를 아래와 같이 마크다운 형식으로 매핑한다:

- **작업 제목**: Jira Summary
- **작업 설명**: Jira Description의 서두 (1~2문장)
- **deps**: Description 내의 '선행/후행' 정보 파싱
- **api**: Description 내의 'API' 정보 파싱
- **states**: Description 내의 'UI 상태' 정보 파싱
- **jira**: 해당 이슈의 Key (예: PROJ-101)

넘버링은 `FE-01`, `FE-02` 순으로 새로 부여한다.

---

## 3. 출력 및 저장

### Step 1: 파일 경로 결정
`python3 scripts/init_task_dir.py "{프로젝트키 또는 기능명}"`을 실행하여 저장할 마크다운 파일 경로를 확보한다.

### Step 2: 마크다운 저장
변환된 내용을 표준 포맷에 맞춰 파일로 저장한다. 기존 파일이 있는 경우 덮어쓰거나 사용자에게 확인 후 업데이트한다.

---

## 4. 주의사항

- **포맷 역변환**: Jira Description이 이 플러그인의 표준 형식으로 작성되어 있지 않은 경우, 최대한 핵심 내용을 추출하여 `FE-XX` 형식으로 재구성한다.
- **Story 우선**: 기본적으로 이슈 타입이 `Story`인 것들만 대상으로 한다.
- **이미 있는 파일**: 동일한 이름의 파일이 이미 존재하는 경우, 내용을 병합하거나 최신 Jira 정보로 덮어쓸지 사용자에게 묻는다.
