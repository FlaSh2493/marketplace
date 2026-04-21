---
name: task-sync-extract
description: Writer 서브에이전트 전용. 기획서·PRD·요구사항 문서에서 프론트엔드 작업만 식별·추출하여 작업 명세를 생성한다.
---

# Frontend Task Extract

**실행 주체: Writer 에이전트 전용**
"무엇을 만들 것인가"만 추출. 구현 방법·AC·체크리스트 작성 금지.

## 사용법
`/task-sync:extract` (입력 문서는 대화에서 직접 제공)

## 실행 절차

STEP 0: 준비
  브랜치명 확인: `.git/HEAD` 또는 대화 컨텍스트

STEP 1: FE 작업 식별 (Claude 역할)
  1-1. 기능 목적·사용자 시나리오·시스템 구성 파악
  1-2. 영역 분류 — FE만 추출
    FE: UI·인터랙션·상태관리·클라이언트 API 호출·라우팅·폼·유효성·반응형·에러 UI·로딩/스켈레톤
    제외(기재만): BE API·DB / 디자인 / 기획·QA
  1-3. 세분화 (단순 1개 / 중간 2~5 / 복잡 5~10+)
    다른 페이지·독립 컴포넌트 → 분리 / 함께 구현 → 묶기
  1-4. 의존관계·API 매핑

STEP 2: 파일 저장
  각 작업마다 create_task_file.py 호출 (이 스크립트가 템플릿 형식으로 파일 생성):
    `echo "{설명}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create_task_file.py "FE-{N}" "{제목}" --source extract --deps "{deps}" --api "{api}" --states "{states}"`
    exit 1 → reason 출력, [STOP]

[GATE] STEP 3: 작업 목록 승인
  테이블 출력: | ID | 작업 제목 | 선행 |
  AskUserQuestion("추출된 작업 목록입니다. 이대로 진행할까요? (수정 시 내용 입력 / no: 취소)")
  [LOCK: 응답 전 진행 금지]
  "yes" → STEP 4 / "수정 {내용}" → Edit 후 STEP 3 반복 / "no" → [TERMINATE]

STEP 4: 완료 알림
  notify_user("추출 완료 [{N}개]: /task-sync:publish 실행 가능")

[TERMINATE]
원문에 없는 작업 추가 금지. 구현 방법·AC 작성 금지.
