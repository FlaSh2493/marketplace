---
name: jira-fetch
description: MCP(Atlassian)으로 Jira 티켓을 조회하고 로컬 캐시에 저장합니다.
---

이 스킬은 Jira에서 티켓 목록을 가져와 로컬 캐시에 저장하고, 사용자가 작업할 티켓을 선택하도록 합니다.

## 사전 조건
- `jira-init` 완료 (워크스페이스 경로 확인)
- `.claude/settings.yaml`의 `jira.project_key` 또는 `jira.default_jql` 설정

## 작업 (Tasks)

1. **JQL 구성**: `settings.yaml`의 `jira.default_jql` 사용.
   - 미설정 시 기본값: `assignee = currentUser() AND status != Done ORDER BY priority DESC`

2. **MCP 조회** (Atlassian MCP):
   - `mcp__atlassian__jira_search` 로 이슈 목록 조회
   - 필드: `key, summary, status, priority, assignee, labels, components`

3. **목록 캐시 저장** (CLI):
   ```bash
   # .docs/{workspace}/_cache/issue-list.json 에 저장
   ```

4. **티켓 선택** (ask_user):
   - 조회된 티켓 목록을 번호와 함께 나열
   - "작업할 티켓을 선택하세요 (번호 또는 키, 다중 선택 가능):"

5. **상세 조회** (Atlassian MCP, 선택된 티켓만):
   - `mcp__atlassian__jira_get_issue` 로 각 티켓 상세 조회
   - 필드: `summary, description, status, priority, assignee, labels, components, linkedIssues, subtasks, comments`

6. **스냅샷 생성** (CLI, 각 티켓):
   ```bash
   # 필드별 sha256 해시 생성
   # .docs/{workspace}/_cache/{KEY}.snapshot.json 저장
   ```
   스냅샷 구조:
   ```json
   {
     "ticket_key": "PROJ-123",
     "fetched_at": "<ISO8601>",
     "pinned_at": null,
     "content_hash": {
       "summary": "<sha256>",
       "description": "<sha256>",
       "comments_digest": "<sha256>",
       "priority": "<sha256>",
       "status": "<sha256>"
     },
     "data": { }
   }
   ```

7. **_index.yaml 갱신** (CLI): 선택된 티켓 키 목록 추가

## 출력
- `.docs/{workspace}/_cache/issue-list.json`
- `.docs/{workspace}/_cache/{KEY}.snapshot.json` (선택된 티켓 수만큼)
- `.docs/{workspace}/_index.yaml` (tickets 배열 갱신)

## 다음 단계
티켓 선택 완료 후 `jira-analyze` 스킬로 도메인 분류를 진행한다.
