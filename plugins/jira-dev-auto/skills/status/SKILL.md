---
name: jira-status
description: .docs/work/{workspace}/ YAML 파일만 읽어 전체 현황 대시보드를 출력합니다. LLM 호출 없음.
---

이 스킬은 토큰 소비 없이 로컬 파일만으로 현황을 조회합니다.

## 특징
- **LLM 호출 없음** (토큰 0)
- 항상 사용 가능 (다른 Phase와 독립)
- 모든 데이터는 `.docs/work/{workspace}/` YAML에서 읽기

## 작업 (Tasks)

### 전체 현황 (`/jira status`)

1. **워크스페이스 확인** (CLI):
   ```bash
   cat .claude/settings.yaml | grep workspace
   ```

2. **데이터 수집** (CLI 배치):
   ```bash
   cat .docs/work/{workspace}/_index.yaml
   find .docs/work/{workspace} -name "*.status.yaml" | xargs cat
   git worktree list --porcelain 2>/dev/null
   ```

3. **대시보드 출력**:
   ```
   워크스페이스: sprint-q2
   ─────────────────────────────────
   도메인: auth
     PROJ-123  ✓ 병합 완료    feat/PROJ-123-auth-login
   도메인: payment
     PROJ-456  ⚙ 구현 완료    feat/PROJ-456-payment-retry   (미병합)
   도메인: api
     PROJ-789  ○ 대기 중      (PROJ-456 의존)
   ─────────────────────────────────
   진행률: 1/3 병합 완료
   ```

### 개별 티켓 상세 (`/jira status PROJ-123`)

4. **데이터 수집** (CLI 배치):
   ```bash
   cat .docs/work/{workspace}/_cache/PROJ-123.snapshot.json | jq '{key, fetched_at, pinned_at}'
   cat .docs/work/{workspace}/{domain}/{KEY}/requirement.yaml
   cat .docs/work/{workspace}/{domain}/{KEY}/status.yaml
   git -C .docs/work/worktrees/PROJ-123 log --oneline -5 2>/dev/null
   ```

5. **상세 출력**:
   ```
   PROJ-123 — Auth Login 구현
   상태: 병합 완료 ✓
   도메인: auth
   브랜치: feat/PROJ-123-auth-login
   PIN: 2026-03-23T10:05:00Z
   커밋: 3개
   병합: develop (2026-03-23T14:30:00Z)
   ```

### worktree 목록 (`/jira worktrees`)

6. **CLI**:
   ```bash
   git worktree list
   ```
   status.yaml과 대조하여 병합 여부 표시

### worktree 미병합만 (`/jira worktrees --unmerged`)

7. `merged: false`인 것만 필터링 + 병합 권장 순서 출력

### 동기화 이력 (`/jira history PROJ-123`)

8. **CLI**:
   ```bash
   cat .docs/work/{workspace}/_cache/PROJ-123.snapshot.json | jq '.sync_history'
   cat .docs/work/{workspace}/_cache/PROJ-123.diff.json 2>/dev/null
   ```

### PIN vs 최신 차이 (`/jira diff PROJ-123`)

9. **CLI**:
   ```bash
   diff -u \
     <(jq '.data' .docs/work/{workspace}/_cache/PROJ-123.snapshot.json) \
     <(jq '.data' .docs/work/{workspace}/_cache/PROJ-123.latest.json 2>/dev/null || echo '{}')
   ```
