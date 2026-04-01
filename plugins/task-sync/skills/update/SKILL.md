---
name: task-sync-update
description: Writer 서브에이전트 전용. 로컬에서 수정된 마크다운 파일의 내용을 Jira 이슈에 동기화한다.
---

# Frontend Task Update

**실행 주체: Writer 에이전트 전용**
마크다운 → Jira 단방향 동기화. 요약·해석 없이 원문 그대로 반영한다.

## 사용법
`/task-sync:update`

## 실행 절차

STEP 0: 대상 파일 탐색 (Glob 도구)
  Glob: `.docs/task/{branch}/.state/*.published`
  결과가 없으면:
    출력: "PUBLISHED 상태인 이슈가 없습니다. publish를 먼저 실행하세요."
    [STOP]
  이슈 키 목록 추출 (파일명에서 `.published` 제거)

STEP 1: 목록 출력
  번호 테이블로 출력:
  ```
  | 번호 | Jira Key  | 작업 제목        |
  |-----|-----------|----------------|
  |  1  | PROJ-101  | 로그인 폼 UI    |
  |  2  | PROJ-102  | 목록 페이지 구현 |
  ```
  (각 파일 Read하여 # 헤더에서 제목 파악)

[GATE] STEP 2: 동기화 대상 선택
  AskUserQuestion("동기화할 이슈 번호를 선택하세요 (예: 1,3 / 전체: all)")
  [LOCK: 응답 전 jira_update.py 절대 실행 금지]

STEP 3: 변경 내용 분석 (Read 도구)
  선택된 각 파일 Read:
  - 작업 제목 (# 헤더에서)
  - ## 설명 섹션 원문 전체
  - ## 추가 요구사항 섹션 (있는 경우)
  - ## 첨부 이미지 섹션 (있는 경우) — assets/ 이미지 포함
  - deps, api, states 필드

  변경 예정 목록 출력:
  ```
  | Jira Key  | 동기화 내용          |
  |-----------|-------------------|
  | PROJ-101  | 설명, deps, 이미지 2장 |
  ```

[GATE] STEP 4: 동기화 확인
  AskUserQuestion("위 내용을 Jira에 반영할까요?")
  [LOCK: 응답 전 jira_update.py 절대 실행 금지]
  응답 "no": [TERMINATE]

STEP 5: Jira 업데이트 (Bash 스크립트)
  각 이슈마다:

  5-1. 마크다운 → ADF 변환
    md_file_path는 절대경로로 구성한다: `$(pwd)/.docs/task/{branch}/{이슈키}/{이슈키}.md`
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/md_to_adf.py {jira_key} "$(pwd)/.docs/task/{branch}/{이슈키}/{이슈키}.md" > /tmp/{이슈키}_adf.json`
    성공: /tmp/{이슈키}_adf.json 저장 확인
    실패: reason 그대로 출력 후 다음 이슈 계속

  5-2. Jira 업데이트
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jira_update.py {이슈키} --summary "{작업 제목}" --adf-file /tmp/{이슈키}_adf.json`
    성공: {"ok": true}
    실패: reason 그대로 출력 후 다음 이슈 계속

STEP 6: 완료 알림
  notify_user("Jira 동기화 완료 [{이슈키 목록}]")

[TERMINATE]
댓글 역동기화 금지. ## 설명 + ## 추가 요구사항 + ## 첨부 이미지 섹션을 Jira에 반영한다.
