---
name: jira-refresh
description: Jira 티켓 변경을 감지하고 영향도를 분류한 뒤 사용자 결정에 따라 재동기화합니다.
---

이 스킬은 PHASE 5→6(구현 전) 및 PHASE 6→7(병합 전) 체크포인트에서 자동으로, 또는 `/jira refresh` 명령으로 수동 실행됩니다.

## 사전 조건
- `_cache/{KEY}.snapshot.json` 존재 (PIN 완료)
- `references/change-impact.md` 로드

## 작업 (Tasks)

1. **MCP 재조회** (활성 티켓 전체):
   - `mcp__atlassian__jira_get_issue` 로 최신 데이터 조회
   - `.docs/work/{workspace}/_cache/{KEY}.latest.json` 저장

2. **필드별 해시 비교** (CLI, 토큰 0):
   ```bash
   # snapshot.json과 latest.json의 content_hash 필드별 비교
   jq -r '.content_hash | to_entries[] | "\(.key): \(.value)"' snapshot.json > /tmp/snap_hashes.txt
   # latest.json의 각 필드를 sha256으로 계산 후 비교
   ```
   - 변경 없음 → 호출 단계로 복귀 (스킬 종료)
   - 변경 있음 → 다음 단계

3. **영향도 분류** (CLI, `references/change-impact.md` 기준, 토큰 0):
   ```
   ignore: labels, 진행방향 status 변경
   warn:   priority 상향, 새 의존성, 요구사항 키워드 포함 댓글
   halt:   summary, description, acceptance_criteria 변경
   ```
   - `ignore` → 로그만 기록 후 복귀
   - `warn` → 4번으로
   - `halt` → 4번으로

4. **사용자 알림** (ask_user):
   - 변경된 필드 목록 표시
   - 선택지:
     - "확인하고 계속" (warn만) → 복귀
     - "변경 검토" → 5번으로
     - "요구사항 반영" → 5번으로
     - "작업 중단" (halt) → 5번으로

5. **정밀 diff 생성** (CLI, 토큰 0):
   ```bash
   diff -u <(jq '.data' snapshot.json) <(jq '.data' latest.json)
   ```
   `.docs/work/{workspace}/_cache/{KEY}.diff.json` 저장

6. **영향 범위 분석** (LLM, ~1500 토큰):
   - 입력: diff + `requirement.yaml`의 키 목록만
   - 출력: `affected_fields`, `affected_files`, `severity` (none/partial/full_rework)

7. **사용자 결정** (ask_user):
   - **"변경 반영"** (partial):
     - `requirement.yaml` 해당 항목만 갱신 (CLI)
     - 영향받는 파일만 수정 지시 (LLM)
     - 스냅샷 재PIN (CLI)
     - 호출 단계로 복귀
   - **"현재 기준으로 계속"**:
     - `sync_history`에 기록 (CLI)
     - PIN 유지, 호출 단계로 복귀
   - **"전면 재작업"** (full_rework):
     - 기존 브랜치를 `{branch}-v1`으로 보존 (CLI)
     - 새 worktree 생성 → `jira-refine`부터 재실행
   - **"follow-up 티켓으로"** (이미 병합된 경우):
     - 새 Jira 티켓 생성 권장 후 종료

## 출력
- `.docs/work/{workspace}/_cache/{KEY}.latest.json`
- `.docs/work/{workspace}/_cache/{KEY}.diff.json` (변경 시)
- `.docs/work/{workspace}/_cache/{KEY}.snapshot.json` (재PIN 시 pinned_at 갱신)
- `.docs/work/{workspace}/{domain}/{KEY}.requirement.yaml` (반영 시)
