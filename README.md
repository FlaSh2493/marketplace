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
| `session-insight` | 휴리스틱 점수로 가치 세션만 필터링 → 일간·주간·월간·rollup 분석 | `/session-insight:daily`, `/session-insight:weekly`, `/session-insight:monthly`, `/session-insight:rollup` | 0.3.0 |

### session-insight

세션이 끝나는 순간(SessionStop 훅) **휴리스틱 점수**로 가치 있는 세션만 골라 정제본을 `.filtered/` 에 복사하고, 모든 세션의 메타는 `index.jsonl` 에 1줄씩 누적한다. 일간·주간·월간·rollup 스킬은 이 필터셋·인덱스만 보고 동작한다 — **서로의 결과 마크다운에 의존하지 않는다.**

#### 설치

```bash
/plugin install session-insight@flash-plugins
```

#### 데이터 흐름

```
세션 종료 (SessionStop 훅)
        │
        ▼  score_and_filter.py
        ├─ 9개 시그널 추출 → 점수 계산
        ├─ score >= 임계값 → 노이즈 제거(thinking, queue/snapshot 등)·tool_result 1500자 truncation 후
        │                    ~/.claude/projects/<cwd>/.filtered/<sid>.jsonl 작성
        └─ 모든 세션(드롭 포함) → .filtered/index.jsonl 한 줄 append

                   .filtered/index.jsonl + .filtered/<sid>.jsonl
                                  │
       ┌─────────────────┬────────┴────────┬─────────────────┐
       ▼                 ▼                 ▼                 ▼
   /daily            /weekly           /monthly           /rollup
       │                 │                 │                 │
       ▼                 ▼                 ▼                 ▼
  daily/<date>.md   weekly/<Www>.md   monthly/<MM>.md   rollup/<from>_<to>.md
```

핵심 원칙:
- **훅 = 진짜 게이팅**. 저점수 세션 본문은 `.filtered/` 에 복사되지 않는다 (LLM 입력 노이즈 제거)
- **메타는 모두 보존**. 드롭된 세션도 `index.jsonl` 에 점수·시그널 1줄로 남아 양적 분석 가능
- **각 tier 독립**. 주간은 daily 마크다운을 안 읽는다 — 인덱스에서 그 주에 해당하는 세션을 직접 합산
- **raw jsonl 보존**. 훅은 raw 를 절대 수정·삭제하지 않는다

#### 휴리스틱 점수표 (9개 시그널)

| 시그널 | +가치 | -가치 |
|---|---|---|
| 도구 호출 수 | 30+ (+3), 5+ (+1) | 5 미만 (-2) |
| 세션 지속 시간 | 5분~2시간 (+2) | 1분 미만 또는 6시간+ (-3) |
| Edit/Write 호출 | 1+ (+3) | 0 (-2) |
| Bash 실행 수 | 1~50 (+1) | 100+ (-2) |
| 사용자 abort | 있음 (+1, 실패 학습) | - |
| 사용자 프롬프트 수 | 3~10 (+2) | 1 (-1) |
| 에러 후 재시도 | 있음 (+1) | - |
| 같은 파일 반복 수정 | 있음 (+1) | - |
| 첫 프롬프트 길이 | 100자+ (+1) | 20자 이내 (-1) |

**기본 임계값**: `score >= 3` → keep.

#### settings.json 으로 점수표 커스터마이즈

`.claude/settings.json` (팀 공유) 또는 `.claude/settings.local.json` (개인) 의 `env` 블록에 환경변수로 덮어쓴다.

```jsonc
{
  "env": {
    "SESSION_INSIGHT_MIN_SCORE": "5",
    "SESSION_INSIGHT_WEIGHTS": "{\"edit_write\":5,\"tools_high\":4,\"first_prompt_long_at\":150}"
  }
}
```

| 환경변수 | 효과 |
|---|---|
| `SESSION_INSIGHT_MIN_SCORE` | 임계값 정수 덮어쓰기 (기본 3) |
| `SESSION_INSIGHT_WEIGHTS` | JSON 객체. 디폴트 dict 에 머지 — 바꿀 키만 적으면 됨 |

설정 가능한 키 (디폴트값 일부):

```python
{
  "tools_high": 3, "tools_high_at": 30, "tools_mid": 1, "tools_mid_at": 5, "tools_low": -2,
  "duration_ok": 2, "duration_min_ok": 5, "duration_max_ok": 120,
  "duration_bad": -3, "duration_too_short": 1, "duration_too_long_min": 360,
  "edit_write": 3, "no_edit": -2,
  "bash_ok": 1, "bash_max_ok": 50, "bash_spam": -2, "bash_spam_at": 100,
  "abort": 1,
  "prompts_ok": 2, "prompts_min_ok": 3, "prompts_max_ok": 10, "single_prompt": -1,
  "error_retry": 1, "repeated_edit": 1,
  "first_prompt_long": 1, "first_prompt_long_at": 100,
  "first_prompt_short": -1, "first_prompt_short_at": 20,
}
```

> 임계값만 바꾸면 raw 재스캔 없이 `index.jsonl` 의 `kept` 만 재계산하면 된다. 가중치를 바꿀 때만 미래 세션이 새 기준을 따른다.

#### 스킬 요약

