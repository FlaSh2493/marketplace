---
name: plan
description: (명시적 커맨드 실행 전용) /autopilot:plan 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# Deep Plan

## Step 1. 준비

1. `resolve_worktree.py`로 작업 환경(`data.worktree_path`)을 확인한다.
2. 이슈를 로드한다:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/plan/scripts/load_issue.py {data.issue} \
     --sections 배경,목표,비목표,요구사항,인수 조건,참고,제약/고려사항
   ```
3. 플랜 템플릿을 읽는다: `${CLAUDE_PLUGIN_ROOT}/skills/plan/templates/template.md`

## Step 2. 분석

`reference/workflow.md`의 순서대로 탐색·설계를 진행한다.

## Step 3. 작성

1. `EnterPlanMode`를 호출하여 Step 1에서 읽은 `template.md` 형식으로 플랜을 작성한다.
2. 작성이 완료되면 `ExitPlanMode`를 호출한다 → `filePath` 확보.
3. **Step 4로 이동한다.**

## Step 4. 검토 (루프)

`AskUserQuestion`으로 아래를 묻는다 (버튼: **저장**, **수정**):

> "플랜을 검토해주세요."

- **저장** → Step 5로 이동한다.
- **수정** → 멈춘다. 사용자가 수정 내용을 말하면 `EnterPlanMode`로 재진입하여 수정하고, `ExitPlanMode` 호출 후 Step 4를 반복한다.

## Step 5. 저장

아래 스크립트로 plan.md에 복사한다:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/plan/scripts/save_plan.py \
  "{exitPlanMode.filePath}" "{data.root_path}/.docs/tasks/{data.issue}/plan.md"
```

완료 후 아래 메시지를 출력하고 **종료한다**:

> "✅ 플랜 저장 완료: `.docs/tasks/{data.issue}/plan.md`
> 구현을 시작하려면 `/autopilot:build`를 실행하세요."

이후 어떤 구현도 수행하지 않는다.
