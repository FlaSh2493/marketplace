---
name: task-sync-write
description: Writer 서브에이전트 전용. fetch에서 선택된 Jira 이슈를 원본 그대로 로컬 문서로 변환한다.
---

# Frontend Task Write

**실행 주체: Writer 에이전트 전용**
내용 요약·해석·추가 절대 금지. Jira 원본을 마크다운으로 변환하여 그대로 저장한다.

## 사용법
`/task-sync:write --branch {branch} {이슈키} [{이슈키}...]`

## 실행 절차

STEP 0: 전제조건 검증
  인수에서 `--branch {값}` 파싱 → branch 변수 보관
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py write {이슈키들}`
  exit 0 → data(branch, task_dir, state_dir, issues) 보관
  exit 1 → reason 출력, [STOP]. 우회 금지.

  CLAUDE_PLUGIN_ROOT 값 확보: `echo $CLAUDE_PLUGIN_ROOT`
  (서브 에이전트에 명시적으로 전달하기 위해 보관)

## 이슈 수 분기

이슈가 **1개**이면 → [STEP 1 단일] 실행
이슈가 **2개 이상**이면 → [STEP 1 병렬] 실행

---

## STEP 1 단일 (이슈 1개일 때)

  1-1. Jira 상세 조회
    `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jira_fetch.py {이슈키} --out-dir {state_dir}`
    exit 0 → 다음. exit 1 → 해당 이슈 [SKIP].

  1-2. 마크다운 변환
    `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jira_to_md.py {state_dir}/{이슈키}_raw.json --issue-key {이슈키} --out-dir {state_dir}`
    exit 0 → 다음. exit 1 → 해당 이슈 [SKIP].

  1-3. 첨부파일 다운로드
    assets_dir: `.docs/task/{branch}/{이슈키}/assets/`
    `mkdir -p {assets_dir}`
    Bash로 `cat {state_dir}/{이슈키}_converted.json | python3 -c "import sys,json; [print(a['localName'],a['url'],a['size']) for a in json.load(sys.stdin).get('attachments',[])]"` 실행하여 목록 추출.
    각 항목:
      size > 52428800 → "⚠ 50MB 초과 — 스킵", 건너뜀
      `curl -sL -f -u "$JIRA_USERNAME:$JIRA_API_TOKEN" -o "{assets_dir}/{localName}" "{url}"`
      exit ≠ 0 → "⚠ 다운로드 실패 — 스킵", 건너뜀

  1-4. 파일 조립 (Bash — assemble_md.py)
    md_path: `.docs/task/{branch}/{이슈키}/{이슈키}.md`
    `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/assemble_md.py {state_dir}/{이슈키}_converted.json {md_path} --issue-key {이슈키} --assets-dir {assets_dir}`
    exit 0 → 다음. exit 1 → 해당 이슈 [SKIP].

  1-5. 완료 마커
    Write: `.docs/task/{branch}/.state/{이슈키}.published`
    내용: `{"issue": "{이슈키}", "written_at": "{현재시각}"}`

→ STEP 2로 이동.

---

## STEP 1 병렬 (이슈 2개 이상일 때)

각 이슈마다 Agent 도구로 서브 에이전트를 **한 메시지에 동시 생성**한다.

각 서브 에이전트 프롬프트에 아래 컨텍스트를 명시적으로 포함한다:
- CLAUDE_PLUGIN_ROOT: `{STEP 0에서 확보한 값}`
- branch: `{branch}`
- state_dir: `{state_dir}`
- task_dir: `{task_dir}`
- 처리할 이슈키: `{이슈키}` (1개)
- JIRA_USERNAME, JIRA_API_TOKEN 환경변수를 사용한다는 안내

각 서브 에이전트가 수행하는 작업 (preflight 생략):

  1-1. Jira 상세 조회
    `python3 {CLAUDE_PLUGIN_ROOT}/scripts/jira_fetch.py {이슈키} --out-dir {state_dir}`
    exit 0 → 다음. exit 1 → {"issue": "{이슈키}", "status": "skip", "reason": "jira_fetch 실패"} 반환.

  1-2. 마크다운 변환
    `python3 {CLAUDE_PLUGIN_ROOT}/scripts/jira_to_md.py {state_dir}/{이슈키}_raw.json --issue-key {이슈키} --out-dir {state_dir}`
    exit 0 → 다음. exit 1 → {"issue": "{이슈키}", "status": "skip", "reason": "jira_to_md 실패"} 반환.

  1-3. 첨부파일 다운로드
    assets_dir: `{task_dir}/{이슈키}/assets/`
    `mkdir -p {assets_dir}`
    Bash로 `cat {state_dir}/{이슈키}_converted.json | python3 -c "import sys,json; [print(a['localName'],a['url'],a['size']) for a in json.load(sys.stdin).get('attachments',[])]"` 실행하여 목록 추출.
    각 항목:
      size > 52428800 → "⚠ 50MB 초과 — 스킵", 건너뜀
      `curl -sL -f -u "$JIRA_USERNAME:$JIRA_API_TOKEN" -o "{assets_dir}/{localName}" "{url}"`
      exit ≠ 0 → "⚠ 다운로드 실패 — 스킵", 건너뜀
    (첨부파일 실패는 이슈 전체 SKIP 사유가 아님. 계속 진행.)

  1-4. 파일 조립
    md_path: `{task_dir}/{이슈키}/{이슈키}.md`
    `python3 {CLAUDE_PLUGIN_ROOT}/scripts/assemble_md.py {state_dir}/{이슈키}_converted.json {md_path} --issue-key {이슈키} --assets-dir {assets_dir}`
    exit 0 → 다음. exit 1 → {"issue": "{이슈키}", "status": "skip", "reason": "assemble_md 실패"} 반환.

  1-5. 완료 마커
    Write: `{state_dir}/{이슈키}.published`
    내용: `{"issue": "{이슈키}", "written_at": "{현재시각}"}`

  완료 시 반환: `{"issue": "{이슈키}", "status": "ok"}`

메인 세션은 모든 서브 에이전트 완료를 기다린 뒤 STEP 2로 이동.

---

STEP 2: 완료 알림
  성공/스킵 이슈 목록 출력.
  모든 이슈 [SKIP] → "모든 이슈 처리 실패" [STOP].

[TERMINATE]

## 실패 정책
- STEP 0 실패 → 전체 [STOP]
- 이슈별 실패 → 해당 이슈 [SKIP], 나머지 계속
- 첨부파일 실패 → 해당 파일만 스킵, 이슈는 계속 진행
- [STOP]/[SKIP] 우회 금지
