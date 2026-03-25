#!/bin/bash
# Smart Multi-Worktree WIP Commit (Stop Hook)

# 1. 글로벌 스위치 확인 (Master Switch)
CONFIG_FILE=".claude/worktree-flow.json"
if [ -f "$CONFIG_FILE" ]; then
  # jq로 wip_enabled가 false이면 즉시 종료
  ENABLED=$(jq -r '.wip_enabled // "true"' "$CONFIG_FILE" 2>/dev/null)
  [ "$ENABLED" == "false" ] && exit 0
fi

# 2. 메인 저장소 루트 찾기
GIT_COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null)
[ -z "$GIT_COMMON_DIR" ] && exit 0
MAIN_ROOT=$(cd "$GIT_COMMON_DIR/.." && pwd)

# 3. 모든 워크트리 리스트 확보 (경로만 추출)
WORKTREES=$(git worktree list --porcelain | grep "^worktree " | cut -d ' ' -f 2-)

# 4. 각 워크트리 순회하며 WIP 커밋 실행
for WT_PATH in $WORKTREES; do
  # 해당 워크트리에 .wip-active 파일이 있는 경우에만 동작
  if [ -f "$WT_PATH/.wip-active" ]; then
    (
      cd "$WT_PATH" || exit
      
      # 변경사항(스테이징, 언스테이징, 미추적 파일) 확인
      if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
        exit
      fi

      # 현재 브랜치명 확보
      BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
      [ -z "$BRANCH" ] && BRANCH="unknown"

      # 변경 내역 요약 (메시지용)
      STAT=$(git diff --stat --cached 2>/dev/null; git diff --stat 2>/dev/null)
      SUMMARY=$(echo "$STAT" | tail -1 | sed 's/^ *//' | cut -d',' -f1)
      [ -z "$SUMMARY" ] && SUMMARY="uncommitted changes"

      # 커밋 실행 (조용하게)
      git add -A
      git commit -m "WIP($BRANCH): $SUMMARY" --no-verify > /dev/null 2>&1
    )
  fi
done
