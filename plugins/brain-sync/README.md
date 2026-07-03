# brain-sync

> cruise task 산출물을 Brain(지식그래프) 폴더 vault로 일괄 변환·적재 — 단방향·멱등

cruise 하네스(`~/Documents/tasks/<KEY>/`)가 쌓은 산출물을 읽어, Obsidian 스타일 마크다운 vault
(`~/Documents/brain/`)에 지식 노드를 만든다. cruise 코드를 import하지 않고 **계약**
([`plugins/cruise/CONTRACT.md`](../cruise/CONTRACT.md) contract_version 1) 만 보고 동작한다.
하네스와 Brain은 이 계약을 경계로 **독립적으로 진화**한다.

---

## 스킬

| 스킬 | 명령어 | 설명 |
|------|--------|------|
| sync | `/brain-sync:sync` | task 전체를 스캔해 new/changed 만 Brain 노드로 변환·적재 |
| status | `/brain-sync:status` | 동기화 대상·vault 현황 dry-run 보고 (쓰기·LLM 없음) |

명시적 호출 전용 (`disable-model-invocation: true`).

---

## Brain vault 레이아웃

```
~/Documents/brain/              ← env BRAIN_ROOT 로 override
├── features/     <slug>.md     ← 단위 기능 허브 (브랜치 기반, task·worktree 묶음)
├── work-items/   <KEY>.md      ← task 노드 (feature 자식 또는 unassigned)
├── patterns/     <kebab>.md    ← 재사용 기법 (여러 task 공유 가능)
├── decisions/    <KEY>-*.md    ← 의사결정 (task 국소)
├── incidents/    <KEY>-*.md    ← 사고 (task 국소)
├── technologies/ <slug>.md     ← 기술 (여러 task 공유 머지 노드)
├── _manifest.json              ← tasks/features/tech_index 멱등 원장
└── _meta.json                  ← 버전·last_sync·counts
```

### feature (단위 기능) 노드
- **브랜치로 식별**되는 최상위 허브. N개 task와 N개 worktree를 묶어 `kind`(worktree|branch),
  `task_count`, `worktree_count`, `tasks[]`, `worktrees[]` 를 기록.
- **권위 소스만** — result.md의 `feature` 권위값이 있는 task만 묶인다. 없으면 work-item `feature: unassigned`.
  휴리스틱 추측을 하지 않아 vault가 신뢰 가능한 진실원이 된다 (정확성 우선). `/cruise:result` 를 돌린 만큼 채워짐.

엣지는 본문 `[[folder/slug]]` wikilink + frontmatter `links[]` 미러로 표현한다.

---

## 매핑 (cruise 산출물 → Brain 노드)

| cruise 입력 | Brain 노드 | 결정적(스크립트) | 종합(LLM) |
|---|---|---|---|
| task.md (Jira/inline 감지) | work-item (1/KEY) | key·summary·jira status·parent | 제목 정리 |
| result.md `## 결과` + outcome | work-item 결과 | outcome·pr·base_branch·commits | 1문장 |
| summary.md `## 개요` + stats | work-item 변경요약 | files/+/- | — |
| result.md `## 잘된 점` | pattern (0..n, 공유) | 불릿 감지 | 명명·기존 슬러그 재사용 |
| result.md `## 결정` | decision (0..n) | 패턴 파싱 | 노드화 판단 |
| result.md `[incident]` | incident (0..n) | 사전필터 | severity/cause/resolution |
| result.md `## 사용 기술` + fm | technology (0..n, 공유) | 슬러그 목록 | 정체성 정규화·머지 |

---

## 멱등성

- **work-item id = `work-items/<KEY>`** — 재실행 시 항상 동일 파일.
- **content_hash 동일 → 쓰기 skip** (`updated` 보존). `_manifest.json` 의 `source_hash` 로
  변경 없는 task는 통째로 건너뛴다.
- **technology = 공유 머지 노드** — `source_keys` 에 KEY 누적, `## 사용 이력` 에 KEY별 1줄.
- **고아 노드** (재실행 시 더 이상 생성 안 됨) → KEY 를 `source_keys` 에서 제거, 비면
  `status: archived` (하드삭제 안 함).

자세한 입출력 계약은 [`CONTRACT_TARGET.md`](./CONTRACT_TARGET.md) 참조.

---

## 사용 흐름

```
cruise: plan → build → ... → review → result   (task당 result.md 생성)
                                         │
                                         ▼
brain-sync: /brain-sync:status   (무엇이 동기화될지 미리보기)
            /brain-sync:sync     (Brain vault로 일괄 적재)
```

`result.md` 가 없는 task는 work-item 만 생성된다(파생 노드 생략). 나중에 `/cruise:result` 로
result.md 가 생기면 다음 sync 에서 source_hash 가 바뀌어 자동 재동기화된다.

---

## 의존성

- Python 3, PyYAML (`pip install pyyaml`).
- 다른 플러그인에 런타임 의존하지 않는다. cruise 산출물은 파일로만 읽는다.

---

## 환경변수

| 변수 | 기본값 | 용도 |
|------|--------|------|
| `BRAIN_ROOT` | `~/Documents/brain` | Brain vault 위치 |
| `CRUISE_TASKS_ROOT` | `~/Documents/tasks` | cruise task 저장소 위치 |

---

## 설치

```bash
/plugin marketplace add FlaSh2493/marketplace
/plugin install brain-sync@flash-plugins
```
