---
name: plan
description: 이슈 워크트리를 생성하고 이슈 명세를 로드하여 플랜 및 구현을 진행한다. 추가 수정 요청 시 컨텍스트를 유지하며 반복한다.
---

# Worktree Plan

**실행 주체: Main Session**
`{이슈키}.md`의 `## 설명` 섹션 수정 절대 금지 — Jira 원본 보존. 추가 요구사항은 `## 추가 요구사항` 섹션에만 append.

## 사용법
`/worktree-flow:plan {이슈키}`

---

## 전제조건 — 워크트리 진입 (완료 전까지 아래로 절대 넘어가지 않는다)

1. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure_worktree.py {이슈키}` 실행
   성공: data.worktree_path, data.branch, data.root_path, data.base_branch 보관
   실패: reason 출력 후 [STOP]
2. `cd {data.worktree_path} && pwd && git branch --show-current` 실행하여 경로·브랜치 확인

**중요**: Claude Bash 도구는 각 명령마다 새 셸을 생성하므로, 이후 모든 작업에서:
- 파일 작업: `{data.worktree_path}/` prefix 절대경로 사용
- Bash/git 명령: 매번 `cd {data.worktree_path} && command` 형태로 실행

---

## 이슈 로드

`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키} --sections 설명,메타데이터` 실행
성공: 내용을 컨텍스트로 보관
실패: reason 출력 후 [STOP]

---

## 작업 규칙

**영향 범위 분석** (플랜 작성 시):
1. 이슈 명세에서 변경 예상 파일/컴포넌트/함수명 키워드 추출
2. `semantic_search_nodes_tool` 호출 (query: {키워드}, limit: 10)
3. 결과 있으면 `get_impact_radius_tool` 호출 (changed_files: 위 결과, max_depth: 2)
4. 실패/결과 없음 시 fallback: `cd {data.worktree_path} && rg {패턴}` 직접 탐색
5. 관련 파일 Read (`{data.worktree_path}/파일경로` 절대경로)
- code-review-graph 그래프 없음: 4번 fallback으로 진행

**커밋**: 구현 중 WIP 커밋하지 않는다. 커밋은 merge 단계에서 처리한다.
