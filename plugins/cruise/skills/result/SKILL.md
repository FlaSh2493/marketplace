---
name: cruise-result
description: (명시적 커맨드 실행 전용) /cruise:result 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Result

task 종료 시점(pr/review 이후)에 **회고 산출물 result.md 1개를 작성·덮어쓴다.**
task의 결과·교훈·결정을 담는 고신호 요약이다. 소비자(예: `/cruise:log` 가 Jira 이슈 댓글에 회고를 포함)는
CONTRACT.md §5 스키마만 보고 이 파일을 읽는다.

> **종료 규칙:** 어떤 STEP에서 종료하든 `{task_dir}/result.md` 를 **덮어쓰기**(append 아님)
> 기록하고 [STOP]한다. `{task_dir}` = `context.py` 의 `task_path` 의 디렉토리 (리터럴 경로를 쓰지 않는다).
> - frontmatter 공통 5필드 + result 전용 필드 완비
> - 본문은 고정 H2 헤딩을 그대로 사용 (소비자 파싱 계약)
> - 산출물 스키마는 `plugins/cruise/CONTRACT.md` (§5, contract_version 8) 를 따른다

> **금지:**
> - 상태 한 줄 + 산출물 링크 외에 요약·다음 액션 추천·후속 작업 제안 일체 출력하지 않는다.
> - 사용자가 명시적으로 요청하지 않은 어떤 액션도 수행하지 않는다. 다른 스킬을 자동 호출하지 않는다.
> - `*.archive/` 디렉토리는 읽지 않는다.

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

`branch`, `repo` 등을 메모리에 보관한다.

---

## STEP 2 — 결정적 필드 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/result/scripts/gather.py {KEY}
```

출력 JSON: `summary, branch, repo, outcome, now`.

- 이 값들은 (live git + 형제 산출물 + gh)에서 결정적으로 추출된 것이다. **그대로 frontmatter에 복사**한다.
- `updated`: 항상 `now`.
- `outcome`: gather가 제안한 값을 기본으로 하되, 명백히 틀리면 LLM이 보정한다.
- PR·커밋·이슈키 등은 frontmatter에 담지 않는다 — 소비자가 `gh`/git·본문에서 파생한다.

---

## STEP 3 — 회고 종합 (LLM 작업)

다음 입력을 읽어 본문 학습을 종합한다:
- `{task_dir}/task.md` (배경·목표)
- `plan.md` `## 개정 이력` — **요구사항이 언제·왜 바뀌었나.** 시도했다가 되돌린 것이 여기만 남아
  있으므로 `## 결정`(rejected 대안)·`## 어려웠던 점`(방향 전환·반복 개정)의 핵심 재료다
- `plan.md` `## 요구사항` 체크 상태 — 완료/미해결/철회 (최종 달성 범위)
- `summary.md` (`## 개요`·`## 변경 파일`·`## 구현 현황`·`## 검증` — 변경 요약 + 검사·검증에서 드러난 fail/manual) — 있으면
- `review.md` (리뷰에서 드러난 문제) — 있으면

본문 H2 헤딩별로 채운다 (헤딩 텍스트는 변경 금지). 일반론이 아니라 이 코드베이스에서 재사용·반복
회피 가능한 **구체적 교훈**으로 쓴다.

> **문장은 `${CLAUDE_PLUGIN_ROOT}/references/wording.md` 를 따른다.** 비슷한 작업을 시작하려는
> 사람이 읽는다 — 합니다체로, 전문용어는 풀어서. 다만 `## 사용 기술` 은 기술명이 본문이므로 예외다.

- `## 결과` — 1~3문장, 무엇이 나왔고 최종 상태.
- `## 잘된 점` — 재사용 가능한 기법 1개 = 불릿 1개.
- `## 어려웠던 점 / 실패` — 문제/회귀/롤백. 운영급 사고면 불릿 앞에 `[incident]`.
- `## 결정` — `<결정> — because <이유> (rejected: <대안>)` 형식. 대안 없으면 `(rejected: 없음)`.
  **개정 이력에 방향 전환이 있으면 되돌린 쪽을 `rejected` 에 적는다** (예: `rejected: zustand 전역 스토어 — 구현 후 공유 링크 불가로 되돌림`).
- `## 사용 기술` — `` `tech` — 어디에 왜 `` . (사용 기술은 본문에만 남긴다 — frontmatter에 중복 기재하지 않는다.)
- `## 후속 작업` — 미룬 TODO. 없으면 섹션 자체를 생략.

학습할 내용이 없는 섹션은 `- 없음` 한 줄로 둔다 (헤딩은 유지).

템플릿: `${CLAUDE_PLUGIN_ROOT}/skills/result/templates/result.md`

---

## STEP 4 — result.md 저장

`{task_dir}/result.md` 를 **항상 덮어쓰기** 저장한다.

frontmatter (공통 5필드 + result 전용):

```yaml
---
summary: {gather.summary}
branch: {branch}
repo: {repo}
status: completed
updated: {now}
outcome: {shipped | merged | abandoned | in-progress}
---
```

**상태 한 줄 + 산출물 링크**를 출력하고 [STOP].

```
완료
[result.md](file://{task_dir}/result.md)
```

경로는 `~` 가 아니라 절대경로로 낸다.
