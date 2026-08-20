---
name: cruise-plan
description: (명시적 커맨드 실행 전용) /cruise:plan 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Plan

plan.md 는 **누적 산출물**이다 (CONTRACT §4a). 최초에는 명세·대화로 생성하고, 이후에는
**개정 모드**로 부분 수정하며 자란다. 작은 추가·개정은 `cruise:build` 의 세미플랜이 담당하고,
plan 은 **최초 작성 · Phase 구조 재편 · Jira 명세 반영**을 맡는다.

개정 절차의 단일 규약: `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/amend.md`

> **종료 규칙:** 어떤 STEP에서 종료하든 `{task_dir}/plan.md` 를 기록하고 [STOP]한다.
> `{task_dir}` = `context.py` 의 `task_path` 의 디렉토리 (리터럴 경로를 쓰지 않는다).
>
> - frontmatter 공통 5필드 + 스킬별 필드 완비
> - `status`: completed | cancelled | failed
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용
> - 종료 시 **상태 한 줄 + 산출물 링크**를 출력한다 (amend.md §7)
> - 예외: 개정 모드에서 빈 선언이면 파일을 쓰지 않고 `변경 없음` 만 출력한다

> **금지:**
>
> - 상태 한 줄 + 산출물 링크 외에 요약·다음 액션 추천·후속 작업 제안 일체 출력하지 않는다
> - 사용자가 명시적으로 요청하지 않은 어떤 액션도 수행하지 않는다
> - 다른 스킬을 자동으로 호출하지 않는다
> - **개정 모드에서 plan.md를 전체 재작성하지 않는다.** 해당 R·작업 항목·검증 행만 부분 수정한다
>   (전체 재작성은 사용자가 "처음부터 다시" 를 명시했을 때만)
> - **R-ID를 재발급·재번호·삭제하지 않는다.** 철회는 `(철회: 사유)` 접미로 보존한다
> - summary.md는 읽지 않는다. plan의 입력은 task.md · 대화 컨텍스트 · 인자 · 이전 plan.md다.
> - 근거로 인용할 발화가 없는 요구사항은 만들지 않는다 (추측 금지)

> **Plan Mode:** 승인 **전에는 읽기만** 한다. 판별 결과를 ExitPlanMode 본문으로 제시하고,
> 승인 후에 쓰기·외부 액션을 실행한 뒤 [STOP]한다. 승인 후에도 **구현으로 넘어가지 않는다.**
>
> - 승인 전 실행 금지: `fetch.py` · `create.py` · `git checkout -b` · `git branch -m` ·
>   `update.py` · plan.md 쓰기
> - 허용: `context.py` · `load_issue.py`(로컬 읽기) · Read/Grep/Glob
> - 게이트는 `AskUserQuestion` 대신 **ExitPlanMode 로 대체**한다 (이중 승인 금지)
> - 로컬 task.md 가 없어 명세를 못 읽었으면 그 사실을 ExitPlanMode 본문에 명시한다

---

## STEP 0 — 설정 프리플라이트 (Jira 인증 확인)

Jira를 조회/생성하기 전에 `~/.config/cruise/config.json` 의 인증 정보를 확인한다.

```bash
CONFIG_DIR="${CRUISE_HOME:-${XDG_CONFIG_HOME:-$HOME/.config}/cruise}"
python3 -c "import json,sys; c=json.load(open('$CONFIG_DIR/config.json')); r=c.get('credentials',{}); sys.exit(0 if r.get('email') and r.get('jira_api_token') else 1)" 2>/dev/null && echo OK || echo MISSING
```

- `OK` → STEP 1 진행.
- `MISSING` (또는 파일 없음) → **Jira 기능(분기 A·C의 이슈 생성)은 사용할 수 없다.** 사용자에게
  아래를 자기 터미널에서 실행해 설정하라고 안내한다(대화형 `getpass` 사용 — Claude가 직접 실행 금지):

  ```
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/setup_config.py
  ```

  설정 없이도 로컬 cruise-inline 폴백(분기 C 폴백)으로는 계속 진행할 수 있다.

