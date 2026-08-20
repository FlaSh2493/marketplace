# Cruise 하네스 산출물 계약 (Harness Artifact Contract)

```yaml
contract_version: 11
```

> **v11 변경:** `plan.md` 를 **누적 산출물**로 격상했다(§4a). 요구사항 체크박스
> (`- [ ] R1` / `- [x] R1`)가 진척의 진실 원천이며 **build 스킬이 갱신한다**(본문은 건드리지 않는다).
> R-ID 는 재발급·재사용·삭제하지 않고(철회는 `(철회: 사유)` 접미로 보존), 변경 사유는
> `## 개정 이력` 에 근거 인용과 함께 남긴다. `plan.archive/` 는 **전체 재작성 시에만** 만들고,
> `summary.archive/` 는 폐지했다.
>
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
| `plan.md` | `phases_count: int` | `## 요구사항`(`- [ ] R1:` 체크리스트 + `### 미지수`) `## 구현 계획`(Phase별 `<!-- delegate: -->` + 생성/수정 파일 + 작업항목↔R-ID) `## 검증 방법`(표) `## 개정 이력`. **누적 산출물(§4a)** · **얇은 계약** — 배경·목표·완료 조건은 task.md가 소스, plan에 복제하지 않음. 샘플 코드·영향 범위·아키텍처 산문·재사용 목록 제거(구현도 재사용도 build가 실제 파일 읽고 결정) |
| `summary.md` | `base_branch` `files_changed:int` `insertions:int` `deletions:int` `check_result:pass\|fail` `check_tools:{lint,type,test}` `requirements_checked:int` `fix_attempts:int` | `## 개요` `## 변경 파일`(작업단위별 `### 그룹명` 서브헤딩 + 하위 파일 불릿) `## 구현 현황` `## 검증`(압축: 검사 한 줄 + 요구사항 pass/fail 집계 + fail·manual만 진단 한 줄) `## 비고`. 에러 원문·전체 검증 표·변경 통계 본문은 담지 않는다(수치는 frontmatter). **build 스킬이 구현+검사+요구사항 검증 결과를 담아 매 build마다 덮어씀.** 유일한 build 산출물. `summary.archive/` 는 만들지 않는다(v11) |
| `review.md` | `pr_number:int` `iterations:[{n,at,reviews_processed,validation,pushed_sha}]` | 리뷰 이력(append-only) |

> **커밋·PR·머지는 산출물이 아니다 (v6·v7).** commit 스킬은 git 이력만 남기고, pr 스킬은 GitHub에
> PR만 만들며, merge 스킬은 머지 커밋만 남긴다. 커밋 목록·PR URL·번호·base·상태가 필요한 소비자는
> `gh pr list --repo {repo} --head {branch} --json number,url,title,baseRefName,state,commits` 로,
> 머지 이력이 필요하면 `git log --merges` 로 조회한다. `repo`·`branch` 는 남은 산출물
> (plan/summary/review/result)의 공통 frontmatter에서 얻는다. **최신 산출물부터 조회한다
> (result → review → summary → plan)** — 워크트리 전환 등으로 plan.md의 branch가 stale해질 수
> 있으므로, 이후 작성된 산출물이 실제 작업 브랜치를 더 정확히 반영한다. gh 실패·PR 없음이면
> 해당 정보를 건너뛴다.

> 모든 산출물이 항상 존재하는 것은 아니다. 실제 디스크에서는 산출물이 불균일하다
> (예: review.md·result.md 는 없는 task가 많다). 소비자는 `*_md_exists` 를 검사하고 없는 것은 건너뛴다.

---

## 4a. plan.md — 누적 산출물 규칙 (v11)

`plan.md` 는 한 task의 **요구사항 이력 전체**를 들고 있는 유일한 산출물이다. 재작성으로 갈아치우지
않고 개정(부분 수정)으로 자란다. 소비자는 아래 규칙을 전제로 파싱할 수 있다.

### 체크박스 = 진척의 진실 원천

