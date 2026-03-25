---
name: init
description: 현재 브랜치 기반으로 작업 명세 디렉토리를 초기화하는 스킬. "태스크 초기화", "폴더 만들어줘" 등을 요청할 때 사용한다.
---

# Frontend Task Init

**실행 주체: Main Session 전용**

## 사용법
`/fe-task-extractor:init`

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py init`
  성공: data.branch, data.task_dir 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 1: 디렉토리 생성
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_task_dir.py "{branch}"`
  성공: data.dir 경로 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 2: 결과 보고
  아래 형식으로 출력:
  ```
  ✅ 초기화 완료
  브랜치: {branch}
  경로:   .docs/task/{branch}/
  ```
  다음 단계 안내:
  - 기획서에서 추출: `/fe-task-extractor:extract`
  - Jira에서 가져오기: `/fe-task-extractor:fetch`

[TERMINATE]
