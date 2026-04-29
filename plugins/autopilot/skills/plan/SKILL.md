---
name: plan
description: (명시적 커맨드 실행 전용) /autopilot:plan 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# Deep Plan

## 발동 self-check

다음 중 하나라도 해당하면 진행:

- 변경이 3+ 파일에 걸침
- 공개 인터페이스/계약 변경
- 데이터 마이그레이션 동반
- 요구가 모호하거나 다중 해법 가능

해당 없으면 이 skill 쓰지 말고 바로 작업하라.

## 진행 절차

1. **준비**: `resolve_worktree.py` 등을 통해 작업 환경(`data.worktree_path`)을 확인한다.
2. **워크플로우 실행**: `reference/workflow.md`에 적힌 순서대로 분석과 설계를 진행한다.
3. **이슈 로드**: `scripts/load_issue.py {data.issue} --sections 배경,목표,비목표,요구사항,인수 조건,참고,제약/고려사항` 을 호출하여 맥락을 파악한다.
4. **Plan 작성**: `templates/template.md` 형식을 준수하여 `EnterPlanMode`로 작성한다.
5. **Phase 관리**: 컨텍스트 크기에 따라 Phase를 나누어 상세히 기술한다.

## 저장 및 종료

- 완료된 플랜은 `tasks/{data.issue}/plan.md` 경로에 저장되도록 한다.
- 플랜 모드 중 대화로 플랜 내용이 변경되면 즉시 `plan.md`를 업데이트한다.
