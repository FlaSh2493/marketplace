---
name: extract
description: Writer 서브에이전트 전용. 기획서·PRD·요구사항 문서에서 프론트엔드 작업만 식별·추출하여 작업 명세를 생성한다.
---

# Frontend Task Extract

**실행 주체: Writer 에이전트 전용**
"무엇을 만들 것인가"만 추출한다. 구현 방법·AC·체크리스트 작성 금지.

## 사용법
`/fe-task-extractor:extract`
(입력 문서는 대화에서 직접 제공)

## 실행 절차

STEP 0: 템플릿 로드 (Read 도구)
  Read: `${CLAUDE_PLUGIN_ROOT}/templates/fe-task-template.md`
  Read: `${CLAUDE_PLUGIN_ROOT}/templates/fe-task-example.md`
  브랜치명 확인: Read `.git/HEAD` 또는 대화 컨텍스트에서 파악

STEP 1: FE 작업 식별 (Claude 역할)

  1-1. 전체 이해
    기능 목적, 사용자 시나리오, 시스템 구성 파악

  1-2. 영역 분류 — FE만 추출
    FE: UI·인터랙션·상태관리·클라이언트 API 호출·라우팅·폼·클라이언트 유효성·반응형·에러 UI·로딩/스켈레톤
    제외(기재만): BE API 구현·DB / 디자인 / 기획·QA

  1-3. 세분화
    단순 1개 / 중간 2~5개 / 복잡 5~10+
    서로 다른 페이지·독립 컴포넌트 → 분리 / 함께 구현되는 것 → 묶기

  1-4. 의존관계·API 매핑
    각 작업의 선행/후행, 연동 API 기록

STEP 2: 파일 저장 (Bash — create_task_file.py 필수)
  각 작업마다:
  ```
  echo "{설명}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create_task_file.py \
    "{branch}" "FE-{N}" "{작업 제목}" \
    --source extract \
    --deps "{deps}" --api "{api}" --states "{states}"
  ```
  성공: data.file_path 확인
  실패: reason 그대로 출력 후 [STOP]

  저장 후 각 파일마다 pending 마커 (Bash):
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} FE-{N} NONE PENDING`

[GATE] STEP 3: 작업 목록 승인
  저장된 파일 목록을 표로 출력:
  ```
  | ID    | 작업 제목        | 선행  |
  |-------|----------------|-------|
  | FE-01 | 로그인 폼 UI    | 없음  |
  | FE-02 | 목록 페이지 구현 | FE-01 |
  ```
  AskUserQuestion("추출된 작업 목록입니다. 이대로 진행할까요? (수정 필요 시 내용 입력 / no: 취소)")
  [LOCK: 응답 전 다음 진행 금지]

  응답 "yes": STEP 4 진행
  응답 "수정 {내용}": 해당 파일 Edit 후 STEP 3 반복
  응답 "no": [TERMINATE]

STEP 4: 완료 알림
  notify_user("추출 완료 [{N}개]: /fe-task-extractor:publish 실행 가능")

[TERMINATE]
구현 방법·AC·체크리스트 작성 금지. 원문에 없는 작업 추가 금지.
