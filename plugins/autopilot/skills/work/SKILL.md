---
name: autopilot-work
description: 새 세션에서 기존 워크트리에 추가/수정/삭제 작업 시 사용. 이슈 명세 재로드 없이 요구사항 기반으로 바로 플랜을 세운다.
---

# Worktree Work

**실행 주체: Main Session**
`{이슈키}.md`의 `## 설명` 섹션 수정 절대 금지 — Jira 원본 보존. 추가 요구사항은 `## 추가 요구사항` 섹션에만 append.

## 사용법
`/autopilot:work {이슈키} {요구사항}`

---

## 전제조건 — 워크트리 진입 (완료 전까지 아래로 절대 넘어가지 않는다)

1. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure_worktree.py {이슈키}` 실행
   성공: data.display를 사용자에게 그대로 출력. data.worktree_path, data.branch, data.issue_doc_root, data.base_branch 보관
   실패: reason 출력 후 [STOP]
2. `cd {data.worktree_path} && pwd && git branch --show-current` 실행하여 경로·브랜치 확인

**중요 — 경로 규칙**: Claude Bash 도구는 각 명령마다 새 셸을 생성한다.

| 작업 | 경로 |
|------|------|
| **코드** Read/Edit/Write/Glob/Grep | `{data.worktree_path}/파일경로` |
| **Bash/git** 명령 | `cd {data.worktree_path} && command` |

**⚠ `data.issue_doc_root`는 이슈 문서 접근 전용이다. 코드 파일에 이 경로를 사용하면 피처 브랜치에 직접 수정이 발생한다. 코드 작업은 반드시 `{data.worktree_path}/`만 사용한다.**

---

**이슈 명세 로드 금지**: `load_issue.py` 실행하지 않는다. 요구사항은 현재 대화에서 사용자가 직접 전달한 내용만 사용한다. 요구사항이 아직 없으면 이슈 명세 확인·추측·로드 금지 — 사용자가 다음 메시지로 전달할 때까지 대기한다.

## 작업 규칙

**영향 범위 분석** (플랜 작성 시):
1. {요구사항}에서 변경 예상 파일/컴포넌트/함수명 키워드 추출
2. `semantic_search_nodes_tool` 호출 (query: {키워드}, limit: 10)
3. 결과 있으면 `get_impact_radius_tool` 호출 (changed_files: 위 결과, max_depth: 2)
4. 실패/결과 없음 시 fallback: `cd {data.worktree_path} && rg {패턴}` 직접 탐색
5. 관련 파일 Read (`{data.worktree_path}/파일경로` 절대경로)
- code-review-graph 그래프 없음: 4번 fallback으로 진행

**커밋**: 구현 중 WIP 커밋하지 않는다. 커밋은 merge 단계에서 처리한다.

**구현 완료 후**: AskUserQuestion에 다음 선택지를 제시:
```
구현이 완료되었습니다. 다음 중 선택하세요:
1. `/autopilot:check` — lint, type-check, test 검사 실행 (오류 시 자동 수정)
2. `/autopilot:merge {피처브랜치}` — 이 워크트리만 피처 브랜치에 머지
3. `/autopilot:merge-all {피처브랜치}` — 모든 활성 워크트리를 한번에 머지
4. 추가 작업 계속
```
