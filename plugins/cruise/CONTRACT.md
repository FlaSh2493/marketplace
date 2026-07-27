# Cruise 하네스 산출물 계약 (Harness Artifact Contract)

```yaml
contract_version: 10
```

> **v10 변경 (breaking):** 저장 루트가 더 이상 고정 리터럴 `~/Documents/tasks` 가 아니다.
> cruise 설정 `~/.config/cruise/config.json` 의 `settings.tasks_root`(기본 `~/Documents/tasks`)로
> 결정된다. 소비자는 루트를 하드코딩하지 말고 이 설정값을 기준으로 경로를 해석해야 한다.
>
> **v9 변경 (breaking):** 공통 frontmatter를 9필드에서 5필드(`summary`·`branch`·`repo`·`status`·`updated`)로
> 축소했다. `key`·`key_source`·`skill`·`created`·`tags` 를 제거했다 — 어떤 소비자도 읽지 않거나
> 저장 디렉토리명·git에서 파생 가능한 필드다. cruise-inline task.md 형태 감지는 `source: cruise-inline`(3b)
> vs `issuetype`/`customfields`(3a) 유무로만 한다.
>
> **v8 변경 (breaking):** `result.md` frontmatter를 공통 9필드 + `outcome` 으로 축소했다.
> `pr_url`·`pr_number`·`commits_count`·`base_branch`·`base_source`·`issue_keys`·`technologies`·
> `artifacts_present` 를 제거했다 — 소비자가 `gh`/git·result 본문에서 파생하거나 원래 안 읽던 필드다.
>
> **v7 변경 (breaking):** `merge.md` 산출물을 폐지했다. 머지 이력의 진실 원천은 **git 이력**이며,
> 소비자는 `git log --merges` 로 직접 조회한다. `outcome: merged` 판정은 gh PR 상태(`MERGED`)로만
> 도출한다(merge.md는 base→feature 로컬 머지라 task 머지 신호가 아니었다).
>
> **v6 변경 (breaking):** `commit.md`·`pr.md` 산출물을 폐지했다. 커밋·PR 정보의 진실 원천은
> **git 이력과 GitHub**이며, 소비자(result·cruise:log)는 `gh` 로 직접 조회한다.

이 문서는 cruise 하네스가 디스크에 남기는 산출물의 **안정적 스키마**를 정의한다.
외부 도구는 cruise 코드를 import하지 않고 **이 계약만** 보고 산출물을 읽을 수 있다.
cruise 자신은 이 파일을 읽지 않는다.

> **독립성 원칙** — 하네스는 산출물을 소비하는 쪽의 구조를 모른다. 변환은 소비자가 한다.
> 하네스와 소비자는 이 계약을 경계로 독립적으로 진화한다. 계약을 깨는 변경(필드 제거·의미 변경)은
> `contract_version` 을 올린다. 필드 추가는 minor 변경으로 버전을 올리지 않아도 된다.

---

## 1. 저장 위치 · 키 규칙

- 저장 루트: 기본 `~/Documents/tasks/<KEY>/` — cruise `~/.config/cruise/config.json` 의
  `settings.tasks_root` 로 변경 가능(소비자는 해당 값 기준으로 경로를 해석해야 한다)
- `KEY` 결정 (cruise `scripts/context.py`):
  - 브랜치명에 `[A-Z]+-\d+` 패턴이 있으면 그 값 (예: `SPT-4152`, `IET-7750`) — `key_source: issue`
  - 없으면 브랜치명을 슬러그화한 값 (예: `develop`, `feat-nextjs-migration`) — `key_source: slug`
  - 인자로 직접 받은 경우 — `key_source: arg` 또는 `user-arg`
- 한 디렉토리 = 한 task. 디렉토리 안에는 아래 산출물 + Jira 동기화 메타(`meta.json`, `raw.json`) +
  `attachments/`, `*.archive/`(이전 산출물 백업), `.DS_Store`, 사람이 쓴 임의 파일(`handover.md` 등)이
  **섞여 있을 수 있다.** 소비자는 임의 부분집합을 견뎌야 한다.

---

## 2. 공통 frontmatter (5필드)

`task.md`(cruise-inline 형) 및 cruise가 생성하는 모든 `.md`(plan/summary/review/result)는
아래 5필드를 공통으로 가진다. 모두 소비자(result·cruise:log)가 실제로 읽는 필드다.

| 필드 | 타입 | 의미 | 안정성 |
|------|------|------|--------|
| `summary` | string | task 한 줄 요약 (task.md에서 상속) | 안정 |
| `branch` | string | 작업 브랜치 | 안정 |
| `repo` | string | `owner/name` GitHub repo | 안정 |
| `status` | enum | `completed` \| `cancelled` \| `failed` (**cruise 생애주기**) | 안정 |
| `updated` | string | 마지막 수정 UTC ISO8601 | 안정 |

> `status` 는 **cruise 생애주기 상태**다. Jira 상태(`Working` 등)와 혼동하지 말 것.
> task 키는 저장 디렉토리명(`<KEY>/`)이 진실 원천이므로 frontmatter에 중복하지 않는다.

