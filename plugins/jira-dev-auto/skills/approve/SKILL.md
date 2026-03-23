---
name: jira-approve
description: 각 티켓별 plan.md를 하나씩 검토하고 빌드/구현 진행 여부를 결정합니다.
---

이 스킬은 생성된 구현 계획들을 사용자에게 하나씩 보여주고 최종 승인을 받습니다.

## 사전 조건
- `jira-plan` 완료 (모든 티켓 `plan.md` 및 `plan.yaml` 존재)

## 작업 (Tasks) — 티켓마다 반복

1. **계획 노출** (CLI/view):
   - `.docs/work/{workspace}/{domain}/{KEY}/plan.md` 파일을 화면에 출력합니다.
   - 현재 진행 중인 티켓의 인덱스를 표시합니다 (예: "3/5개 티켓 검토 중").

2. **사용자 결정** (ask_user):
   - **선택 UI** 제공:
     - `[1] 승인 (Approve)` -> 해당 티켓 `status.yaml`에 `approved: true` 기록
     - `[2] 수정 요청 (Request Changes)` -> 피드백 입력 후 `plan` 스킬로 복귀
     - `[3] 보류 (Skip)` -> 나중에 다시 검토 (현재 세션 제외)
     - `[4] 거절 (Reject)` -> 해당 티켓 작업을 취소하고 목록에서 제외
     - `[자유 입력] 의견 추가`

3. **결과 기록** (CLI):
   - `.docs/work/{workspace}/{domain}/{KEY}/status.yaml`에 승인 상태를 업데이트합니다.
   ```yaml
   approval:
     status: "approved" # or "skipped", "rejected"
     at: "<ISO8601>"
     feedback: "..."
   ```

4. **다음 티켓 이동**: 모든 티켓에 대한 결정이 완료될 때까지 반복합니다.

## 출력
- `.docs/work/{workspace}/{domain}/{KEY}/status.yaml` 업데이트

## 다음 단계
승인된 티켓들에 대해서만 `jira-implement` 단계로 진입합니다.
