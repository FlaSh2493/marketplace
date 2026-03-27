---
name: autopilot-check
description: 워크트리에서 lint, type-check, test를 순차 실행하고 오류 발생 시 자동 수정 후 재실행한다. 모두 통과하면 결과를 보고한다.
---

# Worktree Check

**실행 주체: Main Session**

## 사용법
`/autopilot:check`

---

## 경로 변수 규칙

| 변수 | 의미 | 용도 |
|------|------|------|
| `wt_root` | git worktree 루트 (`git rev-parse --show-toplevel`) | **git 명령 전용** (diff, merge-base 등) |
| `check_dir` | package.json이 있는 앱 디렉토리 | **검사 실행 전용** (lint, type-check, test, eslint --fix, Read/Edit) |

- git 명령: `cd {wt_root} && git ...`
- 검사/수정: `cd {check_dir} && {run_cmd} ...`, Read/Edit는 `{check_dir}/파일경로`
- **두 변수를 절대 혼용하지 않는다**

---

## STEP 0: 워크트리 확인

다음 명령을 각각 실행하여 컨텍스트 확보:
- `git rev-parse --show-toplevel` → wt_root
- `git rev-parse --abbrev-ref HEAD` → current_branch

current_branch가 `worktree-` prefix로 시작하지 않으면: "워크트리 브랜치가 아닙니다. 워크트리 안에서 실행하세요." 출력 후 [STOP]

---

## STEP 1: 환경 탐지

### 1-1. 변경된 앱 디렉토리 탐지

워크트리의 변경 파일 목록을 확보 (커밋된 변경 + 미커밋 변경 모두 포함):
```bash
cd {wt_root} && {
  # 커밋된 변경: merge-base 기준
  MERGE_BASE=$(git merge-base HEAD "$(git log --format='%D' HEAD | grep -oE 'origin/[^ ,]+' | head -1)" 2>/dev/null)
  [ -n "$MERGE_BASE" ] && git diff --name-only "$MERGE_BASE" HEAD
  # 미커밋 변경: staged + unstaged + untracked
  git diff --name-only HEAD
  git ls-files --others --exclude-standard
} | sort -u
```
출력이 비어있으면: "변경된 파일이 없습니다." 출력 후 [STOP]

변경 파일 경로에서 `package.json`을 가진 가장 가까운 상위 디렉토리를 찾는다:
- 각 변경 파일의 디렉토리부터 상위로 올라가며 `package.json` 탐색 (wt_root에서 멈춤)
- wt_root 자체의 package.json에만 매칭되는 파일 중, 앱 코드가 아닌 것 (.github/, .claude/ 등 dot-디렉토리)은 제외
- 찾은 디렉토리 목록을 중복 제거 → check_dirs

**단일 앱** (check_dirs가 1개): 그대로 진행
**복수 앱** (check_dirs가 2개 이상): 각 앱별로 STEP 1-2 ~ STEP 2를 반복 실행. 한 앱이 실패해도 나머지 앱은 계속 진행. 결과 보고는 앱별로 구분하여 STEP 3에서 통합.
**check_dirs가 비어있음** (모두 앱 외부 파일): "검사 대상 앱이 없습니다." 출력 후 [STOP]

→ check_dir 확보 (복수 앱이면 순회)

### 1-2. 패키지 매니저 판별

`{check_dir}` 에서 lock 파일 존재 여부로 판별. 없으면 `{wt_root}` 까지 상위 탐색:

| lock 파일 | 패키지 매니저 | run_cmd | install_cmd |
|-----------|-------------|---------|-------------|
| `pnpm-lock.yaml` | pnpm | `pnpm run` | `pnpm install` |
| `yarn.lock` | yarn | `yarn run` | `yarn install` |
| `package-lock.json` 또는 위 둘 다 없음 | npm | `npm run` | `npm install` |

여러 lock 파일이 있으면 위 표 우선순위대로 (pnpm > yarn > npm).

→ run_cmd, install_cmd 확보

### 1-3. node_modules 확인

`{check_dir}/node_modules` 존재 여부 확인. 없으면 `{wt_root}/node_modules` 도 확인 (hoisted 설치).

둘 다 없으면: `cd {wt_root} && {install_cmd}` 실행 (루트에서 설치 — monorepo 호이스팅 대응).
설치 실패 시: 에러 출력 후 [STOP]
**복수 앱 순회 중이면 install은 최초 1회만** — 이후 앱에서는 node_modules 재확인만 한다.

### 1-4. 검사 명령어 매핑

`{check_dir}/package.json`의 scripts에서 아래 순서로 매핑 (앞에서 먼저 매칭되는 것 사용):

| 검사 | 후보 스크립트명 (우선순위순) |
|------|----------------------------|
| lint | `lint`, `eslint` |
| check-types | `check-types`, `type-check`, `typecheck`, `tsc` |
| test | `test`, `jest`, `vitest` |

