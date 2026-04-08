# 충돌 해결 프로세스 (공유 절차)

**이 문서는 충돌 해결 절차만 담당한다. 실패/성공 후 동작(STOP, 건너뜀 등)은 호출한 스킬이 처리한다.**

## 변수

| 변수 | 설명 |
|------|------|
| `{resolve_root}` | 피처 브랜치가 체크아웃된 git 루트 경로 |
| `{피처브랜치}` | 머지 대상 피처 브랜치명 |
| `{branch}` | 머지 중인 워크트리 브랜치명 |

---

## 절차

### 1. 충돌 파일 목록 확보

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/show_conflicts.py
```

충돌 파일마다 아래 프로세스를 순서대로 진행한다.

---

### 2. 파일별 해결

각 충돌 파일에 대해:

```
[GATE] AskUserQuestion("충돌: {파일명}\n{diff}\n\n선택: [auto / feature / base / 직접편집]")
```

#### 응답 "auto"

1. 파일을 Read로 읽어 conflict marker(`<<<<<<< / ======= / >>>>>>>`)를 파악
2. 충돌 내용 요약 출력 (ours = 피처브랜치 / theirs = 워크트리브랜치 각각 무엇을 변경했는지)
3. 양쪽 변경 내용을 분석하여 적절히 병합:
   - 서로 다른 내용 추가 → 양쪽 모두 포함
   - 같은 부분을 다르게 수정 → 맥락상 더 적절한 쪽 선택 (이유 명시)
4. Edit으로 conflict marker를 제거하고 병합 결과 적용
5. `cd {resolve_root} && git diff -- '{파일명}'` 실행하여 병합 결과 diff 출력
6. `[GATE] AskUserQuestion("위 병합 결과를 확인하세요.\n\n확인: [ok / 직접편집]")`
   - 응답 "ok": `cd {resolve_root} && git add -- '{파일명}'` 실행
   - 응답 "직접편집": 아래 직접편집 흐름으로 이동

#### 응답 "feature"

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py '{파일}' feature
```

#### 응답 "base"

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py '{파일}' base
```

#### 응답 "직접편집"

```
[GATE] AskUserQuestion("편집 완료 후 'done' 입력")
```

사용자가 'done' 입력 시:
- `grep -Ec "^(<{7} |>{7} )" '{resolve_root}/{파일명}'` 실행
- exit 0 (마커 존재): "충돌 마커가 아직 남아있습니다." 출력 → [GATE] 반복
- exit 1 (마커 없음): `cd {resolve_root} && git add -- '{파일명}'` 실행

---

### 3. --continue 전 최종 마커 검사

```bash
cd {resolve_root} && git diff --name-only --cached
```

staged 파일 각각에 대해:
```bash
grep -lE "^(<{7} |>{7} )" '{resolve_root}/{파일명}'
```

마커가 남은 파일이 있으면:
```
"아직 충돌 마커가 남아있는 파일: {목록}" 출력
```
→ **호출 스킬의 실패 처리로 이동** (STOP 또는 건너뜀)

---

### 4. merge --continue

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --branch {branch} --continue
```

- exit 0: 충돌 해결 완료 → 호출 스킬의 성공 처리로 이동
- exit 2: 다음 충돌 파일 → 2번 절차 반복
- exit 1: 오류 → **호출 스킬의 실패 처리로 이동**
