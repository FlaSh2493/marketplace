---
name: autopilot-check
description: 워크트리에서 lint, type-check, test를 순차 실행하고 오류 발생 시 자동 수정 후 재실행한다. 모두 통과하면 결과를 보고한다.
---

# Worktree Check

**실행 주체: Main Session**

## 사용법
`/autopilot:check [branch]`

- `branch`: 선택 인자. 생략 시 현재 브랜치 사용.

---

## STEP 0: 브랜치 확인

인자로 브랜치가 전달된 경우:
```bash
git worktree list --porcelain
```
해당 브랜치의 워크트리 경로를 찾아 `wt_root`로 사용. 없으면 현재 디렉토리를 `wt_root`로 사용하고 `current_branch`는 전달된 인자값 사용.

인자가 없는 경우:
```bash
git rev-parse --show-toplevel   → wt_root
git rev-parse --abbrev-ref HEAD → current_branch
```

상태 초기화:
```bash
main_root=$(git worktree list | head -1 | awk '{print $1}')
state_dir="$main_root/.docs/task/{current_branch}/.state"
mkdir -p "$state_dir"
rm -f "$state_dir/check" "$state_dir/check-all" "$state_dir/merge" "$state_dir/merge-all" "$state_dir/pr" "$state_dir/review-fix"
```

---

## STEP 1: 환경 탐지

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/detect_env.py {wt_root} --install
```

- `status == "error"` → reason 출력 후 [STOP]
- `data.apps`가 비어있으면 → data.message 출력 후 [STOP]

각 앱별 결과를 표시:
```
앱: {relative_path}
환경: {pkg_manager}
검사 항목:
- lint:        {checks.lint 또는 "스킵 (스크립트 없음)"}
- check-types: {checks.check-types 또는 "스킵 (스크립트 없음)"}
- test:        {checks.test 또는 "스킵 (스크립트 없음)"}
```

checks가 3개 모두 없으면 해당 앱 스킵. 단일 앱에서 스킵되면 [STOP].

---

## STEP 2: 검증 실행 (앱별)

각 앱에 대해 **checker agent** 호출:

```
[checker agent 호출]
입력:
  check_dir: {app.check_dir}
  run_cmd:   {app.run_cmd}
  checks:    {app.checks}
```

결과 반환: `{ passed, failed, fixed_files, skipped }`

- 한 앱이 실패해도 나머지 앱은 계속 진행
- 실패한 앱의 이후 검사는 agent 내부에서 이미 중단됨

---

## STEP 3: 결과 보고

모든 앱 통과 시:
```
┌──────────────────────────────────┐
│ 모든 검사 통과                    │
│ lint:        ✅ pass {수정여부}   │
│ check-types: ✅ pass {수정여부}   │
│ test:        ✅ pass {수정여부}   │
└──────────────────────────────────┘
```
- {수정여부}: 수정 없이 통과 → `(clean)`, 수정 후 통과 → `(fixed)`
- 스킵: `⏭ skip (스크립트 없음)`
- 복수 앱이면 앱별로 반복 출력

일부 앱 실패 시:
```
❌ {검사명} 실패 ({relative_path})
시도: {attempt}회
남은 에러:
{last_error}

수동 확인이 필요합니다.
```

전체 통과 시 완료 마커 조건 확인:
- 실행된 검사 항목(lint/check-types/test 중) >= 1개 이상
- 실패한 검사 항목 == 0개

조건 충족 시 AskUserQuestion으로 다음 선택지 제시:
```
검사를 모두 통과했습니다. 다음 중 선택하세요:
1. `/autopilot:check-all` — 모든 워크트리 검사 후 merge-all 준비 (메인 세션에서 실행)
2. `/autopilot:merge {피처브랜치}` — 이 워크트리만 피처 브랜치에 머지
3. `/autopilot:merge-all {피처브랜치}` — 모든 활성 워크트리를 한번에 머지
4. 추가 작업 계속
```

완료 마커 (조건 충족 시에만)
  Write: `{state_dir}/check` (빈 파일)

[TERMINATE]
