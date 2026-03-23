---
name: jira-start
description: "선택한 spec의 작업을 시작합니다. 이슈 간 자동 연결됩니다. Use when the user says 'start working on' a spec."
argument-hint: "<spec명> (예: login-spec)"
disable-model-invocation: true
---

## 동작
1. {workDir}/jira-planner/specs/{spec}/state.json 로드
2. 첫 미완료 이슈 확인
3. issues/{이슈키}.md 읽기 → 세션에 주입
4. 이슈 작업 루프:
   a. Plan 모드 안내 → 사용자 계획 수립 → 승인
   b. 구현 → 사용자 확인
   c. 자동: 문서 저장 + 상태 업데이트
   d. 다음 이슈 있으면 → 이전 결과 요약 + 다음 이슈 로드 → 4a로
5. 전체 완료 시 → 요약 출력 + 세션 종료

## 이슈 전환 시 주입 정보
- 이전 이슈 변경 파일 목록
- 새로 생성/수정된 인터페이스 요약 (500토큰 이내)
- 다음 이슈의 재작성된 요구사항 전문 (issues/{키}.md)
---
## auto-chain 로직 포함
본 스킬은 이슈 완료 시 자동으로 다음 이슈를 로드하는 로직을 포함합니다.
(auto-chain 스킬과 연계됨)
