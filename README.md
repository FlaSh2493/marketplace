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
| `session-insight` | 세션 로그 노이즈 자동 제거 + 스킬별 토큰 부하 분석 | `/session-insight:analyze` | 0.1.0 |

### session-insight

세션 로그(`~/.claude/projects/`)의 구조적 노이즈를 자동 제거하고, 스킬·플러그인별 토큰 부하를 분석한다.

#### 설치

```bash
/plugin install session-insight@flash-plugins
```

#### 기능 1: 노이즈 자동 제거 (SessionStop 훅)

세션 종료 시 자동으로 실행되며, 원본 `.jsonl`에서 노이즈를 제거한 `.filtered.jsonl`을 생성한다.

| 구분 | 대상 | 처리 |
|------|------|------|
| **DROP** | `queue-operation`, `file-history-snapshot`, `ai-title`, `last-prompt` | 항목 전체 제거 |
| **DROP** | attachment: `deferred_tools_delta`, `hook_success`, `mcp_instructions_delta`, `todo_reminder`, `skill_listing` | 항목 전체 제거 |
| **TRUNCATE** | `user` 메시지의 `tool_result` content | 500자 초과 시 잘라냄 (원본 길이 태그 보존) |
| **STRIP** | `assistant` 메시지의 `thinking` 블록 | 블록만 제거, `text`·`tool_use`·`usage`는 보존 |
| **KEEP** | `attachment` type `hook_failure` | 그대로 보존 |

- **입력**: stdin JSON `{"session_id": "...", "cwd": "..."}`
- **출력**: `~/.claude/projects/<encoded-cwd>/<session_id>.filtered.jsonl`
  - `<encoded-cwd>`: cwd의 `/`를 `-`로 치환 (예: `/Users/madup/my/marketplace` → `-Users-madup-my-marketplace`)
- **예상 효과**: 원본 대비 50–60% 파일 크기 감소

#### 기능 2: 스킬별 토큰 부하 분석 (`/session-insight:analyze`)

필터된 로그를 읽어 스킬별 토큰 통계를 집계하고, Claude가 고부하 원인을 구체적으로 설명한다.

**입력 옵션:**

| 옵션 | 설명 | 예시 |
|------|------|------|
| (없음) | 최근 30일 | `/session-insight:analyze` |
| `--days N` | 최근 N일 | `/session-insight:analyze --days 7` |
| `--from DATE --to DATE` | 날짜 범위 지정 | `/session-insight:analyze --from 2026-04-01 --to 2026-04-25` |
| `--all` | 전체 기간 | `/session-insight:analyze --all` |

**통계 스크립트 출력 (`analyze_tokens.py`):**

```json
{
  "period": { "from": "2026-03-25", "to": "2026-04-25" },
  "skills": {
    "/autopilot:build": {
      "count": 12,
      "avg_input_tokens": 42000,
      "avg_output_tokens": 1800,
      "cache_hit_rate": 0.3
    }
  },
  "sessions": [
    {
      "id": "abc123",
      "start": "2026-04-20T10:00:00+00:00",
      "total_tokens": 120000,
      "turns": [
        {
          "turn": 3,
          "skill": "/autopilot:build",
          "input_tokens": 52000,
          "output_tokens": 2100,
          "cache_hit_rate": 0.1,
          "user_text_length": 120,
          "tool_results_count": 4,
          "tool_results_total_chars": 18000
        }
      ]
    }
  ],
  "total": { "sessions": 15, "input_tokens": 500000, "output_tokens": 25000 }
}
```

> `tool_results_total_chars`는 truncate 전 원본 길이 기준 — 왜 토큰이 많은지 파악하는 데 사용된다.

**Claude 분석 출력:**

- **[타입 1] 개별 인사이트**: 고부하 세션의 각 turn별로 스킬명, 토큰 수, 원인(tool_result 크기·수, cache miss 등)을 구체적으로 서술
- **[타입 2] 전체 요약**: 스킬별 토큰 테이블, 고부하 공통 패턴, 최적화 제안

#### 디렉토리 구조

```
plugins/session-insight/
├── .claude-plugin/
│   └── plugin.json           ← hooks 참조 포함
├── hooks/
│   └── hooks.json            ← SessionStop 훅 정의
├── scripts/
│   ├── filter_logs.py        ← 노이즈 제거 스크립트 (SessionStop 시 자동 실행)
│   └── analyze_tokens.py     ← 토큰 통계 추출 스크립트 (analyze 스킬이 호출)
└── skills/
    └── analyze/
        └── SKILL.md
```

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
| `plan {브랜치명} [이슈키...] [--no-spec] [--replan]` | 워크트리 생성 → 이슈 명세 로드 → 플랜 수립 → `{브랜치명}.plan.md` 생성. 구현은 수행하지 않음 |
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
        ├── agents/             ← 서브에이전트 정의
        │   ├── checker.md      ← lint/type-check/test 자동 수정
        │   └── review-fixer.md ← 리뷰 코멘트 일괄 적용
        ├── scripts/            ← 순수 계산 로직 (Python)
        │   ├── detect_env.py
        │   ├── fetch_reviews.py
        │   ├── extract_metadata.py
        │   ├── infer_labels.py
        │   └── ...
        ├── skills/
        │   ├── _shared/        ← 공유 절차 문서 (Read로 참조)
        │   │   ├── CONFLICT_RESOLUTION.md
        │   │   └── CHECK_LOOP.md
        │   ├── plan/
        │   │   └── SKILL.md
        │   ├── check/
        │   │   └── SKILL.md
        │   └── ...
        └── HELP.txt            ← 정적 도움말 텍스트
```

## 플러그인 기여하기

1. `plugins/` 하위에 새 플러그인 디렉토리를 생성합니다.
2. `.claude-plugin/marketplace.json`의 `plugins` 배열에 항목을 추가합니다.
3. **PR을 제출**합니다. CI에서 자동으로 유효성 검증이 실행됩니다.
