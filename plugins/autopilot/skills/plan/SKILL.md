---
name: plan
description: (명시적 커맨드 실행 전용) /autopilot:plan 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# 플랜 작성

이슈 명세를 분석해 Phase별 구현 계획을 작성한다.

## 사용법
`/autopilot:plan {이슈키}`

## 흐름 개요

```
STEP 1  환경 확인 + 이슈 로드
STEP 2  코드베이스 분석
STEP 3  plan.md 작성
STEP 4  [GATE] 검토
STEP 5  완료
```

---

## STEP 1: 환경 확인 + 이슈 로드

1. `resolve_worktree.py`로 작업 환경(`data.worktree_path`)을 확인한다.
2. 이슈를 로드한다:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/plan/scripts/load_issue.py {data.issue} \
     --sections 배경,목표,비목표,요구사항,인수 조건,참고,제약/고려사항
   ```
3. 플랜 템플릿을 읽는다: `${CLAUDE_PLUGIN_ROOT}/skills/plan/templates/template.md`

---

## STEP 2: 분석

`reference/workflow.md`의 순서대로 탐색·설계를 진행한다.

---

## STEP 3: 작성

Write 도구로 `{data.root_path}/.docs/tasks/{data.issue}/plan.md`에 STEP 1에서 읽은 `template.md` 형식으로 플랜을 작성한다.

---

## STEP 4: [GATE] 검토

AskUserQuestion으로 아래를 묻는다 (버튼: **저장**, **수정**):

> "플랜을 검토해주세요."

- **저장** → STEP 5로 이동한다.
- **수정** → 멈춘다. 사용자가 수정 내용을 말하면 Write 도구로 `plan.md`를 덮어쓰고 STEP 4를 반복한다.

---

## STEP 5: 완료

아래 메시지를 출력하고 종료한다:

> "✅ 플랜 저장 완료: `.docs/tasks/{data.issue}/plan.md`
> 구현을 시작하려면 `/autopilot:build`를 실행하세요."

이후 어떤 구현도 수행하지 않는다.