```markdown
## 요구사항
- [x] R1: 목록을 카드로 보여줍니다 (모바일 1열 / 태블릿 3열 / 데스크톱 4열)
- [ ] R2: 목록을 아래로 내리면 다음 페이지가 이어서 나옵니다
- [x] R3: 보여줄 항목이 없으면 안내 문구가 나옵니다 (수동확인)
- [ ] R4: 정렬 기능 (철회: 이번에는 넣지 않습니다 — 필터부터 확인하고 다음에)
```

| 표기 | 의미 |
|------|------|
| `- [ ] Rn:` | 미구현 또는 미검증 — build 의 재구현 타깃 |
| `- [x] Rn:` | 검증 통과 |
| `(수동확인)` 접미 | 자동 검증 불가로 사람 확인이 필요한 항목 (`[x]` 로 둠) |
| `(철회: 사유)` 접미 | 철회됨. 검증·구현 대상이 아니며 집계에서 제외 |

**요구사항 문장은 밖에서 보이는 변화로 쓴다.** `cruise:log` 가 이 문장을 Jira 댓글에
그대로 싣기 때문에, 컴포넌트·훅·라이브러리 이름이 아니라 "무엇이 가능해지는가 / 무엇이
달라지는가" 로 서술한다 (합니다체, 전문용어는 풀어서). 기술 서술은 `## 구현 계획` 의 작업 항목에 둔다.
소비자는 `## 요구사항` 의 R 문장을 **비전문가가 읽을 수 있는 텍스트**로 취급할 수 있다.

**체크박스는 `build` 가 갱신한다.** build 는 체크박스 외 어떤 줄도 수정하지 않는다.
본문(요구사항 문장·Phase·검증 표·미지수·개정 이력)은 `plan` 과 build 의 세미플랜만 수정한다.

### R-ID 안정성

- 신규 ID 는 **현재 최대값 + 1**. 철회된 ID 도 재사용하지 않는다
- 기존 ID 를 **재발급·재번호·삭제하지 않는다.** 철회는 줄을 지우지 않고 접미로 표기
- 요구사항 내용이 바뀌면(문장·작업 항목·검증 방법 중 무엇이든) 해당 R 의 **체크를 해제**한다
- R-ID 는 `## 구현 계획` 작업 항목(`(R1, R3)`)과 `## 검증 방법` 표 행이 역참조하는 추적 키다

### `### 미지수`

`## 요구사항` 하위 섹션. 확정되지 않은 논의를 보관한다. R-ID 를 부여하지 않으므로 구현·검증
대상이 아니다. 결론이 나면 R 로 승격하고 해당 줄을 제거한다. 없으면 섹션을 생략한다.

### `## 개정 이력`

요구사항이 언제·왜 바뀌었는지를 근거 인용과 함께 남기는 append-only 목록. 세션이 끊겨도
"어디까지 반영했는지" 를 이 섹션으로 복원한다.

```markdown
## 개정 이력
- 2026-08-20: R1~R5 최초 작성 (task.md 명세 + 암묵 요구사항 도출)
- 2026-08-20: R6 추가 — 카테고리를 골라 목록을 걸러냅니다 ("카테고리별로 걸러지게")
- 2026-08-20: R7 추가 — 키보드만으로 필터를 조작합니다 (인자: "키보드 탐색도 되게")
- 2026-08-20: R1 개정 — 태블릿 3열·데스크톱 4열 ("2열은 비어 보이네")
- 2026-08-20: R4 철회 — 이번에는 넣지 않습니다 ("정렬은 이번엔 빼자")
```

- 형식: `- {YYYY-MM-DD}: {추가|개정|철회} {R-ID} — {요약} ({근거})`
- 근거는 대화 발화를 인용하거나, 스킬 인자에서 온 경우 `인자:` 접두를 붙인다
- 명세에서 도출된 최초 작성은 근거에 출처를 적는다

### archive

- `plan.archive/plan-{ts}.md` 는 **전체 재작성 시에만** 만든다. 부분 개정에서는 만들지 않는다
  (변경 사유는 `## 개정 이력` 에 있으므로 백업이 중복이다)
- archive 는 **새 plan.md 쓰기가 성공한 뒤**에 만든다 (중단 시 live 산출물이 사라지지 않도록)
- `summary.archive/` 는 폐지했다 — summary.md 는 최신 스냅샷 1개로 충분하다

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
