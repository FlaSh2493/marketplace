---
name: end
description: (명시적 커맨드 실행 전용) /autopilot:end 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# Worktree End

워크트리를 제거하고 로컬 브랜치를 삭제한다.

## 사용법
`/autopilot:end {브랜치명}`

---

## STEP 1: 워크트리 제거 시도

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/remove_worktree.py $ARGUMENTS
```

결과 처리:
- `status: ok` → `data.display` 내용을 그대로 출력 후 [STOP]
- `status: error` → `data.reason` 내용을 에러로 출력 후 [STOP]
- `status: dirty` → STEP 2 진행

---

## STEP 2: 미커밋 변경 확인

아래 형식으로 변경 파일 목록을 출력한다:

```
워크트리에 커밋되지 않은 변경사항이 있습니다:
{files 배열의 각 항목을 줄바꿈으로 출력}
```

AskUserQuestion으로 강제 진행 여부를 묻는다:
- "강제 제거" → STEP 3 진행
- "취소" → [STOP]

---

## STEP 3: 강제 제거

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/remove_worktree.py $ARGUMENTS --force
```

결과 처리:
- `status: ok` → `data.display` 내용을 그대로 출력 후 [STOP]
- `status: error` → `data.reason` 내용을 에러로 출력 후 [STOP]
