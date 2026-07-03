---
name: cruise-result
description: (명시적 커맨드 실행 전용) /cruise:result 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Result

task 종료 시점(pr/review 이후)에 **회고 산출물 result.md 1개를 작성·덮어쓴다.**
이 파일은 외부 소비자(brain-sync 등)가 task를 지식으로 변환할 때 가장 먼저 읽는 고신호 단일 소스다.

> **종료 규칙:** 어떤 STEP에서 종료하든 Write 도구로 `~/Documents/tasks/{KEY}/result.md` 를
> **덮어쓰기**(append 아님) 기록하고 [STOP]한다.
> - frontmatter 공통 9필드 + result 전용 필드 완비
> - 본문은 고정 H2 헤딩을 그대로 사용 (소비자 파싱 계약)
> - 산출물 스키마는 `plugins/cruise/CONTRACT.md` (contract_version 1) 를 따른다

> **금지:**
> - **하네스 고유 어휘만 사용한다.** Pattern/Decision/Incident/Technology 를 frontmatter *필드명*이나
>   본문 헤딩으로 쓰지 않는다 (Brain 구조 비의존). 단 `## 어려웠던 점 / 실패` 불릿의 `[incident]` 접두만 허용.
> - 산출물 작성 후 요약·다음 액션 추천·후속 작업 제안 일체 출력하지 않는다 ("완료" 한 줄만).
> - 사용자가 명시적으로 요청하지 않은 어떤 액션도 수행하지 않는다. 다른 스킬을 자동 호출하지 않는다.
> - `*.archive/` 디렉토리는 읽지 않는다.

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

`key`, `key_source`, `branch`, `repo` 등을 메모리에 보관한다.

---

## STEP 2 — 결정적 필드 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/result/scripts/gather.py {KEY}
```

출력 JSON: `key, key_source, summary, branch, repo, base_branch, base_source,
pr_url, pr_number, commits_count, outcome, feature, feature_slug, feature_trusted,
worktree, issue_keys, artifacts_present, created_existing, now`.

- 이 값들은 (live git + 형제 산출물)에서 결정적으로 추출된 것이다. **그대로 frontmatter에 복사**한다.
- `created`: `created_existing` 이 비어있지 않으면 그 값을 유지, 비어있으면 `now`. `updated`: 항상 `now`.
- `outcome`: gather가 제안한 값을 기본으로 하되, 명백히 틀리면 LLM이 보정한다.
- **`feature`/`worktree`/`issue_keys` 는 절대 수정·추측하지 않는다.** gather 출력을 그대로 쓴다.
  gather는 **이 task의 체크아웃에서 신뢰 가능한 base(base_source∈{pr,upstream,reflog})일 때만** feature를 동결하고,
  아니면 `feature: ""`(=unassigned)로 둔다. LLM이 비어있는 feature를 임의로 채우지 않는다 (정확성 우선·추측 금지).

---

## STEP 3 — 회고 종합 (LLM 작업)

다음 입력을 읽어 본문 학습을 종합한다:
- `~/Documents/tasks/{KEY}/task.md` (배경·목표)
- `summary.md` (`## 개요`, 변경 요약) — 있으면
- `build.md` (Run 로그에서 시도/문제) — 있으면
- `check.md` / `review.md` (검사·리뷰에서 드러난 문제) — 있으면

본문 H2 헤딩별로 채운다 (헤딩 텍스트는 변경 금지):
- `## 결과` — 1~3문장, 무엇이 나왔고 최종 상태.
- `## 잘된 점` — 재사용 가능한 기법 1개 = 불릿 1개.
- `## 어려웠던 점 / 실패` — 문제/회귀/롤백. 운영급 사고면 불릿 앞에 `[incident]`.
- `## 결정` — `<결정> — because <이유> (rejected: <대안>)` 형식. 대안 없으면 `(rejected: 없음)`.
- `## 사용 기술` — `` `tech` — 어디에 왜 `` . frontmatter `technologies` 는 여기 등장한 기술의 소문자 슬러그 평문 배열.
- `## 후속 작업` — 미룬 TODO. 없으면 섹션 자체를 생략.

학습할 내용이 없는 섹션은 `- 없음` 한 줄로 둔다 (헤딩은 유지).

템플릿: `${CLAUDE_PLUGIN_ROOT}/skills/result/templates/result.md`

---

## STEP 4 — result.md 저장

Write 도구로 `~/Documents/tasks/{KEY}/result.md` 를 **항상 덮어쓰기** 저장한다.

frontmatter (공통 9필드 + result 전용):

```yaml
---
key: {KEY}
key_source: {key_source}
skill: result
summary: {gather.summary}
branch: {branch}
repo: {repo}
status: completed
created: {created_existing 있으면 유지, 없으면 now}
updated: {now}
tags: []
outcome: {shipped | merged | abandoned | in-progress}
base_branch: {base_branch}
base_source: {base_source}
pr_url: "{pr_url}"
pr_number: {pr_number 또는 null}
commits_count: {commits_count}
feature: "{gather.feature}"          # gather 출력 그대로. "" 면 unassigned (비우기)
worktree:
  kind: "{gather.worktree.kind}"     # worktree | branch | ""
  name: "{gather.worktree.name}"
issue_keys: [{gather.issue_keys}]
technologies: [{소문자 슬러그 평문 배열}]
artifacts_present: [{gather.artifacts_present}]
---
```

"완료" 한 줄 출력 후 [STOP].
