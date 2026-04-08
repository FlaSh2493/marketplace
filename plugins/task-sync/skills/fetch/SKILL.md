---
name: task-sync-fetch
description: Jira에서 나에게 할당된 미완료 이슈를 조회하고 선택하여 Writer 서브에이전트에 문서 작성을 위임하는 스킬. "내 지라 이슈 가져와줘", "지라 불러와", "내 할 일 불러와" 등을 요청할 때 사용한다.
---

# Frontend Task Fetch

**실행 주체: Main Session 전용**
문서 작성 금지. 이슈 선택 후 Writer 서브에이전트에 위임한다.

## 사용법
- `/task-sync:fetch` — Jira 조회 후 선택
- `/task-sync:fetch PROJ-101 PROJ-102` — 이슈 직접 지정 (선택 스킵)

## 실행 절차

STEP 0: 전제조건 검증
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py fetch`
  exit 0 → data(branch, task_dir, state_dir) 보관
  exit 1 → reason 출력, [STOP]

STEP 1: 이슈 목록 확인
  인수 있으면 → STEP 1-B로.
  인수 없으면:
    `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jira_fetch.py --search --format table --out-dir {state_dir}`
    exit 0 → JSON 응답의 table을 그대로 사용자에게 출력, mapping 보관
    exit 1 → reason 그대로 출력(안내 메시지 포함), [STOP]

  [GATE] STEP 1-A: 이슈 선택
    AskUserQuestion("가져올 이슈 번호를 선택하세요 (예: 1,3 / 전체: all)")
    [LOCK: 응답 전 save_selection.py 실행 금지]
    mapping으로 번호 → 이슈 키 변환

STEP 1-B: 선택 저장
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/save_selection.py {branch} {이슈키들}`
  exit 0 → data.selected 보관. exit 1 → reason 출력, [STOP]

STEP 1-C: 빈 파일 생성
  각 이슈: `.docs/task/{branch}/{이슈키}/{이슈키}.md` 존재 여부 확인
  이미 존재하면:
    [GATE] AskUserQuestion("이미 있는 이슈: {목록}. 덮어쓸 번호 선택 (스킵: 엔터)")
    선택된 이슈만 덮어쓰기 대상
  생성 대상마다:
    `echo "" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create_task_file.py "{branch}" "{이슈키}" "임시제목" --source jira-fetch`
    exit 1 → reason 출력, [STOP]

STEP 2: write 스킬 실행
  Skill 도구: `/task-sync:write --branch {branch} {이슈키들 공백 구분}`
  출력: "문서 작성 완료 [{이슈키 목록}]"

[TERMINATE]