매핑 결과를 사용자에게 표시:
```
앱: {check_dir의 wt_root 기준 상대경로}
환경: {패키지 매니저}
검사 항목:
- lint:        {매핑된 스크립트명 또는 "스킵 (스크립트 없음)"}
- check-types: {매핑된 스크립트명 또는 "스킵 (스크립트 없음)"}
- test:        {매핑된 스크립트명 또는 "스킵 (스크립트 없음)"}
```

3개 모두 스킵이면: "실행할 검사가 없습니다." 출력 후 해당 앱 스킵 (복수 앱이면 다음 앱으로, 단일 앱이면 [STOP])

---

## STEP 2: 순차 실행 + 자동 수정 루프

검사 순서: **lint → check-types → test**
(lint를 먼저 잡아야 type-check가 정확하고, type을 먼저 잡아야 test 실패 원인이 줄어든다)

**중요 — 선행 검사 재검증**: 다음 검사로 넘어가기 전, 직전 검사에서 코드 수정이 있었으면 이미 통과한 모든 검사를 순서대로 한번씩 재실행한다. 재실행에서 실패하면 해당 검사의 자동 수정 루프(2-2)로 진입한다. 재검증은 전체에서 최대 1회만 수행 — 재검증 중 수정이 발생해도 추가 재검증하지 않는다.

각 검사에 대해 (스킵 대상 제외):

### 2-1. 첫 실행

```
cd {check_dir} && {run_cmd} {script} 2>&1
```
- timeout 300초 (5분). 초과 시 해당 검사 **실패** ❌ — "타임아웃: {검사명}이 5분 내에 완료되지 않았습니다." 보고 후 2-3으로.
- exit 0 → 해당 검사 **통과 (수정 없음)** ✅ → 다음 검사로

### 2-2. 실패 시 자동 수정 루프 (최대 3회)

attempt = 0

**[루프 시작]** (attempt < 3)

attempt += 1

1. **에러 분석**:
   - 에러 출력에서 `파일경로:라인번호` + 에러메시지 파싱 시도
   - **파싱 불가** (설정 오류, 모듈 미설치, 구문 에러 등 파일:라인 형식이 아닌 경우):
     해당 검사 **실패** ❌ → 2-3으로 (자동 수정 불가한 환경 문제)

2. **파일 읽기**: 해당 파일을 Read (`{check_dir}/파일경로` 절대경로)

3. **수정 판단 및 적용**:

   | 검사 | 수정 전략 |
   |------|----------|
   | lint | `{check_dir}/package.json`의 lint 스크립트 내용을 확인하여 사용 중인 린터를 판별. eslint면 `cd {check_dir} && npx eslint --fix {파일들}`, biome이면 `cd {check_dir} && npx biome check --fix {파일들}` 시도. 자동수정 불가한 에러는 메시지 기반으로 직접 Edit |
   | check-types | 타입 에러 메시지(TS2xxx)를 분석하여 코드 수정. 타입 정의 누락이면 import/interface 추가, 타입 불일치면 코드 로직 수정 |
   | test | 실패 테스트의 expect/actual 비교 → **구현 코드를 수정** (테스트가 스펙이므로 테스트 코드 수정은 최후 수단) |

4. **재실행**: `cd {check_dir} && {run_cmd} {script} 2>&1` (timeout 300초)

5. exit 0 → **통과 (수정함)** ✅ → 루프 탈출, 다음 검사로

**[루프 끝]**

attempt >= 3 → 해당 검사 **실패** ❌ → 2-3으로

### 2-3. 검사 실패 시

남은 에러를 사용자에게 보고:
```
❌ {검사명} 실패 ({check_dir의 wt_root 기준 상대경로})
시도: {attempt}회
남은 에러:
{마지막 실행의 에러 출력}

수동 확인이 필요합니다.
```

**같은 앱의 이후 검사는 실행하지 않는다** — 선행 검사 실패 상태에서 후행 검사 결과는 신뢰할 수 없다.
복수 앱이면 다음 앱으로 계속 진행한다.

---

## STEP 3: 결과 보고

모든 앱의 모든 검사 통과 시:
```
┌──────────────────────────────────┐
│ 모든 검사 통과                    │
│ lint:        ✅ pass {수정여부}   │
│ check-types: ✅ pass {수정여부}   │
│ test:        ✅ pass {수정여부}   │
└──────────────────────────────────┘
```
- {수정여부}: 수정 없이 통과 → `(clean)`, 수정 후 통과 → `(fixed, {attempt}회 시도)`
- 스킵된 항목: `⏭ skip (스크립트 없음)`
- 복수 앱인 경우 앱별로 위 박스를 반복 출력

일부 앱 실패 시: 실패 앱 목록 + 통과 앱 목록을 함께 보고하고 [STOP]

전체 통과 시 AskUserQuestion으로 다음 선택지 제시:
```
검사를 모두 통과했습니다. 다음 중 선택하세요:
1. `/autopilot:merge {피처브랜치}` — 이 워크트리만 피처 브랜치에 머지
2. `/autopilot:merge-all {피처브랜치}` — 모든 활성 워크트리를 한번에 머지
3. 추가 작업 계속
```

[TERMINATE]
