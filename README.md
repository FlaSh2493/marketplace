# 내 프로젝트 Claude Code 플러그인 마켓플레이스

내 프로젝트 팀용 Claude Code 플러그인을 공유·설치할 수 있는 마켓플레이스입니다.

## 플러그인 설치

1. 마켓플레이스 등록
```bash
/plugin marketplace add FlaSh2493/marketplace
```

2. 플러그인 설치
```bash
/plugin install <plugin-name>@flash-plugins
```

3. 플러그인 업데이트 (변경사항 반영)
```bash
/plugin marketplace update
/plugin uninstall <plugin-name>
/plugin install <plugin-name>@flash-plugins
```

## 등록된 플러그인

| 플러그인 | 설명 | 명령어 | 버전 |
|---------|------|--------|------|
| `autopilot` | 이슈 단위 워크트리 자동화 — 플랜·구현·검사·머지·PR·리뷰 | `/autopilot:plan`, `/autopilot:build`, `/autopilot:req`, `/autopilot:check`, `/autopilot:merge`, `/autopilot:pr`, `/autopilot:review-fix`, `/autopilot:status`, `/autopilot:help` | 0.1.0 |
| `task-sync` | 작업 명세와 Jira 양방향 동기화 | `/task-sync:extract`, `/task-sync:fetch`, `/task-sync:publish`, `/task-sync:update`, `/task-sync:help` | 0.1.0 |
| `gh-sub` | 복수 GitHub 계정 관리 및 저장소별 계정 전환 | `/gh-sub:switch`, `/gh-sub:add`, `/gh-sub:status` | 0.1.0 |
| `e2e-testid-sync` | E2E 테스트를 위한 test-id 및 aria-busy 상태 주입 | N/A | 0.1.0 |
| `session-insight` | 세션 로그를 일간·주간·월간 계층으로 롤업 분석 | `/session-insight:daily`, `/session-insight:weekly`, `/session-insight:monthly` | 0.2.0 |

### session-insight

세션 로그(`~/.claude/projects/`)를 **일간 → 주간 → 월간** 계층으로 롤업 분석한다. 각 상위 계층은 이전 계층의 압축본(markdown 리포트) 만 읽기 때문에 컨텍스트가 폭발하지 않는다. 산술·정렬 같은 결정적 부분만 일간 스크립트가 담당하고, **요약 자체는 모든 계층에서 에이전트가 동일한 8항목 루브릭으로 작성** 한다.

#### 설치

```bash
/plugin install session-insight@flash-plugins
```

#### 데이터 흐름

```
~/.claude/projects/<encoded-cwd>/<sid>.jsonl   (Claude Code 가 기록하는 raw)
        │
        ▼  collect_daily.py <YYYY-MM-DD>      ← 유일하게 raw 를 만지는 스크립트
구조화 markdown (stdout)
        │
        ▼  /session-insight:daily             ← 에이전트가 8항목 루브릭으로 작성
<cwd>/.claude/session-insight/daily/<YYYY-MM-DD>.md
        │
        ▼  /session-insight:weekly            ← daily 7개 → 일별 추세
<cwd>/.claude/session-insight/weekly/<YYYY-Www>.md
        │
        ▼  /session-insight:monthly           ← weekly 4–5개 → 주별 추세
<cwd>/.claude/session-insight/monthly/<YYYY-MM>.md
```

핵심 원칙:
- raw jsonl 을 만지는 건 **일간 한 곳뿐**. 주간은 daily 마크다운, 월간은 weekly 마크다운만 입력
- 세 계층 모두 **동일한 8항목 루브릭** → 일/주/월 비교·추세화 가능
- SessionStop 훅 없음. 사용자 호출 시에만 동작
- 같은 파일이 이미 있으면 **덮어쓰기** (재실행으로 갱신 가능)

#### 스킬 요약

