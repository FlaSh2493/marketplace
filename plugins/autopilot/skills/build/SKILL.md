---
name: autopilot-build
description: /autopilot:plan 이 생성한 {이슈키}/plan.md 를 읽어 구현만 수행한다. 이슈 명세 재로드와 코드 탐색(semantic_search, impact_radius, 이미지 재분석)을 생략하여 컨텍스트를 최소화한다. 플랜이 없으면 plan 스킬을 먼저 실행하도록 안내한다.
---

# Worktree Build

**실행 주체: Main Session**
`{이슈키}.md`의 `## 설명` 섹션 수정 절대 금지 — Jira 원본 보존. 추가 요구사항은 `## 추가 요구사항` 섹션에만 append.

이 스킬은 **plan.md 기반 구현만** 담당한다. 이슈 명세 재로드·코드 탐색·이미지 재분석을 금지하여 토큰을 최소화한다.

## 사용법
```
/autopilot:build {브랜치명}
/autopilot:build                  ← 워크트리 내에서 실행 시 현재 브랜치 자동 감지
```

---

## 전제조건 (완료 전까지 아래로 절대 넘어가지 않는다)

### 1. 브랜치·워크트리 resolve

브랜치명이 주어지지 않았으면 `cd $(pwd) && git branch --show-current` 로 현재 브랜치를 확보한다.

`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure_worktree.py {브랜치명}` 실행
- 기존 워크트리가 있으면 멱등하게 메타데이터만 반환
- `data.worktree_path`, `data.branch`, `data.issue_doc_root`, `data.issues` 보관
- 실패 시 reason 출력 후 [STOP]

상태 초기화:
```bash
main_root=$(git worktree list | head -1 | awk '{print $1}')
state_dir="$main_root/.docs/task/{data.branch}/.state"
mkdir -p "$state_dir"
rm -f "$state_dir/build" "$state_dir/check" "$state_dir/check-all" "$state_dir/merge" "$state_dir/merge-all" "$state_dir/pr" "$state_dir/review-fix"
```

`cd {data.worktree_path} && pwd && git branch --show-current` 로 경로·브랜치 확인.

### 2. plan.md 존재 검증

plan 파일 경로: `{data.issue_doc_root}/.docs/task/{data.branch}/{data.issues[0]}/plan.md`
(다중 이슈 시 각 이슈키로 경로 구성하여 각각 검증)

파일이 없으면 아래 메시지를 출력하고 [STOP]:
```
[STOP] 플랜 파일이 없습니다: {예상경로}
먼저 /autopilot:plan {data.branch} 를 실행하여 플랜을 작성하세요.
```

### 3. plan.md 로드

Read 로 plan.md 를 읽어 frontmatter 와 본문을 컨텍스트로 보관한다.
- frontmatter: `branch`, `issues`, `base_branch`, `worktree_path`, `spec_mode`
- frontmatter 의 `worktree_path` 가 1단계에서 얻은 `data.worktree_path` 와 다르면 plan.md 의 값을 우선 신뢰(워크트리가 다른 경로에 복구된 경우 대비).
- 본문의 섹션 구조는 plan 스킬 템플릿을 따른다.

---

## 경로 규칙 (Bash는 매 호출마다 새 셸 — 매번 cd prefix 필수)

| 작업 | 경로 |
|------|------|
| **이슈 문서** 읽기/수정 | `{data.issue_doc_root}/{이슈키}.md` |
| **plan.md** 읽기 | `{data.issue_doc_root}/.docs/task/{data.branch}/{이슈키}/plan.md` |
| **코드** Read/Edit/Write | `{data.worktree_path}/파일경로` |
| **Bash/git** 명령 | `cd {data.worktree_path} && command` |

**⚠ 코드 편집은 반드시 `{data.worktree_path}/` 하위만 대상으로 한다. `data.issue_doc_root`(피처 브랜치) 아래 코드 파일을 수정하지 않는다.**

---

## 구현 중 금지 사항 (토큰 절감 핵심)

이 스킬의 목적은 plan.md 를 신뢰하여 추가 탐색 없이 구현하는 것. 아래 행위를 **하지 않는다**:

- `load_issue.py` 재호출 금지 — plan.md "요구사항 요약" 만 참조
- `semantic_search_nodes_tool` / `get_impact_radius_tool` 재호출 금지 — plan.md "대상 파일" 만 참조
- 이슈 이미지 재-Read 금지 — plan.md "화면 분석" 텍스트만 참조 (※ 단, "구현 완료 후 이미지 재확인" 단계는 예외)
- plan.md "대상 파일" 섹션에 없는 파일을 선제적으로 열거·검색 금지
  - 구현 중 꼭 추가 파일이 필요하다고 판단되면 사용자에게 보고하고 `/autopilot:plan {브랜치명} --replan` 을 제안한다

---

## 구현

1. plan.md "구현 순서" 를 따라 "대상 파일" 의 파일만 Read/Edit/Write 한다.
2. 파일 경로는 항상 `{data.worktree_path}/파일경로` 로 지정한다.
3. Bash 명령은 매번 `cd {data.worktree_path} && ...` 로 시작한다.
4. **WIP 커밋 금지**. 커밋은 merge 단계에서 일괄 처리한다.

---

## 구현 완료 후 이미지 재확인

plan.md 에 `## 이미지 목록` 섹션이 있으면:
1. 해당 경로의 이미지를 Read 로 열어 구현 결과와 대조
2. 대조 항목:
   - 레이아웃·구조 일치 여부
   - 컴포넌트 구성 누락 여부
   - 텍스트·라벨·상태값 일치 여부
3. 불일치 항목이 있으면 해당 부분 재작업 → 다시 대조. 모두 일치할 때까지 반복.
4. 일치하면 `✅ 이미지 대조 완료 — 일치` 출력 후 진행.

`## 이미지 목록` 섹션이 없으면 이 단계를 스킵.

---

## 완료 안내

완료 마커
  Write: `{state_dir}/build` (빈 파일)

AskUserQuestion 으로 다음 선택지를 제시:

```
구현이 완료되었습니다. 다음 중 선택하세요:
1. /autopilot:check — lint, type-check, test 검사 실행 (오류 시 자동 수정)
2. /autopilot:merge {피처브랜치} — 이 워크트리만 피처 브랜치에 머지
3. /autopilot:merge-all {피처브랜치} — 모든 활성 워크트리를 한번에 머지
4. 추가 작업 계속
```
