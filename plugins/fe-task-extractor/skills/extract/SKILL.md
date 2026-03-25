---
name: extract
description: Writer 서브에이전트 전용. 기획서·PRD·요구사항 문서에서 프론트엔드 작업만 식별·추출하여 작업 명세를 생성한다. "프론트엔드 작업 추출", "FE 태스크 분리", "작업 세분화" 등을 요청할 때 사용한다.
---

# Frontend Task Extract

**실행 주체: Writer 에이전트 전용**
"무엇을 만들 것인가"만 추출한다. 구현 방법·AC·체크리스트 작성 금지.

## 사용법
`/fe-task-extractor:extract`
(입력 문서는 대화에서 직접 제공)

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py extract`
  성공: data.branch, data.template_path, data.example_path 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 1: 예시 로드
  data.example_path의 파일을 읽어 출력 형식 파악
  (예시 파일이 없으면 스킵)

STEP 2: FE 작업 식별 (Claude 역할)

  2-1. 전체 이해
    기능 목적, 사용자 시나리오, 시스템 구성 파악

  2-2. 영역 분류 — FE만 추출
    FE: UI·인터랙션·상태관리·클라이언트 API 호출·라우팅·폼·클라이언트 유효성·반응형·에러 UI·로딩/스켈레톤
    제외(기재만): BE API 구현·DB·서버 인증·비즈니스 로직 / 디자인 / 기획·QA

  2-3. 세분화
    단순 1개 / 중간 2~5개 / 복잡 5~10+
    서로 다른 페이지·독립 컴포넌트 → 분리
    함께 구현되는 것 → 묶기

  2-4. 의존관계·API 매핑
    각 작업의 선행/후행, 연동 API 기록

STEP 3: 파일 생성
  각 작업마다 (FE-01, FE-02, ...):
  ```bash
  echo "{설명}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create_task_file.py \
    "{branch}" "FE-{N}" "{제목}" \
    --status "신규" \
    --assignee "@본인" \
    --source "extract" \
    --deps "{선행→후행 또는 없음}" \
    --api "{API 또는 없음}" \
    --states "{상태 흐름 또는 없음}"
  ```
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_template.py {file_path}`
  실패: reason 그대로 출력 후 [STOP]

[GATE] STEP 4: 작업 목록 승인
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/list_tasks.py {branch} --state NONE`
  결과를 아래 표 형식으로 출력:
  ```
  | ID    | 작업 제목        | 선행 |
  |-------|----------------|------|
  | FE-01 | 로그인 폼 UI    | 없음 |
  | FE-02 | 목록 페이지 구현 | FE-01 |
  ```
  실행: AskUserQuestion("추출된 작업 목록입니다. 이대로 진행할까요? (수정이 필요하면 내용을 입력하세요 / no: 취소)")
  [LOCK: 응답 전 transition.py 절대 실행 금지]

  응답 "yes":
    STEP 5 진행

  응답 "수정 {내용}":
    해당 파일 수정 후 validate_template.py 재실행
    [GATE] STEP 4 반복

  응답 "no":
    출력: "취소되었습니다."
    [TERMINATE]

STEP 5: 상태 전이
  각 파일마다:
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} FE-{N} NONE DRAFT`
  실패: reason 그대로 출력 후 [STOP]

  완료 시: notify_user("추출 완료. /fe-task-extractor:publish 실행 가능")

[TERMINATE]
구현 방법·AC·체크리스트 작성 금지. 원문에 없는 작업 추가 금지.
