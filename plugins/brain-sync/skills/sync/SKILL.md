---
name: brain-sync-sync
description: (명시적 커맨드 실행 전용) /brain-sync:sync 명령이 입력된 경우에만 활성화한다. cruise task 산출물 전체를 Brain(지식그래프) 폴더 vault로 일괄 변환·적재한다. 단방향(cruise→Brain)·멱등.
disable-model-invocation: true
---

# Brain Sync — Sync (cruise → Brain vault)

cruise task 산출물을 읽어 Brain vault(`~/Documents/brain/`)에 work-item·pattern·decision·incident·technology
노드를 **멱등하게** 생성/갱신한다. 변환 규칙은 `plugins/brain-sync/CONTRACT_TARGET.md` 와
`plugins/cruise/CONTRACT.md` (contract_version 1) 를 따른다.

> **역할 분담:** 스크립트가 결정적 추출·멱등 쓰기를 한다. LLM은 **node plan(창의적 종합)** 만 만든다.
> work-item 식별/실행 사실(branch/repo/pr/outcome 등)은 스크립트가 채우므로 plan에 넣지 않는다.

> **금지:**
> - 동기화 외 액션(커밋, cruise 스킬 호출 등) 일체 금지.
> - 처리 후 요약·다음 액션 추천 출력 금지 (마지막 총괄 한 줄만).
> - cruise 산출물(`~/Documents/tasks/`)을 수정하지 않는다. 읽기 전용 입력이다.

---

## STEP 1 — 인벤토리 스캔

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scan.py
```

(인자로 `--jira-only` 가 주어지면 추가.) 출력의 `tasks[]` 를 메모리에 보관한다.

## STEP 2 — 범위 결정

기본 처리 대상 = `status ∈ {new, changed}` 인 task. `unchanged` 는 건너뛴다(이미 동기화됨, source_hash 동일).
대상 개수를 **한 줄로** 보고하고 바로 STEP 3 진행 (게이트 없음 — 사용자가 멈추려면 직접 중단).

대상이 0개면 "동기화 대상 없음" 한 줄 출력 후 STEP 5 로 건너뛴다.

## STEP 3 — task별 변환 루프

각 대상 task `<KEY>` 에 대해:

### 3a. no_result task (`has_result == false`)
파생 노드 없이 work-item 만 생성한다 (LLM 종합 생략, 토큰 절약):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sync.py <KEY> --auto
```

### 3b. result.md 있는 task
먼저 사실을 추출한다:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract.py <KEY>
```

출력의 `result`(잘된 점/실패/결정/사용 기술), `existing_patterns`, `existing_technologies` 를 보고
**node plan JSON** 을 종합한다. 규칙:

- `patterns`: `result.worked` 중 **재사용 가치가 있는** 기법만 노드화. 슬러그는 `existing_patterns` 에
  같은 개념이 있으면 **그 슬러그를 재사용**하고, 없으면 새 kebab 슬러그를 만든다 (중복 방지).
- `decisions`: `result.decisions` 의 `<결정> — because <이유> (rejected: <대안>)` 를 파싱해 채운다.
- `incidents`: `result.failed` 중 `[incident]` 접두가 붙었거나 운영 영향이 명확한 것만.
- `technologies`: `result.technologies` + `result.tech_notes` 기반. 슬러그는 `existing_technologies` 와
  **동일 개념을 정규화**(react==reactjs, next==nextjs)해 하나로 합친다. 각 항목에 `usage` 한 줄.
- `work_item`: `title`, `result_summary`(1문장), 필요 시 `background`/`goal`/`change_summary` 만.
  branch/repo/pr/outcome 등 실행 사실은 **넣지 않는다**(스크립트가 채움).

> **feature는 plan에 넣지 않는다.** feature 멤버십은 result.md의 권위값(`feature` 필드)에서
> sync.py가 **자동으로** 처리한다(추측 금지). LLM은 feature를 만들거나 추측하지 않는다.
> result.md.feature 가 비어있으면(=unassigned) 해당 task는 어떤 feature에도 묶이지 않는다.

plan JSON 스키마:
```json
{
  "work_item": {"title": "...", "result_summary": "...", "background": "", "goal": "", "change_summary": ""},
  "patterns":  [{"slug": "kebab", "title": "...", "problem": "...", "solution": "...", "body": ""}],
  "decisions": [{"name": "kebab", "title": "...", "decision": "...", "rationale": "...", "alternatives": ["..."], "body": ""}],
  "incidents": [{"name": "kebab", "title": "...", "severity": "...", "symptom": "...", "cause": "...", "resolution": "...", "body": ""}],
  "technologies": [{"slug": "react", "title": "React", "category": "library", "usage": "..."}]
}
```

plan 을 stdin 으로 sync.py 에 넘긴다:

```bash
echo '<plan-json>' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sync.py <KEY> --plan -
```

각 호출 출력: `{key, created, updated, unchanged, archived, nodes}` 를 메모리에 누적한다.
(work-item·파생 노드와 함께 `features/<slug>` 노드도 sync.py가 자동 생성·갱신·archive 한다.)

## STEP 4 — 마무리

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/manifest.py --finalize
```

## STEP 5 — 총괄 보고

처리한 task 수, 생성/갱신/스킵/archive 노드 합계, **feature 수 / unassigned task 수**, vault 경로를
**한 줄**로 출력하고 [STOP]. unassigned task가 많으면 "`/cruise:result` 로 feature를 채울 수 있음" 한 줄 덧붙인다.
