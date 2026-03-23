---
name: jira-status
description: "전체 spec별 진행 상황을 보여줍니다. Use when the user asks about progress or status."
argument-hint: "[spec명]. 생략 시 전체 현황."
disable-model-invocation: true
---

## 출력 예시 (전체)
  login-spec     2/3 완료  IET-1 ✓ IET-2 ✓ IET-3 ○
  payment-spec   0/2       IET-4 ○ IET-5 ○

## 출력 예시 (특정 spec)
  /jira-status login-spec

  login-spec (서브에이전트, 3 이슈)
    IET-1  세션 로직 분리          ✓ Done
    IET-2  세션 만료 + 자동 갱신    ✓ Done
    IET-3  결제 에러 핸들링         ○ Not Started

  다음: /jira-start login-spec (IET-3부터 재개)