| 스킬 | 인자 | 동작 |
|------|------|------|
| `/session-insight:daily` | `[YYYY-MM-DD]` 또는 `--from --to` (생략 시 **어제**) | 그 날짜의 통과 세션을 8항목 루브릭으로 분석. 범위 시 일자별 독립 리포트 N개 |
| `/session-insight:weekly` | `[YYYY-MM-DD]` (생략 시 **지난 주**) | 그 날짜가 속한 ISO 주의 통과 세션을 직접 합산해 일별 추세 중심 분석 (daily.md 미참조) |
| `/session-insight:monthly` | `[YYYY-MM-DD]` (생략 시 **지난 달**) | 그 날짜가 속한 월의 통과 세션을 직접 합산해 주별 추세 중심 분석 (weekly.md 미참조) |
| `/session-insight:rollup` | `--from YYYY-MM-DD --to YYYY-MM-DD` (필수) | 범위에 대해 일별 요약·주간 패턴·월간 트렌드를 한 번의 LLM 호출로 통합 출력 |

모든 스킬은 결과 파일이 이미 있으면 **덮어쓰기**. raw jsonl 은 만지지 않는다.

#### `collect_filtered.py` 가 제공하는 섹션 (모든 tier 공통 입력)

- 헤더 (필터 통과율·총 토큰·점수 분포·드롭 시그널 합산)
- **드롭된 세션 메타 표** — 양적 시그널 (`session | date | score | tools | duration | edits | bash | prompts`)
- 통과 세션 목록 표
- 스킬별 집계 표 (`skill | count | avg input | avg output | cache hit | total input`)
- **고부하 turn 섹션** — 세션별 다지표 union (`input_tokens`, `output_tokens`, `tool_chars` 각 Top 5/세션 합집합), turn 당 tool_uses · user_text 앞 300자
- 직접입력 목록 — 스킬 호출 없이 들어간 user_text 첫 100자

> 필터된 jsonl 에서는 thinking 블록이 이미 제거되었으므로, 시행착오 분석은 `error_retry` / `abort` / 같은 도구 반복 시그널로 추적한다.

#### 8항목 루브릭 (네 스킬 공통)

각 항목 모두 turn/세션 인용을 근거로 첨부. 관찰 없으면 "해당 없음" 명시.

| 번호 | 항목 | 일간 | 주간 | 월간 / rollup |
|:---:|------|------|------|------|
| 1 | 토큰 부하 | 가장 무거운 스킬 Top3 + 추정 원인 | 일별 추세 | 주별 추세·누적 |
| 2 | 시행착오 | error_retry / abort / 도구 반복 | 일별 변화 | 굳어진 패턴 |
| 3 | 이상 반응 | tool 에러·반복 호출 | 일별 변화 | 반복 발생 패턴 |
| 4 | 입력 품질 | 모호한 user_text → 긴 작업 | 일별 흐름 | 월간 흐름 |
| 5 | 도구 사용 패턴 | 비효율 시퀀스 | 일별 변화 | 굳어진 비효율 |
| 6 | 최적화 제안 | 근거 인용 필수 | 일별 추세 기반 | 월 단위 의사결정용 |
| 7 | 신규 스킬 후보 | 근거 인용 필수 | 일별 추세 기반 | 누적으로 정당화 |
| 8 | 반복 요구사항 | direct_inputs 군집 | **일별 추세** | **주별 추세** |

#### 저장 위치

훅이 만드는 데이터 (사용자 홈):

```
~/.claude/projects/<encoded-cwd>/.filtered/
├── index.jsonl                  ← 모든 세션 메타 (kept=true/false)
└── <session-id>.jsonl           ← kept=true 정제본 (thinking 제거, tool_result 1500자 트렁케이트)
```

스킬이 만드는 리포트 (각 프로젝트):

```
<cwd>/.claude/session-insight/
├── daily/<YYYY-MM-DD>.md        ← /session-insight:daily
├── weekly/<YYYY-Www>.md         ← /session-insight:weekly
├── monthly/<YYYY-MM>.md         ← /session-insight:monthly
└── rollup/<from>_<to>.md        ← /session-insight:rollup
```

`.claude/session-insight/` 는 `.gitignore` 에 등록되어 커밋되지 않는다.

#### 플러그인 디렉토리 구조

```
plugins/session-insight/
├── .claude-plugin/
│   └── plugin.json
├── hooks/
│   └── hooks.json               ← SessionStop 훅 등록
├── scripts/
│   ├── _session_common.py       ← 공통 유틸
│   ├── score_and_filter.py      ← SessionStop 시점 점수+필터+인덱스
│   └── collect_filtered.py      ← tier 별 필터셋 → 마크다운 (stdout)
└── skills/
    ├── daily/SKILL.md
    ├── weekly/SKILL.md
    ├── monthly/SKILL.md
    └── rollup/SKILL.md
```

#### 운영 메모

- **훅이 한 번도 안 돌았으면** `.filtered/` 가 없어 모든 스킬은 안내 메시지를 띄우고 종료. 한 세션 이상 종료한 뒤 사용
- **임계값 튜닝**: 인덱스에 점수가 모두 기록되므로, 임계값만 바꿔 가며 keep 비율을 비교 가능. 분포가 한쪽으로 쏠리면 가중치도 함께 조정
- **알려진 약점** = 스킬 감지 정규식(`/word:word`) 이 user_text 의 우연한 패턴을 오탐할 수 있음 (예: `/autopilot:check는`, `/localhost:1420`). 표 해석 시 주의
- **에이전트 미사용**: 모든 처리는 Python 스크립트 + 메인 세션 LLM 으로 완결 — subagent 호출 없음

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
