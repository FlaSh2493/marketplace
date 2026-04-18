---
name: autopilot-check-all
description: 메인 세션에서 모든 활성 워크트리의 lint, type-check, test를 일괄 실행한다. 오류 발생 시 자동 수정 후 재실행하며, 전체 통과 시 merge-all을 제안한다.
---

# Worktree Check All

**실행 주체: Main Session**
git push 금지.

## 사용법
`/autopilot:check-all`

---

## STEP 0: 워크트리 목록 조회

상태 초기화:
```bash
main_root=$(git rev-parse --show-toplevel)
state_dir="$main_root/.docs/task/check-all/.state"
mkdir -p "$state_dir"
rm -f "$state_dir/check" "$state_dir/check-all" "$state_dir/merge" "$state_dir/merge-all" "$state_dir/pr" "$state_dir/review-fix"
```

다음 명령을 각각 실행:
- `git worktree list --porcelain` → 전체 워크트리 목록 파싱
- 첫 번째 항목(main_root_path) 제외한 나머지 수집

각 워크트리 경로별로 `.autopilot` 파일 존재 여부 확인:
```bash
python3 -c "import json; d=json.load(open('{wt_path}/.autopilot')); print(d.get('base_branch',''))" 2>/dev/null
```
`.autopilot` 없거나 파싱 실패 → 해당 워크트리 제외

수집된 워크트리가 없으면: "활성 워크트리가 없습니다." 출력 후 [STOP]

각 워크트리의 브랜치와 이슈 목록을 수집:
```bash
git -C {wt_path} rev-parse --abbrev-ref HEAD  → wt_branch
```

---

## STEP 1: 환경 탐지 (워크트리별)

워크트리 목록을 순서대로 처리:

각 워크트리마다:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/detect_env.py {wt_path} --install
```

- `status == "error"` → 해당 워크트리 스킵, 경고 출력
- `data.apps`가 비어있으면 → 해당 워크트리 스킵 ("검사할 앱 없음")
- 성공 시 → `{ wt_path, wt_branch, apps }` 수집

탐지 결과를 표로 출력:
```
워크트리 검사 계획:
┌──────────────────────────┬──────────────┬──────────────────────────────────┐
│ 브랜치                    │ 이슈          │ 검사 항목                         │
├──────────────────────────┼──────────────┼──────────────────────────────────┤
│ worktree-PLAT-101        │ PLAT-101     │ lint ✓  type-check ✓  test ✓    │
│ worktree-PLAT-102        │ PLAT-102     │ lint ✓  type-check ✓  test -    │
└──────────────────────────┴──────────────┴──────────────────────────────────┘
```

모든 워크트리가 스킵되면: "검사할 워크트리가 없습니다." [STOP]

---

## STEP 2: 검증 실행 (워크트리별)

탐지된 워크트리를 순서대로 처리. 한 워크트리 실패해도 나머지 계속 진행.

각 워크트리마다 출력:
```
━━━ {wt_branch} 검사 중 ━━━
```

각 앱에 대해 **checker agent** 호출:

```
[checker agent 호출]
입력:
  check_dir: {app.check_dir}
  run_cmd:   {app.run_cmd}
  checks:    {app.checks}
```

checker agent는 오류 발생 시 자동 수정 후 재실행 (최대 3회):
- lint --fix 자동 적용
- 타입 오류 코드 수정
- 수정 후에도 실패 시 해당 검사 실패로 기록

결과 반환: `{ passed, failed, fixed_files, skipped }`
결과를 `wt_results` 배열에 수집: `{ wt_branch, wt_path, apps_result }`

---

## STEP 3: 결과 보고

전체 결과 표 출력:

```
┌──────────────────────────┬───────────────┬──────────────┬──────────────┐
│ 브랜치                    │ lint          │ type-check   │ test         │
├──────────────────────────┼───────────────┼──────────────┼──────────────┤
│ worktree-PLAT-101        │ ✅ (fixed)    │ ✅ (clean)   │ ✅ (clean)   │
│ worktree-PLAT-102        │ ✅ (clean)    │ ✅ (clean)   │ ⏭ skip      │
│ worktree-PLAT-103        │ ❌ 실패       │ -            │ -            │
└──────────────────────────┴───────────────┴──────────────┴──────────────┘
```

- `✅ (clean)`: 수정 없이 통과
- `✅ (fixed)`: 자동 수정 후 통과
- `⏭ skip`: 스크립트 없음
- `❌ 실패`: 자동 수정 3회 후에도 실패

**전체 통과 시:**

완료 마커 조건 확인:
- 검사한 워크트리 수 >= 1
- 실패한 워크트리 수 == 0

조건 충족 시 AskUserQuestion으로 다음 선택지 제시:
```
모든 워크트리 검사를 통과했습니다. 다음 중 선택하세요:
1. `/autopilot:merge-all {피처브랜치}` — 모든 워크트리 한번에 머지
2. 추가 작업 계속
```

완료 마커 (조건 충족 시에만)
  Write: `{state_dir}/check-all` (빈 파일)

**일부 실패 시:**

실패한 워크트리 목록 출력 후 완료 마커 기록 안 함:
```
❌ 검사 실패 워크트리:
- {wt_branch}: {검사명} 실패
  → 해당 워크트리 세션에서 `/autopilot:check` 실행하여 수동 확인
```

[TERMINATE]