| 스킬 | 인자 | 동작 |
|------|------|------|
| `/session-insight:daily` | `[YYYY-MM-DD]` 또는 `--from YYYY-MM-DD --to YYYY-MM-DD` (생략 시 **어제**) | 그날치 raw → 구조화 md 생성 후 8항목 루브릭으로 일간 리포트 작성·저장. 범위 입력 시 일자별 독립 리포트 N개 생성 |
| `/session-insight:weekly` | `[YYYY-MM-DD]` (생략 시 **지난 주**) | 그 날짜가 속한 ISO 주(월–일) 의 daily 리포트를 읽어 일별 추세 중심 주간 리포트 작성·저장 |
| `/session-insight:monthly` | `[YYYY-MM-DD]` (생략 시 **지난 달**) | 그 날짜가 속한 월의 weekly 리포트를 읽어 주별 추세 중심 월간 리포트 작성·저장 |

#### `/session-insight:daily` 상세

**용법**:

```bash
/session-insight:daily                                       # 어제
/session-insight:daily 2026-04-27                            # 그 날짜
/session-insight:daily --from 2026-04-20 --to 2026-04-24     # 범위 (5일치 일자별 리포트 5개)
```

**처리 단계**:

1. 인자에서 처리할 날짜 목록을 결정 (단일 / 범위 / 어제)
2. 각 날짜마다 독립적으로:
   - `collect_daily.py "$(pwd)" <date>` 실행 → 구조화 markdown 받음
   - 그 markdown 을 입력으로 8항목 루브릭 작성
   - `<cwd>/.claude/session-insight/daily/<date>.md` 로 저장 (덮어쓰기)
   - 세션이 없는 날은 스킵
3. 끝나면 생성·갱신된 파일 목록 짧게 보고

**스크립트(`collect_daily.py`) 가 제공하는 섹션**:

- 헤더 (날짜·세션 수·총 input/output 토큰·thinking 블록 수)
- 세션 목록 표 (`id | start | turns | input | output | thinking blocks`)
- 스킬별 집계 표 (`skill | count | avg input | avg output | cache hit | total input`) — 그날 안의 다세션 합산
- **고부하 turn 섹션** — 세션별 다지표 union 으로 선정 (`input_tokens`, `output_tokens`, `tool_chars`, `thinking_chars` 각 Top 5/세션 합집합). turn 당:
  - tokens·cache hit·tool 개수·tool_chars
  - `tool_uses` 시퀀스
  - `user_text` 앞 300자
  - thinking 블록 본문 **전체** (발췌 없음, `<details>` 로 접힘)
- 직접입력 목록 — 스킬 호출 없이 들어간 user_text 첫 100자 (그날 반복 패턴 1차 감지용)

#### `/session-insight:weekly` 상세

**용법**:

```bash
/session-insight:weekly                # 지난 주 (직전 완료 주)
/session-insight:weekly 2026-04-27     # 그 날짜가 속한 ISO 주
```

**처리 단계**:

1. 기준 날짜 결정 (단일 / 7일 전)
2. 그 날짜가 속한 ISO 주 라벨(`YYYY-Www`) 과 월–일 7일 범위 계산
3. `daily/<YYYY-MM-DD>.md` 중 그 주에 속하는 것만 읽음 (없으면 0/7, 일부면 N/7)
4. 일간 리포트들을 입력으로 **같은 8항목 루브릭** 작성. 단순 합산 금지 — **일별 변화·추세·신규 패턴** 강조
5. `weekly/<YYYY-Www>.md` 로 저장
6. 일간 리포트가 0개면 `/session-insight:daily` 안내 후 종료

#### `/session-insight:monthly` 상세

**용법**:

```bash
/session-insight:monthly               # 지난 달 (직전 완료 월)
/session-insight:monthly 2026-04-27    # 그 날짜가 속한 월
```

**처리 단계**:

1. 기준 날짜 결정 (단일 / 1개월 전)
2. 월 라벨(`YYYY-MM`) 과 그 월에 걸치는 ISO 주들 계산 (목요일이 그 월에 속하면 그 월의 주로 간주, 보통 4–5개)
3. `weekly/<YYYY-Www>.md` 중 그 월에 속하는 것만 읽음
4. 주간 리포트들을 입력으로 **같은 8항목 루브릭** 작성. **주별 추세** 와 **월 단위로 굳어진 패턴** 강조 (한 주만의 노이즈는 배제)
5. `monthly/<YYYY-MM>.md` 로 저장
6. 주간 리포트가 0개면 `/session-insight:weekly` 안내 후 종료

