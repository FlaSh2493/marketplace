---
name: work
description: 새 세션에서 기존 워크트리에 추가/수정/삭제 작업 시 사용. 이슈 명세 재로드 없이 요구사항 기반으로 바로 플랜을 세운다.
---

# Worktree Work

**실행 주체: Main Session**
`{이슈키}.md`의 `## 설명` 섹션 수정 절대 금지 — Jira 원본 보존. 추가 요구사항은 `## 추가 요구사항` 섹션에만 append.

## 사용법
`/worktree-flow:work {이슈키} {요구사항}`

---

## 전제조건 — 워크트리 진입 (완료 전까지 아래로 절대 넘어가지 않는다)

1. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure_worktree.py {이슈키}` 실행
   성공: data.worktree_path, data.branch, data.root_path, data.main_branch 보관
   실패: reason 출력 후 [STOP]
2. `cd {data.worktree_path} && pwd && git branch --show-current` 실행하여 경로·브랜치 확인

**중요**: Claude Bash 도구는 각 명령마다 새 셸을 생성하므로, 이후 모든 작업에서:
- 파일 작업: `{data.worktree_path}/` prefix 절대경로 사용
- Bash/git 명령: 매번 `cd {data.worktree_path} && command` 형태로 실행

---

## 작업 규칙

**영향 범위 분석** (플랜 작성 시):
1. {요구사항}에서 변경 예상 파일/컴포넌트/함수명 키워드 추출
2. `semantic_search_nodes_tool` 호출 (query: {키워드}, limit: 10)
3. 결과 있으면 `get_impact_radius_tool` 호출 (changed_files: 위 결과, max_depth: 2)
4. 실패/결과 없음 시 fallback: `cd {data.worktree_path} && rg {패턴}` 직접 탐색
5. 관련 파일 Read (`{data.worktree_path}/파일경로` 절대경로)
- code-review-graph 그래프 없음: "code-review-graph 그래프가 없습니다. /worktree-flow:init 을 먼저 실행하세요." 출력 후 [STOP]

**요구사항 추가/수정** 발생 시:
Edit 도구로 `{root_path}/.docs/task/{main_branch}/{이슈키}/{이슈키}.md` 끝에 추가:
```
## 추가 요구사항

{내용}
```
(이미 `## 추가 요구사항` 섹션이 있으면 해당 섹션 끝에 append)

**커밋**: 구현 중 WIP 커밋하지 않는다. 커밋은 merge 단계에서 처리한다.
