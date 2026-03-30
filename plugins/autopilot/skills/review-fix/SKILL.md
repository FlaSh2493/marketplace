---
name: autopilot-review-fix
description: PR을 올린 후 CodeRabbit의 리뷰를 자동으로 대기하여 제안사항을 적용하고 결과를 보고한다.
---

# CodeRabbit 리뷰 적용

**실행 주체: Main Session**

## 사용법
`/autopilot:review-fix`

## 실행 절차

STEP 0: 컨텍스트 확보
  다음 명령을 각각 실행하여 컨텍스트 확보:
  - `git rev-parse --show-toplevel` → worktree_path
    실패 시: "git 저장소가 아닙니다." 출력 후 [STOP]
  - `git rev-parse --abbrev-ref HEAD` → current_branch
    출력이 `HEAD`(detached HEAD)이면: "detached HEAD 상태입니다. 브랜치를 checkout하세요." 출력 후 [STOP]

  current_branch가 `develop` 또는 `main`이면: "피처 브랜치에서 실행하세요." 출력 후 [STOP]

  safe_branch: current_branch의 `/`를 `-`로 치환한 값
  state_file: `/tmp/autopilot_review_{safe_branch}.json` (상태 파일 경로)

  **이후 모든 Bash 명령은 `cd '{worktree_path}' && command` 형태로 실행**

STEP 0-A: PR 번호 확인
  ```bash
  cd '{worktree_path}' && gh pr list --head '{current_branch}' --base develop --state open --json number -q '.[0].number // empty'
  ```
  출력이 비어있으면: "열린 PR이 없습니다. 먼저 /autopilot:pr로 PR을 생성하세요." 출력 후 [STOP]
  → pr_number 변수에 보관

STEP 1: 이전 상태 확인
  state_file 존재 여부 확인:
  - 존재 && "reviews_fetched" 필드가 true: 이미 리뷰를 가져온 상태 → STEP 3으로 점프
  - 존재 && 필드 없음: 폴링 중 중단된 상태 → STEP 2 재개
  - 없음: 처음 실행 → STEP 2 진행

  상태 파일 구조:
  ```json
  {
    "pr_number": 123,
    "current_branch": "feature/foo",
    "reviews_fetched": false,
    "reviews": [],
    "applied_count": 0,
    "failed_count": 0,
    "applied_files": []
  }
  ```

STEP 2: CodeRabbit 리뷰 폴링
  최대 10분(600초) 동안 30초마다 리뷰 확인:
  ```bash
  cd '{worktree_path}' && for i in {1..20}; do
    reviews=$(gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
      --jq '[.[] | select(.user.login | test("coderabbitai"))]')
    if [ -n "$reviews" ] && [ "$reviews" != "[]" ]; then
      echo "$reviews"
      break
    fi
    echo "[$i/20] 리뷰 대기 중..." >&2
    sleep 30
  done
  ```

  리뷰 감지 시:
  - reviews 데이터를 상태 파일에 저장
  - "reviews_fetched": true 마킹
  - STEP 3 진행

  타임아웃(20회 반복 후):
  - "CodeRabbit 리뷰가 아직 없습니다. 잠시 후 다시 실행하세요: /autopilot:review-fix" 출력
  - [STOP]

STEP 3: 리뷰 파싱 및 제안 추출
  상태 파일의 reviews에서:

  3-A. suggestion 블록 추출:
    - 각 comment의 body에서 ````suggestion` ... ````diff 패턴 추출
    - 패턴: 파일경로 → 변경 전 코드 → 변경 후 코드
    - 추출 실패하면 무시하고 계속

  3-B. 일반 텍스트 코멘트 처리:
    - suggestion 블록 없는 코멘트는 텍스트 요약만 기록
    - 자동 적용하지 않고 결과 보고 시 사용자에게 표시

  제안 항목 목록 구성:
  ```json
  {
    "suggestions": [
      {
        "type": "code_change",
        "file": "src/foo.ts",
        "before": "...",
        "after": "..."
      },
      {
        "type": "text_only",
        "author": "coderabbitai",
        "comment": "..."
      }
    ]
  }
  ```

  상태 파일에 suggestions 배열 저장

STEP 4: 제안 자동 적용
  각 suggestion별 순차 처리:

  4-A. type == "code_change":
    - 해당 파일 읽기 (Read 도구)
    - 파일에서 "before" 코드 찾기 (정확 매칭 또는 퍼지 매칭)
    - 매칭 성공: Edit 도구로 "before" → "after" 치환
    - 성공 시: applied_count 증가, applied_files에 파일명 추가
    - 실패 시: failed_count 증가, 실패 이유 기록 (matched not found 등)

  4-B. type == "text_only":
    - 자동 적용 불가 → 결과 보고 시 사용자에게 수동 검토 유도

  모든 항목 처리 후 상태 파일 갱신

STEP 5: 결과 보고
  ```
  ┌─────────────────────────────────────────┐
  │ CodeRabbit 리뷰 적용 완료                  │
  │ PR: #{pr_number}                         │
  │ 적용된 제안: {applied_count}개             │
  │ 실패한 제안: {failed_count}개             │
  │ 수정 파일: {applied_files.join(", ")}    │
  └─────────────────────────────────────────┘
  ```

  failed_count > 0이면 추가 표시:
  ```
  ⚠️  일부 제안을 자동 적용하지 못했습니다:
  - {실패한 항목 설명}

  텍스트 코멘트도 확인하세요:
  - {text_only 코멘트 내용}
  ```

  applied_count == 0이고 실패도 있으면:
  "자동으로 적용할 수 있는 제안이 없었습니다. PR 코멘트를 수동으로 확인하세요." 출력 후 STEP 7로

STEP 6: 커밋 & Push
  ```bash
  cd '{worktree_path}' && git add -A && \
    git commit -m "fix: apply coderabbit review suggestions" && \
    git push
  ```

  실패 시: "커밋/푸시에 실패했습니다. 수동으로 확인하세요." [STOP]
  성공 시: "리뷰 제안 적용 완료 (커밋됨)" → STEP 7

[GATE] STEP 7: 완료 후 선택지 제시
  AskUserQuestion으로 다음 선택지 제시:
  ```
  다음 중 선택하세요:
  1. /autopilot:check — lint/type-check/test 실행
  2. /autopilot:merge — 피처 브랜치에 통합
  3. /autopilot:review-fix 재실행 — 새 리뷰 반영 (폴링 초기화)
  4. 추가 작업 계속
  ```

[TERMINATE]

## 중단 내성

- **폴링 중 중단**: 상태 파일 없으면 STEP 2부터 재시작
- **리뷰 가져온 후 중단**: 상태 파일 있으면 STEP 3부터 재개
- **수정 적용 중 중단**: 미적용 제안만 이어서 처리
- **재실행 시**: 기존 state_file을 읽어서 중복 폴링 방지

## 실패 케이스 처리

- 파일을 찾을 수 없음 → 실패로 기록, 계속 진행
- "before" 코드가 정확히 매칭 안 됨 → 실패로 기록, 다음 제안으로
- 편집 중 충돌 → 편집 도구 오류 메시지 표시, 사용자 확인 후 수동 처리 가능
