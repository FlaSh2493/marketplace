---
name: autopilot-plan
description: 워크트리를 생성하고 이슈 명세를 로드하여 플랜 및 구현을 진행한다. 이슈는 여러 개 지정 가능하며 상호 영향을 고려한 통합 플랜을 수립한다. --no-spec 플래그를 사용하면 명세 로드 없이 사용자 요구사항 기반으로 작업한다. 추가 수정 요청 시 컨텍스트를 유지하며 반복한다.
---

# Worktree Plan

**실행 주체: Main Session**
`{이슈키}.md`의 `## 설명` 섹션 수정 절대 금지 — Jira 원본 보존. 추가 요구사항은 `## 추가 요구사항` 섹션에만 append.

## 사용법
```
/autopilot:plan {브랜치명} [이슈키1 이슈키2 ...] [--no-spec]
```
- 이슈키 필수. 생략 시 로컬 이슈 목록에서 선택
- `--no-spec` 없음: 이슈 명세 로드 후 플랜 수립
- `--no-spec` 있음: 명세 로드 없이 사용자 요구사항 기반으로 작업

---

## 전제조건 — 워크트리 진입 (완료 전까지 아래로 절대 넘어가지 않는다)

1. 이슈키가 없으면:
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/list_issues.py` 실행
   성공: 이슈 목록 출력 후 AskUserQuestion("작업할 이슈키를 선택하세요 (여러 개면 공백으로 구분):\n{목록}")
   실패 또는 목록 비어있음: AskUserQuestion("작업할 이슈키를 입력하세요 (여러 개면 공백으로 구분):")
   입력받은 값을 이슈키로 사용

2. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure_worktree.py {브랜치명} --issues {이슈키1} [이슈키2...]`
   성공: data.display를 사용자에게 그대로 출력. data.worktree_path, data.branch, data.issue_doc_root, data.base_branch, data.issues 보관
   실패: reason 출력 후 [STOP]
3. `cd {data.worktree_path} && pwd && git branch --show-current` 실행하여 경로·브랜치 확인

**경로 규칙** (Bash는 매 호출마다 새 셸 — 매번 cd prefix 필수):

| 작업 | 경로 |
|------|------|
| **이슈 문서** 읽기/수정 | `load_issue.py`가 반환한 `md_path` |
| **코드** Read/Edit/Write/Glob/Grep | `{data.worktree_path}/파일경로` |
| **Bash/git** 명령 | `cd {data.worktree_path} && command` |

**⚠ `data.issue_doc_root`는 이슈 문서 전용. 코드 파일에 사용하면 피처 브랜치에 직접 수정된다. 코드는 반드시 `{data.worktree_path}/`만 사용한다.**

---

## 이슈 로드

`--no-spec` 플래그가 있으면 이 섹션 전체 스킵 — 사용자가 다음 메시지로 요구사항을 전달할 때까지 대기.

`--no-spec` 없으면 `data.issues`의 각 이슈키별로 순차 실행:
```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키} --sections 설명,메타데이터
```
성공: 내용을 컨텍스트로 보관
실패: reason 출력 후 [STOP]

이슈가 여러 개면 전체 명세를 합쳐 컨텍스트에 유지한다.

---

## 작업 규칙

### 플랜 작성 규칙

**1. 공통 컴포넌트 우선** — 새 컴포넌트 작성 전 `semantic_search_nodes_tool` 또는 Grep으로 기존 컴포넌트 탐색. 사용할 컴포넌트명·경로·활용 방식을 플랜에 명시.

**2. 이미지 분석** (이미지 제공 시) — 디자인시스템 컴포넌트 매핑, 레이아웃 구조, spacing/color 토큰을 플랜에 명시. (예: `버튼 → <Button variant='primary'>`, `간격 → gap-4`)

**3. 파일 충돌 명시** (이슈 여러 개인 경우) — 동일 파일을 수정하는 이슈가 있으면 통합 처리 또는 순서 분리 방안을 플랜에 명시.

**4. 구현 순서** — 이슈 간 의존 관계가 있으면 선행 이슈 먼저 구현하도록 순서 명시.

**영향 범위 분석** (플랜 작성 시):
1. 이슈 명세 또는 요구사항에서 키워드 추출 → `semantic_search_nodes_tool` (limit: 10)
2. 결과 있으면 `get_impact_radius_tool` (changed_files: 위 결과, max_depth: 2)
3. 결과 없으면 fallback: `cd {data.worktree_path} && rg {패턴}`

관련 파일 Read 시 반드시 `{data.worktree_path}/파일경로` 사용 (도구 결과가 메인 경로를 반환해도 워크트리 경로로 치환).

**커밋**: 구현 중 WIP 커밋하지 않는다. 커밋은 merge 단계에서 처리한다.

**구현 완료 후**: AskUserQuestion에 다음 선택지를 제시:
```
구현이 완료되었습니다. 다음 중 선택하세요:
1. `/autopilot:check` — lint, type-check, test 검사 실행 (오류 시 자동 수정)
2. `/autopilot:merge {피처브랜치}` — 이 워크트리만 피처 브랜치에 머지
3. `/autopilot:merge-all {피처브랜치}` — 모든 활성 워크트리를 한번에 머지
4. 추가 작업 계속
```
