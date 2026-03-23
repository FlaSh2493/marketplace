---
name: jira-save
description: "현재 이슈의 작업 결과를 문서로 저장합니다. Use when issue implementation is confirmed or user asks to save progress."
argument-hint: "[이슈키]. 생략 시 현재 진행 중인 이슈."
---

## 동작
1. 현재 세션 작업 내용 수집
2. 이슈별 문서 생성:
   - plan.md (구현 계획, 의사결정 근거)
3. {workDir}/jira-planner/specs/{spec}/issues/{이슈키}/ 에 저장
4. state.json + Jira 상태 업데이트
5. auto-chain 로직으로 복귀

## 호출 시점
- 자동: 사용자가 구현 결과를 "ㅇ"으로 확인한 직후
- 수동: 중간 저장이 필요할 때 직접 호출 가능
