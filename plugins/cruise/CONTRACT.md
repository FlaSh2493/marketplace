# Cruise 하네스 산출물 계약 (Harness Artifact Contract)

```yaml
contract_version: 2
```

이 문서는 cruise 하네스가 디스크에 남기는 산출물의 **안정적 스키마**를 정의한다.
외부 소비자(예: `brain-sync` 플러그인)는 cruise 코드를 import하지 않고 **이 계약만** 보고
산출물을 읽는다. cruise 자신은 이 파일을 읽지 않는다.

> **독립성 원칙** — 하네스는 Brain(지식그래프) 구조를 모른다. 변환은 소비자가 한다.
> 하네스와 소비자는 이 계약을 경계로 독립적으로 진화한다. 계약을 깨는 변경(필드 제거·의미 변경)은
> `contract_version` 을 올린다. 필드 추가는 minor 변경으로 버전을 올리지 않아도 된다.

---

## 1. 저장 위치 · 키 규칙

- 저장 루트: `~/Documents/tasks/<KEY>/`
- `KEY` 결정 (cruise `scripts/context.py`):
  - 브랜치명에 `[A-Z]+-\d+` 패턴이 있으면 그 값 (예: `SPT-4152`, `IET-7750`) — `key_source: issue`
  - 없으면 브랜치명을 슬러그화한 값 (예: `develop`, `feat-nextjs-migration`) — `key_source: slug`
  - 인자로 직접 받은 경우 — `key_source: arg` 또는 `user-arg`
- 한 디렉토리 = 한 task. 디렉토리 안에는 아래 산출물 + jsync 메타(`meta.json`, `raw.json`) +
  `attachments/`, `*.archive/`(이전 산출물 백업), `.DS_Store`, 사람이 쓴 임의 파일(`handover.md` 등)이
  **섞여 있을 수 있다.** 소비자는 임의 부분집합을 견뎌야 한다.

---

## 2. 공통 frontmatter (9필드)

`task.md`(cruise-inline 형) 및 cruise가 생성하는 모든 `.md`(plan/build/summary/check/commit/merge/pr/review/result)는
아래 9필드를 공통으로 가진다.

| 필드 | 타입 | 의미 | 안정성 |
|------|------|------|--------|
| `key` | string | task 키 | 안정 |
| `key_source` | enum | `issue` \| `slug` \| `arg` \| `user-arg` | 안정 |
| `skill` | string | 이 파일을 만든 스킬 (`task`/`plan`/`build`/...) | 안정 |
| `summary` | string | task 한 줄 요약 (task.md에서 상속) | 안정 |
| `branch` | string | 작업 브랜치 | 안정 |
| `repo` | string | `owner/name` GitHub repo | 안정 |
| `status` | enum | `completed` \| `cancelled` \| `failed` (**cruise 생애주기**) | 안정 |
| `created` | string | 최초 생성 UTC ISO8601 (재호출 시 유지) | 안정 |
| `updated` | string | 마지막 수정 UTC ISO8601 | 안정 |
| `tags` | string[] | 자유 태그 | 자유 |

> `status` 는 **cruise 생애주기 상태**다. Jira 상태(`Working` 등)와 혼동하지 말 것.

---

## 3. task.md — 두 가지 형태 (소비자는 형태를 감지해야 함)

`task.md` 는 출처에 따라 frontmatter가 **둘 중 하나**다.

### 3a. jsync/Jira 형 (jsync:fetch 로 생성)

공통 9필드가 **아니다.** Jira 필드를 그대로 담는다.

```yaml
key: SPT-4152
summary: 브랜디드 컨텐츠 목록 화면 리뉴얼 (FE)
status: Working            # ← Jira 상태 (cruise status 아님)
issuetype: 스토리
priority: Medium
assignee: scnam@madup.com
labels: []
components: []
fixVersions: []
duedate: ''
parent: SPT-3629
watchers: []
links: {}                  # 또는 {clones: [IET-7743]} 등
customfields:
  sprint: [...]
  epic_link: SPT-3629
  story_points: 0.25
add_worklog: ''
```

### 3b. cruise-inline 형 (cruise가 대화 맥락에서 직접 생성)

공통 9필드 + `source: cruise-inline` (+ 선택 `head_sha`).

```yaml
key: IET-7774
key_source: user-arg
skill: task
summary: ...
branch: develop
repo: madup-inc/xpert-monorepo-fe
head_sha: ""
status: completed
created: ...
updated: ...
source: cruise-inline
tags: [bug, feature-toggle]
```

**감지 규칙:** frontmatter에 `skill: task` 또는 `source: cruise-inline` 가 있으면 3b,
`issuetype`/`customfields` 가 있으면 3a.

### task.md 본문 (양 형태 공통, H2 헤딩)
`## 배경` · `## 목표` · `## 요구사항` · `## 완료 조건` (3a는 description 본문이 이 구조를 느슨하게 따름).

---

## 4. cruise 생성 산출물 — 스킬별 추가 필드

모든 항목은 §2 공통 9필드를 포함한다. 아래는 **추가** 필드만.

