---
name: autopilot-req
description: 현재 대화에서 추가 요구사항을 추출하여 이슈 문서에 기록한다. 이슈키를 지정하거나 생략하면 .autopilot에서 자동 감지한다.
---

# Requirement Record

**실행 주체: Main Session**

## 사용법
```
/autopilot:req [이슈키]
```
- 이슈키 생략 시: `.autopilot`에서 이슈 목록 자동 감지

---

## 실행 절차

STEP 0: 이슈키 확보
  이슈키가 인자로 주어진 경우: 해당 이슈키 사용
  이슈키가 없는 경우:
    `git rev-parse --show-toplevel` → worktree_path
    `cat {worktree_path}/.autopilot` → issues 배열 읽기
    실패 또는 비어있으면: "기록할 이슈가 없습니다." 출력 후 [STOP]
    issues 1개: 해당 이슈키 사용
    issues 여러 개:
      대화 맥락을 분석하여 어느 이슈에 관한 내용인지 판단
      판단 불가 시: AskUserQuestion("어느 이슈에 기록할까요?\n{issues 목록}")

STEP 1: 요구사항 추출
  현재 대화 전체를 검토하여 아래 기준으로 추가 요구사항 후보 추출:
  - 사용자가 새로 언급한 기능/동작 조건
  - 기존 명세에 없는 제약·예외 처리
  - 구현 중 합의된 변경사항
  이미 이슈 명세(`## 설명`)에 있는 내용은 제외

  추출 결과가 없으면: "추가 요구사항이 없습니다." 출력 후 [STOP]

STEP 2: 사용자 확인
  추출한 항목을 보여주고 확인:
  ```
  아래 내용을 [{이슈키}] 추가 요구사항으로 기록할까요?

  - {항목1}
  - {항목2}
  ...

  (수정할 내용이 있으면 말씀해주세요. 기록하려면 'ok')
  ```
  [GATE] AskUserQuestion
  사용자가 수정 요청 시: 반영 후 재확인
  'ok' 또는 확인 응답 시: STEP 3 진행

STEP 3: API 목록 추출
  이슈 설명과 추가 요구사항에서 도메인 키워드 추출 → 코드베이스에서 관련 API 호출 탐색:
  ```
  cd {worktree_path} && rg -n "(fetch|axios|apiClient|useMutation|useQuery|useInfiniteQuery)\(" --type ts -l | head -20
  ```
  키워드와 관련된 파일만 Read → 실제 호출되는 엔드포인트 경로·메서드 수집.
  추출 결과를 STEP 4에서 문서에 기록한다.

STEP 4: 이슈 문서에 기록
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키}` → data.md_path 확보
  실패 시: 경고 출력 후 [STOP]

  data.md_path의 `## 추가 요구사항` 섹션 끝에 append
  섹션 없으면 파일 끝에 생성:
  ```
  ## 추가 요구사항

  <!-- req {날짜} -->
  - {항목1}
  - {항목2}
  ```
  섹션 있으면 기존 섹션 끝에:
  ```
  <!-- req {날짜} -->
  - {항목1}
  - {항목2}
  ```

  이어서 `## 사용 API 목록` 섹션을 upsert (없으면 생성, 있으면 전체 교체):
  ```
  ## 사용 API 목록

  | 메서드 | 엔드포인트 | 호출 위치 |
  |--------|-----------|----------|
  | GET    | /api/example | src/entities/example/api.ts |
  ```
  추출된 API가 없으면:
  ```
  ## 사용 API 목록

  (없음 — 신규 API 작성 필요)
  ```

  완료 출력:
  ```
  [{이슈키}] 추가 요구사항 {N}건 기록 완료 / 사용 API {M}건 기록 완료
  ```

[TERMINATE]
