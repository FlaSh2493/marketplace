# worktree-management

**목적**: git worktree 생성·재사용·정리 절차를 정의한다.

## 브랜치 네이밍 규칙

```
feat/{KEY}-{summary-slug}

slug 규칙:
- 소문자, 하이픈으로 구분
- 최대 30자
- 특수문자 제거

예: feat/PROJ-123-auth-refresh-token
    feat/PROJ-456-payment-retry-logic
```

## worktree 생성

```bash
# 기본 명령
git worktree add {worktree_root}/{KEY} -b {branch} {base_branch}

# worktree_root: settings.yaml의 git.worktree_root (기본값: ../worktrees)
# base_branch: settings.yaml의 git.base_branch (기본값: develop)
```

**충돌 시 처리**:
1. `git worktree list` 로 기존 worktree 확인
2. 동일 경로가 있으면 → 재사용 (새로 만들지 않음)
3. 다른 브랜치로 사용 중이면 → `{KEY}-v2` 형태로 새 경로 생성

## worktree 목록 확인

```bash
git worktree list --porcelain
```

## worktree 상태 확인

```bash
git -C {worktree_path} status --short
git -C {worktree_path} log --oneline -5
git -C {worktree_path} diff --stat HEAD
```

## worktree 정리

```bash
# 병합 완료 후 정리
git worktree remove {worktree_path}

# 강제 삭제 (uncommitted changes 있어도)
git worktree remove --force {worktree_path}

# 전체 정리 (merged: true인 것 전부)
git worktree prune
```

## 규칙

1. 구현 전 반드시 base_branch 최신 상태 확인:
   ```bash
   git -C {repo_root} fetch origin {base_branch}
   git -C {repo_root} merge origin/{base_branch}
   ```
2. worktree 생성 후 즉시 사전 검증 (빌드/deps) 실행
3. 정리는 `merged: true` 확인 후에만 진행
4. 정리 전 사용자 확인 필수 (ask_user)