> **설정 관리:** 값 수정·확인·삭제는 모두 `setup_config.py` 로 한다.
> `setup_config.py show`(현재값·비밀 마스킹), `set KEY`(개별 수정), `delete KEY|--all`.
> 관리 키: `email` · `jira_api_token`(비밀) · `base_url` · `default_project`(선택).

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

결과를 메모리에 보관: `root`, `branch`, `key`, `key_source`, `base_branch`, `task_path`, `task_md_exists`, `plan_md_exists`.
`task_dir` = `task_path` 의 디렉토리. 이후 모든 산출물 경로는 `task_dir` 기준으로만 해석한다.

### 인자 해석

| 인자 | 해석 |
|------|------|
| 없음 | 대상 = 브랜치. 요구사항 근거 = 명세 + 대화 |
| 이슈 키 단독 (`SPT-4200`) | **이슈 연결 지시** (STEP 1.5). 확정 지시가 아니므로 근거는 명세 + 대화 |
| 문장 | 대상 = 브랜치. 근거 = **인자** |
| 이슈 키 + 문장 | 연결(STEP 1.5) + 인자가 확정 지시 |

---

## STEP 1.5 — 이슈 연결 (인자에 이슈 키가 있을 때만)

인자의 이슈 키가 `key` 와 다르면, **그 이슈를 현재 브랜치에 연결**한다. KEY의 단일 진실 원천은
브랜치명이므로, 디렉토리만 바꾸지 않고 브랜치에 키를 심는다(그러지 않으면 이후 스킬이 다른 KEY를 본다).

