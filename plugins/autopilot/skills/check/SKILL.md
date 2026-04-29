---
name: check
description: (명시적 커맨드 실행 전용) /autopilot:check 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# Token-Efficient Verification Harness

**실행 주체: Main Session**

## 사용법
`/autopilot:check [branch]`

---

## STEP 1: 컨텍스트 및 설정 로드

1. **워크트리 확인**:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_worktree.py {branch}
   ```
   - `data.worktree_path` -> `wt_root`
   - `data.issue` -> `issue_key`

2. **검증 설정 로드**:
   `.docs/tasks/{issue_key}/verify-config.json` 파일을 확인한다.
   없을 경우 자동 탐지 실행:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/detect_commands.py {wt_root} --out .docs/tasks/{issue_key}/verify-config.json
   ```

3. **변경 파일 파악**:
   최근 Build 작업에서 변경된 파일 목록을 확보한다. (기록이 없으면 `git diff --name-only` 활용)

---

## STEP 2: 순차적 검증 실행

설정된 `lint` -> `check-types` -> `test` 순서로 실행한다.

### 2.1: Lint 실행 (가장 빠름)
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/run_check.py lint "{config.lint}" --cwd {wt_root}
```

- `passed == true`: 다음 단계(check-types)로 진행.
- `passed == false`: **STEP 3 (Fix 루프)** 진입.

### 2.2: Check-types 실행 (TypeScript)
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/run_check.py check-types "{config.check-types}" --cwd {wt_root}
```

- `passed == true`: 다음 단계(Test)로 진행.
- `passed == false`: **STEP 3 (Fix 루프)** 진입.

### 2.3: Test 실행
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/run_check.py test "{config.test}" --cwd {wt_root}
```

- `passed == true`: 모든 검증 완료.
- `passed == false`: **STEP 3 (Fix 루프)** 진입.

---

## STEP 3: 자동 Fix 루프 (최대 3회)

검증 실패 시 다음 절차를 따른다:

1. **에러 분석 요청**:
   `templates/fix-prompt.md`를 사용하여 Claude에게 수정을 요청한다.
   - 실패한 도구의 JSON 결과 (`errors`, `error_count`)를 프롬프트에 포함.
   - 대상 파일의 현재 내용을 함께 제공.

2. **수정 적용**:
   Claude가 제안한 수정 사항을 파일에 반영한다.

3. **재검증**:
   실패했던 단계부터 다시 실행한다.

4. **종료 조건**:
   - 모든 검증 통과 -> **STEP 4** 진행.
   - 3회 시도 후에도 실패 -> 사용자에게 보고 후 중단.

---

## STEP 4: 결과 보고

검증 결과를 요약하여 출력한다.

- 모든 검사 통과: `✅ All checks passed`
- 실패 시: 실패한 도구와 남은 에러 개수 보고.

---

## 행동 규율 (CRITICAL)

1. **직접 분석 금지**: 검증 도구 출력을 직접 읽고 판단하지 마라. 오직 `run_check.py`가 뱉는 JSON 결과만 신뢰한다.
2. **우회 수정 금지**: `as any`, `@ts-ignore`, 린트 비활성화 주석 등을 사용하여 에러를 "가리는" 행위는 엄격히 금지된다.
3. **범위 준수**: Plan과 Build 산출물 외의 코드를 수정하지 마라.
4. **횟수 제한**: Fix 시도는 횟수(3회)를 엄격히 지킨다.
