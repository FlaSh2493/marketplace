---
name: jira-fetch
description: 현재 활성 스프린트에서 본인의 이슈와 댓글을 조회합니다. (프로젝트 자동 감지 및 Direct API 사용)
---

이 스킬은 Jira REST API를 직접 호출하여 현재 활성 스프린트(`openSprints()`)에서 본인(`currentUser()`)에게 할당된 이슈 목록과 댓글을 조회합니다. 다중 프로젝트가 감지될 경우 사용자가 선택할 수 있도록 합니다.

## 사전 조건
- 환경 변수 설정: `JIRA_URL`, `JIRA_USERNAME`, `JIRA_API_TOKEN`
- 설정되지 않은 경우 안내 메시지를 출력하고 종료합니다.

## 작업 (Tasks)

1. **인증 준비** (CLI):
   ```bash
   # JIRA 인증용 Base64 헤더 생성
   JIRA_CREDENTIALS=$(echo -n "${JIRA_USERNAME}:${JIRA_API_TOKEN}" | base64)
   ```

2. **프로젝트 자동 감지** (CLI/curl):
   - JQL: `sprint in openSprints() AND assignee = currentUser()`
   - 현재 본인의 활성 이슈들을 검색하여 고유한 **프로젝트 키 목록**을 추출합니다.
   - **결과 처리**:
     - 프로젝트 **1개** → 자동 선택 및 알림.
      - 프로젝트 **2개 이상** → **선택 UI** 제공 후 사용자에게 선택 요청 (`ask_user`).
        - 예: `[1] PROJ-A`, `[2] PROJ-B`, `[자유 입력] 직접 입력`
        - 번호를 입력하거나 프로젝트 키를 직접 입력할 수 있음을 안내합니다.
     - 프로젝트 **0개** → "현재 활성 스프린트에 할당된 이슈가 없습니다." 안내 후 종료.

3. **기타 조회 옵션** (필요시):
   - 특정 보드(Board) 정보가 필요한 경우, 선택된 프로젝트의 Kanban 보드 목록을 조회하여 필터링할 수 있습니다.

4. **상세 이슈 및 댓글 조회** (CLI/curl):
   - 선택된 프로젝트에 대해 JQL 실행: `project = "{PROJECT_KEY}" AND sprint in openSprints() AND assignee = currentUser()`
   - 파라미터: `fields=key,summary,description,comment`
   - API 호출:
     ```bash
     curl -s \
       -H "Authorization: Basic ${JIRA_CREDENTIALS}" \
       -H "Content-Type: application/json" \
       "${JIRA_URL}/rest/api/3/search?jql=project%3D%22${PROJECT_KEY}%22%20AND%20sprint%20in%20openSprints()%20AND%20assignee%3DcurrentUser()&fields=key,summary,description,comment"
     ```

5. **출력 및 캐시** (CLI):
   - 터미널에 다음 정보를 출력합니다:
     - **이슈 키 및 제목**
     - **현재 상태**
     - **댓글 내역**: 각 이슈에 달린 모든 댓글의 작성자와 내용을 요약 표시합니다.
   - 결과를 `.docs/work/{workspace}/_cache/issue-list.json`에 저장합니다.

## 핵심 규칙
- **Direct API**: 모든 요청은 `curl` 또는 `fetch`를 이용한 직접 HTTP 호출 방식을 사용합니다.
- **프로젝트 선택**: 여러 프로젝트에 걸쳐 이슈가 있을 경우 반드시 사용자의 확인을 거칩니다.
- **댓글 우선**: 단순히 이슈 목록만 가져오는 것이 아니라, 대화 흐름 파악을 위해 `comment` 데이터를 반드시 함께 확보합니다.
