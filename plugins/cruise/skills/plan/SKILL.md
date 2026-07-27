---
name: cruise-plan
description: (명시적 커맨드 실행 전용) /cruise:plan 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Plan

> **종료 규칙:** 어떤 STEP에서 종료하든 Write 도구로
> `~/Documents/tasks/{KEY}/plan.md` 를 기록하고 [STOP]한다.
>
> - frontmatter 공통 5필드 + 스킬별 필드 완비
> - `status`: completed | cancelled | failed
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용

> **금지:**
>
> - 산출물 작성 후 요약·다음 액션 추천·후속 작업 제안 일체 출력하지 않는다 ("완료" 한 줄만)
> - 사용자가 명시적으로 요청하지 않은 어떤 액션도 수행하지 않는다
> - 다른 스킬을 자동으로 호출하지 않는다
> - Plan mode가 동시 활성화된 경우 `~/Documents/tasks/{KEY}/plan.md` 작성 후 ExitPlanMode 호출만 하고 [STOP]한다. 승인 후에도 구현으로 넘어가지 않는다.
> - 수정 요청 시 plan.md를 갱신하고 "완료"만 출력한다. (이전 plan/summary는 STEP 3.5에서 자동 archive)
> - summary.md는 읽지 않는다. plan은 task.md와 대화 컨텍스트만 입력으로 사용한다.

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

---

## STEP 2 — task.md 확보 (2분기)

STEP 1의 `key_source` 로 분기한다. 목표는 둘 다 동일 — 베이스 명세를 손에 넣고 STEP 2.5로 넘어가는 것. 원칙: **키가 있으면 매번 Jira에서 새로 불러오고, 이슈가 없으면 항상 만들고 불러온다.** Jira가 진실 원천이다.

### 분기 A — 키가 있음 (`key_source == "issue"`) → 매번 새로 fetch

브랜치명에 Jira 키가 있으면 로컬 task.md 존재 여부와 무관하게 **항상 Jira에서 라이브로 다시 불러온다** (오래된 로컬본을 신뢰하지 않는다):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/fetch.py {KEY}
```

→ `~/Documents/tasks/{KEY}/` 에 task.md·raw.json·meta.json 생성/갱신. 이어서 섹션을 읽는다:

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

본문: `## 배경`, `## 목표`, `## 요구사항`, `## 완료 조건`. Write 도구로 `~/Documents/tasks/{KEY}/task.md` 저장 후 STEP 2.5 진행.

---

task.md는 확보 이후 plan이 수정하지 않는다 (소스 오브 트루스 보존). 폴더명·명세 변경은 plan.md 완성 후 대화로 지시.

---

## STEP 2.5 — 요구사항 빠짐없이 분석

베이스 명세 + 대화 컨텍스트를 종합하여 요구사항을 **원자 단위로 분해**한다.

- 각 요구사항에 `R1`, `R2`, … ID를 부여한다. 이 ID는 `## 구현 계획`의 작업 항목·`## 검증 방법` 표, 그리고 이후 check·build 피드백이 일관되게 역참조하는 **추적 키**다 (요구사항↔구현↔검증).
- **명시 요구사항**(명세에 적힌 것)뿐 아니라 **암묵 요구사항**도 끌어낸다: 엣지케이스, 에러 처리, 빈/로딩 상태, 권한·인증, 하위 호환성, 접근성 등.
- 불명확하거나 가정이 필요한 항목은 임의로 단정하지 말고 **미지수**로 따로 모은다 (plan.md `## 요구사항` 하단 `### 미지수`).

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

## STEP 3.5 — 기존 plan/summary archive

`plan_md_exists == true` 인 경우에만 수행. 새 plan을 쓰기 전에 이전 산출물을 아카이브한다.

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
TASK_DIR=~/Documents/tasks/{KEY}
mkdir -p "$TASK_DIR/plan.archive" "$TASK_DIR/summary.archive"
mv "$TASK_DIR/plan.md" "$TASK_DIR/plan.archive/plan-$TS.md"
[ -f "$TASK_DIR/summary.md" ] && mv "$TASK_DIR/summary.md" "$TASK_DIR/summary.archive/summary-$TS.md"
```

- 같은 `{ts}` 로 plan / summary를 짝지어 archive (대응 관계 보존)
- summary.md 없으면 해당 archive는 생략
- archive 파일은 이후 어떤 스킬도 읽지 않는다 (사용자 참조 전용)

---

## STEP 4 — plan.md 작성

`templates/plan.md` 형식을 따른다. Write 도구로 `~/Documents/tasks/{KEY}/plan.md` 저장.

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
- `## 요구사항` — STEP 2.5에서 분해한 `- [ ] R1: …` 체크리스트. 하단에 `### 미지수`(불명확/가정, 없으면 생략).
- `## 구현 계획` — Phase 단위 계획. 각 Phase에 **반드시 포함**:
  - `<!-- delegate: auto|yes|no -->` 메타
  - 작업 항목 체크리스트 — 각 항목 끝에 충족하는 요구사항 ID 표기 (예: `- [ ] … (R1, R3)`)
  - `**생성/수정 파일**` — 트리 또는 목록으로 폴더구조·파일 경로 명시 (신규는 `(new)` 표기)
  - 샘플 코드는 쓰지 않는다 — 구현은 build가 실제 파일을 읽고 결정한다.
- `## 검증 방법` — 요구사항↔검증 추적 표 (`| 요구사항 | 검증 방법 | 도구/명령 |`). 자동 검증 불가 항목은 수동 절차를 명시. lint/type/test로 덮이는 항목은 도구/명령 칸에 `check` 로 표기 (build STEP 5가 집행).

---

## STEP 5 — 종료

"완료" 한 줄 출력 후 [STOP].