| 파일 | 추가 frontmatter | 본문 H2 (안정) |
|------|------------------|----------------|
| `plan.md` | `phases_count: int` | `## 배경` `## 목표` `## 요구사항`(`- [ ] R1:` 체크리스트 + `### 미지수`) `## 영향 범위`(표) `## 아키텍처 / 기술 설계` `## 구현 계획`(Phase별 `<!-- delegate: -->` + 생성/수정 파일·샘플 코드·R-ID) `## 검증 방법`(표) `## 완료 조건` |
| `build.md` | `runs_count: int` | append-only `## Run {ts}` 섹션. + 선택 `## Check Feedback {ts}`(check가 append, 미구현 요구사항 R-ID 인박스) |
| `summary.md` | `base_branch` `files_changed:int` `insertions:int` `deletions:int` | `## 개요` + 변경 요약 (빌드마다 덮어씀) |
| `check.md` | `result: pass\|fail` `tools:{lint,type,test}` `fix_attempts:int` `requirements_checked:int` | `## 결과` `## 요구사항 검증`(표: 요구사항·검증방법·결과·진단) `## 에러`. 매 check마다 덮어쓰기(이력 아님) |
| `commit.md` | `commits:[{sha,message,files_count}]` `commits_count:int` | 커밋 목록 |
| `merge.md` | `entries:[{at,source,target,conflicts_count,result_sha}]` | `## 머지 이력`(append-only) |
| `pr.md` | `pr_url:str` `pr_number:int` `base_branch` `labels:[]` `assignee` | PR 제목/본문 |
| `review.md` | `pr_number:int` `iterations:[{n,at,reviews_processed,validation,pushed_sha}]` | 리뷰 이력(append-only) |
| `result.md` | §5 참조 | §5 참조 |

> 모든 산출물이 항상 존재하는 것은 아니다. 실제 디스크에서는 산출물이 불균일하다
> (예: review.md·merge.md 는 없는 task가 많다). 소비자는 `*_md_exists` 를 검사하고 없는 것은 건너뛴다.

---

## 5. result.md — 변환을 위한 고신호 단일 소스 (`/cruise:result` 생성)

task 종료 시점(pr/review 이후)에 **1회 작성, 덮어쓰기**되는 회고 산출물. 소비자가 가장 먼저 읽는 파일.

> **하네스 고유 어휘만 사용한다.** Pattern/Decision/Incident/Technology 를 *스키마 필드*로 쓰지 않는다.
> 본문의 `[incident]` 인라인 태그 하나만 소비자 분류 힌트로 허용한다.

### frontmatter (공통 9필드 + result 전용)

```yaml
# ...공통 9필드 (skill: result)...
outcome: shipped            # shipped | merged | abandoned | in-progress (상태에서 도출)
base_branch: develop
base_source: pr             # pr | upstream | reflog | heuristic | unknown (base 도출 출처)
pr_url: ""                  # pr.md 에서 복사, 없으면 ""
pr_number: null             # 없으면 null
commits_count: 0            # commit.md 에서 복사
feature: feat/sprint3       # 단위 기능 식별자(브랜치). "" = unassigned (동결 실패 시)
worktree:                   # 작업 시점 worktree 정체성 (머지 후 삭제돼도 보존)
  kind: worktree            # worktree | branch | "" (미상)
  name: sprint3-filter      # linked worktree 디렉토리명, 아니면 ""
issue_keys: [SPT-4152]      # branch+커밋제목에서 추출한 이슈 키(복수 가능)
technologies: [react, nextjs, nuqs]   # 평문 소문자 슬러그 (하네스 태그, Brain 노드 아님)
artifacts_present: [task, plan, build, summary, check, commit, pr]
```

`outcome` 도출: merge.md 머지 완료 → `merged`; PR 있으나 미머지 → `shipped`;
`status: cancelled` → `abandoned`; PR·커밋 없음 → `in-progress`.

### feature 동결 규칙 (정확성 우선·추측 금지)
- feature는 `/cruise:result` 가 **이 task의 체크아웃에서** 1회 계산해 동결한다.
- **신뢰 가능한 base일 때만 동결**: `base_source ∈ {pr, upstream, reflog}`. `heuristic`/`unknown` 이거나
  현재 CWD가 이 task의 체크아웃이 아니면 **`feature: ""`(unassigned)** 로 두고 추측하지 않는다.
- 도출: base_branch가 base군(`develop|main|master|staging|stg|stag|dev|release/*`)이 아니면
  feature=base_branch(umbrella), 맞으면 feature=branch(독립).
- 소비자(brain-sync)는 이 값을 **재도출 없이 그대로** 사용한다. `""` 면 feature 미부여.

### 본문 — 고정 H2 헤딩 (= 소비자 파싱 계약)

```markdown
# Result — <KEY>

## 결과
1~3문장. 무엇이 나왔고 최종 상태는 무엇인가.

## 잘된 점
- 재사용 가능한 기법 1개 = 불릿 1개.

## 어려웠던 점 / 실패
- 부딪힌 문제 / 회귀 / 롤백. 운영급 사고면 `[incident]` 접두.

## 결정
- <결정> — because <이유> (rejected: <대안>)

## 사용 기술
- `nuqs` — URL 상태 관리에 도입; `react` — ...

## 후속 작업   (선택)
- 미룬 TODO / 기술부채.
```

**안정 보장:** §5의 frontmatter 키와 위 H2 헤딩 텍스트는 `contract_version: 1` 동안 안정.
각 H2 아래 불릿의 자유 텍스트는 자유 형식이며, `## 결정` 의 `<결정> — because <이유> (rejected: <대안>)`
패턴과 `## 어려웠던 점 / 실패` 의 `[incident]` 접두만 약하게 구조화되어 있다.