---

## 3. task.md — 두 가지 형태 (소비자는 형태를 감지해야 함)

`task.md` 는 출처에 따라 frontmatter가 **둘 중 하나**다.

### 3a. Jira 형 (cruise:plan 의 fetch 로 생성)

공통 필드 규칙을 따르지 **않는다.** Jira 필드를 그대로 담는다.

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

공통 5필드 + `source: cruise-inline` (+ 선택 `head_sha`).

```yaml
summary: ...
branch: develop
repo: madup-inc/xpert-monorepo-fe
head_sha: ""
status: completed
updated: ...
source: cruise-inline
```

**감지 규칙:** frontmatter에 `source: cruise-inline` 가 있으면 3b,
`issuetype`/`customfields` 가 있으면 3a.

### task.md 본문 (양 형태 공통, H2 헤딩)
`## 배경` · `## 목표` · `## 요구사항` · `## 완료 조건` (3a는 description 본문이 이 구조를 느슨하게 따름).

---

## 4. cruise 생성 산출물 — 스킬별 추가 필드

모든 항목은 §2 공통 5필드를 포함한다. 아래는 **추가** 필드만.

| 파일 | 추가 frontmatter | 본문 H2 (안정) |
|------|------------------|----------------|
| `plan.md` | `phases_count: int` | `## 요구사항`(`- [ ] R1:` 체크리스트 + `### 미지수`) `## 구현 계획`(Phase별 `<!-- delegate: -->` + 생성/수정 파일 + 작업항목↔R-ID) `## 검증 방법`(표). **얇은 계약** — 배경·목표·완료 조건은 task.md가 소스, plan에 복제하지 않음. 샘플 코드·영향 범위·아키텍처 산문·재사용 목록 제거(구현도 재사용도 build가 실제 파일 읽고 결정) |
| `summary.md` | `base_branch` `files_changed:int` `insertions:int` `deletions:int` `check_result:pass\|fail` `check_tools:{lint,type,test}` `requirements_checked:int` `fix_attempts:int` | `## 개요` `## 변경 파일` `## 구현 현황` `## 검증`(압축: 검사 한 줄 + 요구사항 pass/fail 집계 + fail·manual만 진단 한 줄) `## 비고`. 에러 원문·전체 검증 표·변경 통계 본문은 담지 않는다(수치는 frontmatter). **build 스킬이 구현+검사+요구사항 검증 결과를 담아 매 build마다 덮어씀.** 유일한 build 산출물 |
| `review.md` | `pr_number:int` `iterations:[{n,at,reviews_processed,validation,pushed_sha}]` | 리뷰 이력(append-only) |

> **커밋·PR·머지는 산출물이 아니다 (v6·v7).** commit 스킬은 git 이력만 남기고, pr 스킬은 GitHub에
> PR만 만들며, merge 스킬은 머지 커밋만 남긴다. 커밋 목록·PR URL·번호·base·상태가 필요한 소비자는
> `gh pr list --repo {repo} --head {branch} --json number,url,title,baseRefName,state,commits` 로,
> 머지 이력이 필요하면 `git log --merges` 로 조회한다. `repo`·`branch` 는 남은 산출물
> (plan/summary/review/result)의 공통 frontmatter에서 얻는다. gh 실패·PR 없음이면 해당 정보를 건너뛴다.

> 모든 산출물이 항상 존재하는 것은 아니다. 실제 디스크에서는 산출물이 불균일하다
> (예: review.md·result.md 는 없는 task가 많다). 소비자는 `*_md_exists` 를 검사하고 없는 것은 건너뛴다.

---

## 5. result.md — 회고 (`/cruise:result` 생성)

task 종료 시점(pr/review 이후)에 **1회 작성, 덮어쓰기**되는 회고 산출물.
task의 결과·교훈·결정을 담는 고신호 요약으로, 외부 소비자(예: cruise:log 가 Jira 이슈 댓글에 포함)가
cruise 코드를 import하지 않고 **이 스키마만** 보고 읽는다.

### frontmatter (공통 5필드 + result 전용)

```yaml
# ...공통 5필드 (summary·branch·repo·status·updated)...
outcome: shipped            # shipped | merged | abandoned | in-progress (상태에서 도출)
```

> **result 고유 필드는 `outcome` 하나뿐 (v8).** PR·커밋·이슈키·기술·base 등은 frontmatter에 담지 않는다 —
> 소비자가 `gh`/git(§4 조회 규칙)·result 본문(`## 사용 기술` 등)에서 파생한다. `base_source`·`artifacts_present`
> 처럼 아무도 안 읽던 필드도 제거했다.

`outcome` 도출: gh PR 상태가 MERGED → `merged`; PR 있으나 미머지 → `shipped`;
`status: cancelled` → `abandoned`; PR·커밋 없음 → `in-progress`. (`scripts/result/gather.py` 가 gh 상태 조회로 결정적으로 계산)

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
