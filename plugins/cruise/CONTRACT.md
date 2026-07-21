# Cruise 하네스 산출물 계약 (Harness Artifact Contract)

```yaml
contract_version: 4
```

이 문서는 cruise 하네스가 디스크에 남기는 산출물의 **안정적 스키마**를 정의한다.
외부 도구는 cruise 코드를 import하지 않고 **이 계약만** 보고 산출물을 읽을 수 있다.
cruise 자신은 이 파일을 읽지 않는다.

> **독립성 원칙** — 하네스는 산출물을 소비하는 쪽의 구조를 모른다. 변환은 소비자가 한다.
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

`task.md`(cruise-inline 형) 및 cruise가 생성하는 모든 `.md`(plan/build/summary/check/commit/merge/pr/review)는
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

> 모든 산출물이 항상 존재하는 것은 아니다. 실제 디스크에서는 산출물이 불균일하다
> (예: review.md·merge.md·result.md 는 없는 task가 많다). 소비자는 `*_md_exists` 를 검사하고 없는 것은 건너뛴다.

---

## 5. result.md — 회고 (`/cruise:result` 생성)

task 종료 시점(pr/review 이후)에 **1회 작성, 덮어쓰기**되는 회고 산출물.
task의 결과·교훈·결정을 담는 고신호 요약으로, 외부 소비자(예: jsync:log 가 Jira 이슈 댓글에 포함)가
cruise 코드를 import하지 않고 **이 스키마만** 보고 읽는다.

### frontmatter (공통 9필드 + result 전용)

```yaml
# ...공통 9필드 (skill: result)...
outcome: shipped            # shipped | merged | abandoned | in-progress (상태에서 도출)
base_branch: develop
base_source: pr             # pr | upstream | reflog | heuristic | unknown (base 도출 출처)
pr_url: ""                  # pr.md 에서 복사, 없으면 ""
pr_number: null             # 없으면 null
commits_count: 0            # commit.md 에서 복사
issue_keys: [SPT-4152]      # branch+커밋제목에서 추출한 이슈 키(복수 가능)
technologies: [react, nextjs, nuqs]   # 평문 소문자 슬러그
artifacts_present: [task, plan, build, summary, check, commit, pr]
```

`outcome` 도출: merge.md 머지 완료 → `merged`; PR 있으나 미머지 → `shipped`;
`status: cancelled` → `abandoned`; PR·커밋 없음 → `in-progress`. (`scripts/result/gather.py` 가 결정적으로 계산)

### 본문 — 고정 H2 헤딩 (= 소비자 파싱 계약)

소비자가 아래 헤딩 텍스트를 그대로 매칭해 불릿을 추출하므로 헤딩을 바꾸지 않는다.

```markdown
# Result — <KEY>

## 결과                     # 1~3문장, 무엇이 나왔고 최종 상태
## 잘된 점                  # 재사용 가능한 기법 (불릿)
## 어려웠던 점 / 실패        # 문제/회귀/롤백. 운영급 사고는 `[incident]` 접두
## 결정                     # <결정> — because <이유> (rejected: <대안>)
## 사용 기술                # `tech` — 어디에 왜
## 후속 작업                # 미룬 TODO (없으면 섹션 생략)
```

학습 내용이 없는 섹션은 `- 없음` 한 줄로 둔다 (헤딩 유지). `- 없음` 은 소비자가 제외한다.
