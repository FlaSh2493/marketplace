---
name: task-sync-fetch
description: Jira에서 나에게 할당된 미완료 이슈를 조회하고 선택하여 Writer 서브에이전트에 문서 작성을 위임하는 스킬. "내 지라 이슈 가져와줘", "지라 불러와", "내 할 일 불러와" 등을 요청할 때 사용한다.
---

# Frontend Task Fetch

**실행 주체: Main Session 전용**
문서 작성 금지. 이슈 선택 후 Writer 서브에이전트에 위임한다.
파일 검증과 상태 전이는 Writer 완료 후 `/task-sync:publish`에서 처리한다.

## 사용법
- `/task-sync:fetch` — Jira 조회 후 [GATE] 선택
- `/task-sync:fetch PROJ-101 PROJ-102` — 이슈 직접 지정 (선택 스킵)

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py fetch`
  성공: data.branch, data.state_dir 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 1: 이슈 목록 확인
  인수가 있으면 → STEP 1-B (선택 스킵)
  인수가 없으면:
    Jira 조회 (Claude MCP):
      JQL: `assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC`
    결과를 번호 테이블로 출력:
    ```
    | 번호 | Jira Key  | 제목                  | 상태        |
    |-----|-----------|-----------------------|------------|
    |  1  | PROJ-101  | 로그인 폼 UI 구현       | To Do      |
    |  2  | PROJ-102  | 목록 페이지 구현        | In Progress |
    ```

  [GATE] STEP 1-A: 이슈 선택
    AskUserQuestion("가져올 이슈 번호를 선택하세요 (예: 1,3 / 전체: all)")
    [LOCK: 응답 전 save_selection.py 실행 금지]
    응답 수신 후 번호를 이슈 키로 변환

STEP 1-B: 선택 저장
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/save_selection.py {branch} {이슈키들}`
  성공: data.selected 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 1-C: 빈 파일 생성 (Bash)
  선택된 각 이슈마다 파일 존재 여부 확인: `.docs/task/{branch}/{이슈키}/{이슈키}.md`

  이미 존재하는 이슈가 있으면:
    출력: "이미 로컬에 있는 이슈: {이슈키 목록}"
    [GATE] AskUserQuestion("덮어쓸 이슈 번호를 선택하세요. (스킵하려면 엔터)")
    선택한 이슈만 덮어쓰기 대상에 포함, 나머지 스킵

  생성 대상 이슈마다:
    실행: `echo "" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create_task_file.py \
      "{branch}" "{이슈키}" "임시제목" --source jira-fetch`
    성공: data.file_path 확인
    실패: reason 그대로 출력 후 [STOP]

STEP 2: Writer 서브에이전트 런칭
  헤드리스 Writer 에이전트 런칭:
    - 에이전트: task-sync:task-sync
    - 프롬프트: `/task-sync:write --branch {branch} {이슈키들 공백 구분}`
  출력:
    "Writer 에이전트 시작됨 ({N}개 이슈)."
    "완료 알림을 받으면 /task-sync:publish 를 실행하세요."

[TERMINATE]
