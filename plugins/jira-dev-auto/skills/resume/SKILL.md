---
name: jira-resume
description: 중단된 세션을 복구합니다. status.yaml과 실제 git 상태를 대조하고 마지막 완료 단계부터 재개합니다.
---

이 스킬은 `/jira resume` 명령으로 실행되며 세션이 중단된 지점을 찾아 작업을 이어갑니다.

## 작업 (Tasks)

1. **워크스페이스 확인** (CLI):
   - `--workspace {name}` 지정 시 해당 워크스페이스 사용
   - 미지정 시 `.claude/settings.yaml`의 `docs.workspace` 사용
   - `.docs/work/{workspace}/` 존재 확인

2. **인덱스 로드** (CLI):
   ```bash
   cat .docs/work/{workspace}/_index.yaml
   ```
   등록된 티켓 목록 + 도메인 구조 파악

3. **각 티켓 상태 확인** (CLI 배치):
   ```bash
   find .docs/work/{workspace} -name "*.status.yaml" | xargs cat
   ```

4. **실제 git 상태와 대조** (CLI 배치):
   ```bash
   git worktree list --porcelain
   # 각 활성 worktree에 대해:
   git -C {worktree_path} status --short
   git -C {worktree_path} log --oneline -5
   ```
   불일치 발견 시 `status.yaml` 보정 (CLI)

5. **재조회 체크포인트** (`jira-refresh` 호출):
   - 활성 티켓(merged=false)만 재조회
   - 변경 있으면 → 사용자 알림 후 대응

6. **상태 요약 보고** (사용자에게):
   ```
   워크스페이스 'sprint-q2' 복구 완료.
   PROJ-123: 병합 완료 ✓
   PROJ-456: 구현 완료 (미병합) — 커밋 3개
   PROJ-789: 대기 중 (PROJ-456 의존)

   계속 진행할까요?
   ```

7. **ask_user**: 승인 시 → 가장 앞선 미완료 단계부터 재개
   - `status=pending` → `jira-implement`부터
   - `status=in_progress` → 마지막 커밋 이후부터
   - `status=completed, merged=false` → `jira-merge`부터

## 상태 매핑

| status.yaml 상태 | 재개 시작 지점 |
|---|---|
| not_started | jira-analyze |
| pending | jira-implement |
| in_progress | jira-implement (재개) |
| completed | jira-merge |
| merged | 완료 (대시보드만) |