#### 8항목 루브릭 (세 계층 공통)

각 항목 모두 turn/세션 인용을 근거로 첨부. 관찰 없으면 "해당 없음" 명시.

| 번호 | 항목 | 일간 | 주간 | 월간 |
|:---:|------|------|------|------|
| 1 | 토큰 부하 | 가장 무거운 스킬 Top3 + 추정 원인, cache hit 낮은 스킬 | 일별 추세 | 주별 추세·월간 누적 |
| 2 | 시행착오 | thinking 기반 번복·재고 (인용 + turn 근거) | 일별 변화 | 굳어진 패턴 |
| 3 | 이상 반응 | tool 에러·반복 호출·비정상 짧은 출력 | 일별 변화 | 반복 발생 패턴 |
| 4 | 입력 품질 | 모호한 user_text → 긴 작업, 좋은 입력 사례 | 일별 흐름 | 월간 흐름 |
| 5 | 도구 사용 패턴 | 비효율 시퀀스, tool_chars 큰 turn 정체 | 일별 변화 | 굳어진 비효율 |
| 6 | 최적화 제안 | 근거 인용 필수 | 일별 추세 기반 | 월 단위 의사결정용 |
| 7 | 신규 스킬 후보 | 근거 인용 필수 | 일별 추세 기반 | 한 달 누적으로 정당화 |
| 8 | 반복 요구사항 | direct_inputs 군집 (의도별 묶고 빈도·대표 인용) | **일별 추세** | **주별 추세** |

#### 저장 위치

```
<cwd>/.claude/session-insight/
├── daily/<YYYY-MM-DD>.md      ← /session-insight:daily 결과
├── weekly/<YYYY-Www>.md       ← /session-insight:weekly 결과
└── monthly/<YYYY-MM>.md       ← /session-insight:monthly 결과
```

`.claude/session-insight/` 는 `.gitignore` 등록되어 있어 커밋되지 않는다.

#### 플러그인 디렉토리 구조

```
plugins/session-insight/
├── .claude-plugin/
│   └── plugin.json             ← name, description, version, author
├── scripts/
│   ├── _session_common.py      ← encode_cwd, iter_jsonl, get_text, extract_skill,
│   │                              measure_tool_results, compute_cache_hit_rate, get_session_start
│   └── collect_daily.py        ← raw jsonl → 구조화 markdown (stdout)
└── skills/
    ├── daily/SKILL.md
    ├── weekly/SKILL.md
    └── monthly/SKILL.md
```

#### 운영 메모

- **신뢰도가 높은 정보** = 스킬별 집계 표(순수 산술), 기간 필터(timestamp 비교)
- **휴리스틱이 들어간 부분** = heavy turn 다지표 union 의 "Top N", 직접입력의 100자 prefix 군집화 — 에이전트가 raw 인용으로 보강해야 함
- **알려진 약점** = 스킬 감지 정규식(`/word:word`) 이 user_text 의 우연한 패턴을 오탐할 수 있음 (예: `/autopilot:check는`, `/localhost:1420`). 표 해석 시 주의

#### 업데이트

```bash
/plugin marketplace update
/plugin uninstall session-insight
/plugin install session-insight@flash-plugins
```

---

### autopilot 워크플로우

```
plan → build → req → check → merge → pr → review-fix → cleanup
```

