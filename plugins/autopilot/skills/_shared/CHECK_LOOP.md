# 검증 실행 루프 (공유 절차)

**이 문서는 lint → check-types → test 순차 실행 + 자동 수정만 담당한다.**
**전후 동작(복수 앱 순회, 성공/실패 후 분기)은 호출한 스킬 또는 에이전트가 처리한다.**

## 입력 변수

| 변수 | 설명 |
|------|------|
| `{check_dir}` | 검사를 실행할 앱 디렉토리 |
| `{run_cmd}` | 패키지매니저 run 명령 (예: `pnpm run`) |
| `{checks}` | 검사별 스크립트 매핑 (예: lint→"lint", check-types→"check-types", test→"test") |

---

## 검사 순서

**lint → check-types → test**

lint를 먼저 잡아야 type-check가 정확하고, type을 먼저 잡아야 test 실패 원인이 줄어든다.

---

## 각 검사 절차

스킵 대상(`{checks}`에 해당 키 없음)은 건너뛴다.

### 1. 첫 실행

```bash
cd {check_dir} && {run_cmd} {script} 2>&1
```

- timeout 300초. 초과 시 해당 검사 **실패** ❌ — "타임아웃: {검사명}이 5분 내에 완료되지 않았습니다."
- exit 0 → 해당 검사 **통과 (수정 없음)** ✅ → 다음 검사로

### 2. 실패 시 자동 수정 루프 (최대 3회)

attempt = 0

**[루프 시작]** (attempt < 3)

attempt += 1

1. **에러 분석**: 에러 출력에서 `파일경로:라인번호` + 에러메시지 파싱 시도
   - **파싱 불가** (설정 오류, 모듈 미설치, 구문 에러 등): 해당 검사 **실패** ❌ → 3번으로

2. **파일 읽기**: `{check_dir}/파일경로` 절대경로로 Read

3. **수정 판단 및 적용**:

   | 검사 | 수정 전략 |
   |------|----------|
   | lint | package.json lint 스크립트로 린터 판별. eslint면 `cd {check_dir} && npx eslint --fix {파일들}`, biome이면 `cd {check_dir} && npx biome check --fix {파일들}`. 자동수정 불가 에러는 메시지 기반으로 직접 Edit |
   | check-types | 타입 에러 메시지(TS2xxx) 분석하여 코드 수정. 타입 정의 누락이면 import/interface 추가, 타입 불일치면 코드 로직 수정 |
   | test | 실패 테스트의 expect/actual 비교 → **구현 코드 수정** (테스트가 스펙이므로 테스트 코드 수정은 최후 수단) |

4. **재실행**: `cd {check_dir} && {run_cmd} {script} 2>&1` (timeout 300초)

5. exit 0 → **통과 (수정함)** ✅ → 루프 탈출, 다음 검사로

**[루프 끝]**

attempt >= 3 → 해당 검사 **실패** ❌ → 3번으로

### 3. 검사 실패 확정

같은 앱의 이후 검사는 실행하지 않는다 — 선행 검사 실패 상태에서 후행 검사 결과는 신뢰할 수 없다.

실패 정보를 보관:
```
{
  "name": "{검사명}",
  "attempt": {attempt},
  "last_error": "{마지막 실행의 에러 출력 전문}"
}
```

---

## 선행 검사 재검증

다음 검사로 넘어가기 전, 직전 검사에서 코드 수정이 있었으면 이미 통과한 모든 검사를 순서대로 한 번씩 재실행한다.

- 재검증은 전체에서 **최대 1회**만 수행 — 재검증 중 수정이 발생해도 추가 재검증하지 않는다.
- 재검증에서 실패하면 해당 검사의 자동 수정 루프(2번)로 진입한다.

---

## 완료 결과 형식

```json
{
  "passed": ["lint", "check-types", "test"],
  "failed": [
    {
      "name": "check-types",
      "attempt": 3,
      "last_error": "src/Cart.tsx:42 - error TS2322: ..."
    }
  ],
  "fixed_files": ["src/Cart.tsx", "src/utils/format.ts"],
  "skipped": ["test"]
}
```