- 현재 브랜치가 base(main/develop/master/release/*)면 → `git checkout -b {KEY}-{slug}`
- 이미 slug 피처 브랜치면 → `git branch -m {KEY}-{oldslug}` (키를 앞에 삽입)
- **가드:** `git rev-parse --abbrev-ref @{upstream}` 이 있으면 rename이 파괴적이다.
  rename하지 말고 사용자에게 알린 뒤 판단을 맡긴다.
- 연결 승인은 STEP 4의 게이트와 **하나로 합친다** (승인을 두 번 받지 않는다)
- 연결 후 `context.py` 를 재실행해 `key`·`key_source`·`task_dir` 를 갱신한다

---

## STEP 2 — task.md 확보 (2분기)

STEP 1의 `key_source` 로 분기한다. 목표는 둘 다 동일 — 베이스 명세를 손에 넣고 STEP 2.5로 넘어가는 것. 원칙: **키가 있으면 매번 Jira에서 새로 불러오고, 이슈가 없으면 항상 만들고 불러온다.** Jira가 진실 원천이다.

### 분기 A — 키가 있음 (`key_source == "issue"`) → 매번 새로 fetch

브랜치명에 Jira 키가 있으면 로컬 task.md 존재 여부와 무관하게 **항상 Jira에서 라이브로 다시 불러온다** (오래된 로컬본을 신뢰하지 않는다):

**재fetch 전 가드 — 로컬 편집 유실 방지:** `fetch.py` 는 task.md 를 백업 없이 덮어쓴다.
`raw.json` 이 있고 로컬 task.md 가 그것과 다르면(사용자가 편집한 상태), 덮어쓰지 말고
`/cruise:update` 로 Jira에 먼저 반영하라고 알린 뒤 [STOP]한다.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/fetch.py {KEY}
```

→ `{task_dir}/` 에 task.md·raw.json·meta.json 생성/갱신. 이어서 섹션을 읽는다:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py \
  --key {KEY} \
  --sections "배경,목표,요구사항,완료 조건,참고,제약"
```

섹션 내용을 베이스 명세로 삼고 STEP 2.5 진행.

**fetch 실패 시에만** (오프라인·config 미설정·권한): 로컬 task.md가 이미 있으면 그것을 사용하고, 없으면 사용자에게 원인(config/네트워크/권한)을 알린 뒤 분기 C의 cruise-inline 폴백으로 진행한다.

### 분기 C — 이슈 없음 (`key_source == "slug"`) → 이슈 먼저 생성 후 fetch

브랜치에 Jira 키가 없으면 **이슈를 먼저 만들고 그 키로 브랜치를 잡는다** ("이슈 먼저, 브랜치 나중"). 이렇게 하면 KEY의 단일 진실은 계속 브랜치명이고 context.py는 손대지 않는다.

1. 대화 컨텍스트에서 명세(요약·배경·목표·요구사항·완료 조건)를 **메모리에서** 구성한다. **이슈 생성 전에는 로컬에 task.md를 쓰지 않는다** — description은 create.py에 stdin으로 넘기고, 생성 후 fetch.py가 정규 task.md를 만든다 (고아 slug 디렉토리 방지).
2. **생성 전 게이트** (외부 액션이므로 반드시 확인): 프로젝트 키 · 이슈타입(기본 `Task`) · 요약 · description을 사용자에게 보여주고 승인받는다.
   - 선택지에 **"기존 이슈 키 입력"** 을 포함한다. 사용자가 기존 이슈로 작업하려는 경우
     새 이슈를 만들면 중복이 된다. 키를 입력받으면 STEP 1.5(이슈 연결)로 가서 분기 A로 수렴한다.
   - 프로젝트 키는 config.json의 `settings.default_project` 를 `create.py` 가 자동으로 읽는다. **미설정이면 사용자에게 프로젝트 키를 물어** `--project`로 넘긴다 (조용히 폴백하지 않는다). 매번 쓰려면: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/setup_config.py set default_project`
   - 사용자가 생성을 **명시적으로 거부**하면 아래 폴백으로 진행한다.
3. 승인 시 이슈를 생성한다 (description은 stdin 마크다운):

   ```bash
   printf '%s' "$DESCRIPTION_MD" | \
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create.py --project {PROJECT} --type Task --summary "{요약}"
   # stdout: 생성된 키 (예: MKT-500)
   ```

4. **키를 담은 브랜치 확보:**
   - 현재 브랜치가 base(main/develop/master/release/*)면 → `git checkout -b {NEWKEY}-{slug}` (base에서 분기).
   - 이미 slug 피처 브랜치에서 작업 중이면 → `git branch -m {NEWKEY}-{oldslug}` (키를 앞에 삽입).
   - **가드:** 브랜치가 이미 upstream/PR에 push돼 있으면 rename이 파괴적이다. `git rev-parse --abbrev-ref @{upstream}` 이 있으면 rename하지 말고 사용자에게 알린 뒤 판단을 맡긴다.
5. `context.py` 를 재실행한다 → 이제 `key_source: issue`, `key: {NEWKEY}`.
6. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/fetch.py {NEWKEY}` 로 정규 Jira형 task.md 생성 → 분기 A와 동일 지점으로 수렴. STEP 2.5 진행.

**폴백 (Jira 불가/생성 거부 시에만):** 오프라인·config 완전 부재이거나 사용자가 생성을 명시 거부한 경우에 한해, 현재 대화 컨텍스트에서 cruise-inline task.md를 직접 만든다 (CONTRACT §3b). **기본 경로가 아니다.**

```yaml
---
summary: { 대화에서 추출한 한 줄 요약 }
branch: { branch }
repo: { repo }
status: completed
updated: { UTC ISO8601 }
source: cruise-inline
---
```

본문: `## 배경`, `## 목표`, `## 요구사항`, `## 완료 조건`. `{task_dir}/task.md` 저장 후 STEP 2.5 진행.

---

task.md는 확보 이후 plan이 수정하지 않는다 (소스 오브 트루스 보존). 폴더명·명세 변경은 plan.md 완성 후 대화로 지시.

---

## STEP 2.5 — 요구사항 분석 (2모드)

`plan_md_exists` 로 분기한다.

### 신규 모드 (`plan_md_exists == false`)

베이스 명세 + 대화 컨텍스트 + 인자를 종합하여 요구사항을 **원자 단위로 분해**한다.

- 각 요구사항에 `R1`, `R2`, … ID를 부여한다. 이 ID는 `## 구현 계획`의 작업 항목·`## 검증 방법` 표, 그리고 이후 build 의 체크박스·재구현 타깃이 역참조하는 **추적 키**다 (요구사항↔구현↔검증).
- **명시 요구사항**(명세에 적힌 것)뿐 아니라 **암묵 요구사항**도 끌어낸다: 엣지케이스, 에러 처리, 빈/로딩 상태, 권한·인증, 하위 호환성, 접근성 등.
- 불명확하거나 가정이 필요한 항목은 임의로 단정하지 말고 **미지수**로 따로 모은다 (plan.md `## 요구사항` 하단 `### 미지수`).

**근거가 없으면 만들지 않는다.** 명세의 요구사항 섹션이 비어 있고(범용 티켓) 대화·인자에도 확정
결론이 없으면, 추측으로 채우지 말고 아래처럼 알린 뒤 [STOP]한다.

```
{KEY} 명세에서 요구사항을 도출할 수 없습니다.
  배경·목표: {있는 내용}
  요구사항 섹션: 비어 있음
대화로 정한 뒤 다시 실행하거나, /cruise:plan {KEY} <요구사항> 으로 지정하세요.
```

### 개정 모드 (`plan_md_exists == true`)

**`references/amend.md` 규약을 따른다.** 요약하면:

1. 기존 plan.md 의 R 목록 · `### 미지수` · `## 개정 이력` 을 먼저 읽는다
2. **경계 판정**(amend.md §1) — 인자 우선, 없으면 마지막 plan 호출 이후 발화,
   그것도 없으면 개정 이력과 대조해 미반영분만
3. **판별 4분기**(§2) — revise / add / withdraw / 미지수. 기존 R 과 의미가 겹치면 add 하지 않는다
4. 선언이 모두 비면 **파일을 쓰지 않고** `변경 없음` 출력 후 [STOP] (STEP 3~4를 건너뛴다)
5. Phase 구조 재편이 필요하면 그것도 이 모드에서 처리한다 (build 세미플랜은 못 하는 일)

---

## STEP 3 — 코드베이스 영향 파악 (내부 판단용)

분해된 요구사항(R1, R2, …) + 현재 대화의 추가 컨텍스트를 기준으로 영향 범위를 파악한다.
이 단계의 산출은 **Phase를 어떻게 나눌지 판단하기 위한 내부 근거**일 뿐이며, plan.md에는 아무것도 기록하지 않는다 (영향 범위 표·아키텍처 산문·재사용 목록 모두 남기지 않는다).

**code-review-graph MCP가 있는 경우**:

1. `semantic_search_nodes_tool` — 요구사항 키워드로 관련 노드 검색
2. `get_impact_radius_tool` — 영향 파일 2-hop 추적

**없는 경우**: Glob/Grep fallback으로 직접 탐색.

흐름·모듈 경계·기술 선택·재사용 판단은 Phase 분해에 반영하되 산문으로 남기지 않는다 — 구현도, 어떤 기존 코드를 재사용할지도 build가 실제 파일을 읽고 결정한다. (탐색 중 build의 로컬 검색으로는 놓칠 법한 원거리 재사용처를 발견했다면, 그것만 해당 Phase 작업 항목에 한 줄로 붙인다.)

> **자기검증:** 영향 범위에 빠진 곳이 없는지 1회 자문한다 — 변경 대상의 호출부·역참조(backlink)까지 포함되었는가.

---

## STEP 3.5 — 게이트 (승인)

`references/amend.md` §4 의 표시 형식으로 반영 내용을 보여주고 승인받는다.

| 상황 | 게이트 |
|------|--------|
| 신규 모드 (최초 작성) | **있음** — 요구사항 전체가 처음 정해지는 시점 |
| 개정 모드에 `revise`·`withdraw` 포함 | **있음** |
| 개정 모드에 `add`·미지수만 | **없음** — 바로 STEP 4 |
| Plan Mode 활성 | **ExitPlanMode 로 대체** |
| STEP 1.5 이슈 연결이 있었음 | 연결 내용을 **같은 게이트에 합쳐** 표시 (승인 1회) |

`미지수`·`제외` 줄을 반드시 함께 표시한다. 취소 시 파일을 쓰지 않고 [STOP].

---

## STEP 4 — plan.md 작성 / 개정

### 신규 모드 — 전체 작성

`templates/plan.md` 형식을 따라 `{task_dir}/plan.md` 를 만든다.

frontmatter (공통 5필드 + 스킬별):

```yaml
---
summary: { task.md에서 상속, 없으면 브랜치명 추론 }
branch: { branch }
repo: { repo }
status: completed
updated: { UTC ISO8601 }
phases_count: { Phase 수 정수 }
---
```

본문 구조 (헤딩 순서·텍스트 고정) — **필수 항목만 남긴 얇은 계약**. 배경·목표·완료 조건은 task.md가 소스 오브 트루스이므로 plan에 복제하지 않는다.

- `# Plan — {KEY}` (H1)
- `## 요구사항` — `- [ ] R1: …` 체크리스트 (전부 미체크로 시작). 하단에 `### 미지수`(없으면 생략).
- `## 구현 계획` — Phase 단위 계획. 각 Phase에 **반드시 포함**:
  - `<!-- delegate: auto|yes|no -->` 메타
  - 작업 항목 체크리스트 — 각 항목 끝에 충족하는 요구사항 ID 표기 (예: `- [ ] … (R1, R3)`)
  - `**생성/수정 파일**` — 트리 또는 목록으로 폴더구조·파일 경로 명시 (신규는 `(new)` 표기)
  - 샘플 코드는 쓰지 않는다 — 구현은 build가 실제 파일을 읽고 결정한다.
- `## 검증 방법` — 요구사항↔검증 추적 표 (`| 요구사항 | 검증 방법 | 도구/명령 |`). 자동 검증 불가 항목은 수동 절차를 명시. lint/type/test로 덮이는 항목은 도구/명령 칸에 `check` 로 표기 (build가 집행).
- `## 개정 이력` — 최초 작성 한 줄 (`- {날짜}: R1~Rn 최초 작성 (task.md 명세 + 암묵 요구사항 도출)`).

### 개정 모드 — 부분 수정

**전체를 다시 쓰지 않는다.** `references/amend.md` §3 대로 해당 줄만 치환한다.

| 연산 | 적용 |
|------|------|
| `add` | 요구사항 줄 append (ID = 현재 최대 + 1, **미체크**) + 작업 항목 + `생성/수정 파일` + 검증 표 행 |
| `revise` | 해당 줄만 치환 + **체크 해제**. 구현 방식이 바뀌면 `생성/수정 파일` 도 갱신 |
| `withdraw` | 줄을 지우지 않고 `(철회: 사유)` 접미. 관련 작업 항목만 제거 |
| 미지수 | `### 미지수` 에 한 줄 추가 / 승격 시 그 줄 제거 |

- **검증 방법 없는 요구사항은 추가하지 않는다** (추가하면 영구 미검증이 된다)
- 모든 연산 후 `## 개정 이력` 에 근거 인용 포함 한 줄 append
- `phases_count`·`updated` frontmatter 갱신

### archive

- **부분 개정에서는 archive하지 않는다** (변경 사유는 `## 개정 이력` 에 있으므로 백업이 중복)
- **전체 재작성 시에만** 아래를 수행하며, 반드시 **새 plan.md 쓰기가 성공한 뒤**에 한다
  (중단 시 live 산출물이 사라지지 않도록)

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "{task_dir}/plan.archive"
cp "{task_dir}/plan.md.bak" "{task_dir}/plan.archive/plan-$TS.md"   # 쓰기 전 백업본을 이동
```

- `summary.md` 는 **건드리지 않는다.** build 산출물은 build 가 관리한다 (v11)

---

## STEP 5 — 종료

**상태 한 줄 + 산출물 링크**를 출력하고 [STOP]. 요약·다음 액션 추천은 하지 않는다.

```
완료: 추가 R6 / 개정 R1 / 철회 R4
[plan.md](file://{task_dir}/plan.md)
```

- 신규 모드: `완료: R1~R5 신규`
- 반영하지 않은 항목이 있으면 같은 줄에: `완료: 추가 R6 / 미반영 2건 (태블릿 열 수, 접근성)`
- 최초 fetch 로 task.md 를 새로 만들었으면 `task.md` 링크도 함께 낸다
- 빈 선언이면: `변경 없음` 만 출력 (링크 없음)
- 경로는 `~` 가 아니라 **절대경로**로 낸다 (클릭 가능해야 하므로)