| 스킬 | 설명 |
|------|------|
| `plan {브랜치명} [이슈키...] [--replan]` | 워크트리 생성 → 이슈 명세 로드 → 플랜 수립 → `tasks/{이슈키}/plan.md` 생성. 구현은 수행하지 않음 |
| `build [{브랜치명}]` | plan.md 를 읽어 구현만 수행. 이슈 명세/탐색 재호출을 생략하여 컨텍스트 최소화 |
| `req [이슈키]` | 대화에서 추가 요구사항을 추출하여 이슈 문서에 기록 |
| `check` | 워크트리 내 lint, type-check, test 순차 실행. 오류 시 자동 수정 (최대 3회) |
| `merge {피처브랜치}` | 워크트리를 피처 브랜치에 rebase + fast-forward 머지 |
| `merge-all {피처브랜치}` | 모든 활성 워크트리를 충돌 수 기준 정렬 후 순차 머지 |
| `pr` | 현재 브랜치를 push하고 develop 대상 PR 생성 |
| `review-fix` | CodeRabbit 리뷰를 자동으로 대기 → 제안사항 적용 → 결과 보고 |
| `cleanup {피처브랜치} {브랜치명...}` | 머지 완료된 워크트리 정리 (워크트리 제거 + 브랜치 삭제) |
| `status` | 활성 워크트리 상태 조회 (브랜치, 커밋 수, 마지막 커밋) |
| `init` | 초기 설정 (code-review-graph 확인, 그래프 빌드, 사용법 안내) |

## 스킬 이름 규칙

| 항목 | 결정하는 값 | 예시 |
|------|------------|------|
| **슬래시 명령어** (콜론 뒤) | `skills/` 하위 **디렉토리명** | `/jira-report:create` ← 디렉토리가 `create` |
| **검색·목록 표시명** | SKILL.md frontmatter **`name` 필드** | 스킬 검색 시 `jira-report-create`로 표시 |
| **자동 실행 판단** | SKILL.md frontmatter **`description` 필드** | Claude가 맥락에 맞는 스킬인지 판단할 때 사용 |

- 디렉토리명은 짧고 간결하게 (예: `create`, `view`, `sync`)
- `name` 필드는 검색 시 보이는 표시명이므로 플러그인명을 포함하여 명확하게 (예: `jira-report-create`)

## 플러그인 변경 반영

마켓플레이스의 플러그인을 수정한 뒤 변경사항을 반영하려면 **세 단계**를 모두 수행해야 합니다.

```bash
# 1. 마켓플레이스 업데이트 (원격 저장소 → 로컬 마켓플레이스)
/plugin marketplace update

# 2. 플러그인 제거
/plugin uninstall <plugin-name>

# 3. 플러그인 재설치 (마켓플레이스 → 로컬 플러그인)
/plugin install <plugin-name>@flash-plugins
```

> uninstall 없이 install만 하면 변경사항이 반영되지 않을 수 있습니다. 반드시 제거 후 재설치하세요.

## 레포 구조

```
FlaSh2493/marketplace/
├── .claude-plugin/
│   └── marketplace.json        ← 마켓플레이스 메타 + 플러그인 목록
├── .github/
│   └── workflows/
│       └── validate.yml        ← PR 시 자동 유효성 검증
└── plugins/
    └── autopilot/
        ├── .claude-plugin/
        │   └── plugin.json
        ├── scripts/            ← 공유 워크트리·상태 유틸 (Python)
        │   ├── resolve_worktree.py
        │   ├── ensure_worktree.py
        │   ├── load_custom_instructions.py
        │   └── ...
        ├── skills/
        │   ├── _shared/        ← 공유 절차 문서 (Read로 참조)
        │   │   ├── CHECK_LOOP.md
        │   │   └── CUSTOM_INSTRUCTIONS.md
        │   ├── plan/
        │   │   ├── SKILL.md
        │   │   └── scripts/
        │   ├── build/
        │   │   ├── SKILL.md
        │   │   └── agents/autopilot-builder.md
        │   ├── check/
        │   │   └── SKILL.md
        │   ├── merge/
        │   │   ├── SKILL.md
        │   │   └── reference/CONFLICT_RESOLUTION.md
        │   ├── review-fix/
        │   │   ├── SKILL.md
        │   │   └── agents/{checker,review-fixer}.md
        │   └── ...
        └── HELP.txt            ← 정적 도움말 텍스트
```

## 플러그인 기여하기

1. `plugins/` 하위에 새 플러그인 디렉토리를 생성합니다.
2. `.claude-plugin/marketplace.json`의 `plugins` 배열에 항목을 추가합니다.
3. **PR을 제출**합니다. CI에서 자동으로 유효성 검증이 실행됩니다.
