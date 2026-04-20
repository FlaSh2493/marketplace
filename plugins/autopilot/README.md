# autopilot

> Claude Code에서 이슈 단위 병렬 개발을 완전 자동화하는 플러그인

이슈 키 하나로 워크트리 생성 → AI 플랜 수립 → 코드 구현 → 품질 검사 → Rebase merge → PR 생성까지, 개발 워크플로우 전 구간을 Claude가 직접 관리합니다.

---

## 왜 autopilot인가

### 문제: 브랜치 전환의 비용

여러 이슈를 동시에 작업할 때 `git stash` + `git checkout`의 반복은 컨텍스트를 끊고 실수를 유발합니다. 작업 중인 내용을 임시로 치워두고, 돌아올 때 다시 펼쳐야 하는 이 흐름 자체가 생산성을 갉아먹습니다.

### 해결: 이슈별 격리된 워크트리

git worktree는 하나의 레포에서 여러 작업 디렉토리를 동시에 유지합니다. autopilot는 이 기능을 Claude Code의 스킬 시스템과 연결해, 이슈 키만 입력하면 격리 환경 생성부터 구현까지 자동으로 처리합니다.

---

## 워크플로우

```
plan → req → check[-all] → merge[-all] → pr → cleanup
```

| 스킬 | 설명 |
|------|------|
| `plan {브랜치명} [이슈키...] [--no-spec]` | 워크트리 생성 → 이슈 명세 로드 → 플랜 → 구현. `--no-spec`으로 명세 없이 요구사항 기반 작업 가능 |
| `req [이슈키]` | 대화에서 추가 요구사항을 추출하여 이슈 문서에 기록 |
| `check` | 워크트리 내 lint, type-check, test 순차 실행. 오류 시 자동 수정 (최대 3회) |
| `check-all` | 메인 세션에서 모든 활성 워크트리 일괄 검사. 오류 시 자동 수정. 전체 통과 시 merge-all 제안 |
| `merge {피처브랜치}` | 워크트리를 피처 브랜치에 rebase + fast-forward 머지 |
| `merge-all {피처브랜치}` | 모든 활성 워크트리를 충돌 수 기준 정렬 후 순차 머지 |
| `pr` | 현재 브랜치를 push하고 develop 대상 PR 자동 생성 |
| `cleanup {피처브랜치} {브랜치명...}` | 머지 완료된 워크트리 정리 (워크트리 제거 + 브랜치 삭제) |
| `status` | 활성 워크트리 상태 조회 (브랜치, 커밋 수, 마지막 커밋) |
| `init` | 초기 설정 (code-review-graph 확인, 그래프 빌드, 사용법 안내) |

모든 스킬은 완료 후 자연스러운 다음 액션을 추천합니다.

---

## 핵심 기능

### 1. AI 기반 영향 범위 분석 플랜

`/autopilot:plan feat/sprint3 PLAT-101`을 실행하면:

1. 이슈 명세서에서 변경 예상 파일·컴포넌트·함수명 키워드를 추출
2. **code-review-graph** MCP 도구로 코드 의존성 그래프를 탐색해 실제 영향 파일 목록을 확보
3. 영향 파일 기준으로 필요한 파일만 읽어 플랜을 작성

이슈를 여러 개 지정하면 (`PLAT-101 PLAT-102`) 상호 영향을 고려한 통합 플랜을 수립합니다.

플랜 확인 후 사용자가 승인해야만 코드 수정이 시작됩니다.

### 2. 자동 품질 검사 + 자동 수정

`/autopilot:check`를 실행하면:

1. 워크트리 내 변경 파일 기반으로 앱 디렉토리 자동 탐지 (monorepo 대응)
2. 패키지 매니저 자동 판별 (pnpm / yarn / npm)
3. lint → type-check → test 순차 실행
4. 오류 발생 시 에러 분석 → 코드 수정 → 재실행 (최대 3회)
5. 린터 자동 판별 (eslint / biome 등)로 --fix 적용

### 3. Rebase + Fast-forward 머지

`/autopilot:merge feat/sprint3`을 실행하면:

- 미커밋 변경사항을 논리적 단위로 그룹핑하여 개별 커밋
- 피처 브랜치 위에 rebase 후 fast-forward 머지
- 충돌 시 파일별로 `feature / base / 직접편집` 인터랙티브 해결
- 커밋 메시지에 요구사항·작업내용·특이사항을 구조화

### 4. PR 자동 생성

`/autopilot:pr`을 실행하면:

- 커밋 로그 + diff 분석으로 PR 제목/본문 자동 작성
- 도메인 라벨 자동 추론 (변경 파일 경로 기반)
- 사용자 확인 후 push → PR 생성

### 5. 프로젝트 커스텀 지침 (External Instructions)

`.autopilot-instructions/` 디렉토리에 스킬별 지침을 추가하여 기본 동작을 세밀하게 제어할 수 있습니다.

- **위치**: 프로젝트 루트 (git root)
- **규칙**: `.autopilot-instructions/{skill-name}.md`
- **우선순위**: 커스텀 지침이 기본 `SKILL.md` 보다 우선합니다.

**사용 예시 (`.autopilot-instructions/build.md`):**
```markdown
- 모든 커밋 메시지는 영문으로만 작성한다.
- 패키지 추가 시 반드시 pnpm을 고수한다.
- 특정 디렉토리(A) 수정 시 관련 컴포넌트(B)도 함께 검토한다.
```

---

## 구조적 특이사항

### 스크립트와 Claude의 역할 분리

모든 git 조작은 Python 스크립트가 담당하고, Claude는 스크립트 출력을 해석해 사용자에게 전달합니다. Claude가 직접 `git merge`나 `git reset`을 실행하는 것을 **에이전트 정의 수준에서 금지**합니다.

```
exit 0 → 다음 스텝 진행
exit 1 → reason 그대로 출력 후 STOP (우회 금지)
exit 2 → 충돌 해결 프로세스 진입 (merge 전용)
```

### GATE 패턴 — 되돌리기 어려운 작업은 사람이 확인

- 플랜 수립 후 구현 시작 전: `ExitPlanMode` 게이트
- 머지 전 커밋 목록 확인: `AskUserQuestion` 게이트
- 충돌 파일 처리 방식: 파일마다 `AskUserQuestion` 게이트
- PR 생성 전 제목/본문 확인: `AskUserQuestion` 게이트

자동화하되, 되돌리기 어려운 시점에는 반드시 사람이 개입합니다.

### code-review-graph 연동 — Fallback 포함

코드 의존성 그래프가 없으면 Claude가 직접 Glob/Grep으로 탐색하는 fallback이 있어 그래프 없이도 동작합니다. 그래프가 있을 때는 `semantic_search_nodes_tool` → `get_impact_radius_tool` 순서로 연쇄 호출해 변경 파일의 의존 범위를 2-hop까지 추적합니다.

---

## 워크트리 위치 설정

워크트리가 생성될 경로를 settings 파일에서 지정할 수 있습니다. 설정이 없으면 **레포 부모 디렉토리(sibling)**가 기본값입니다 — 원본 레포와 동일 깊이에 워크트리가 생성됩니다.

**`.claude/settings.local.json`** (개인 설정 권장):
```json
{
  "autopilot": {
    "worktreeRoot": "../worktrees"
  }
}
```

- 상대경로는 설정 파일이 있는 `.claude/` 디렉토리 기준으로 resolve됩니다
- `"../worktrees"` → 레포 부모 디렉토리 하위 `worktrees/`
- 절대경로도 사용 가능: `"/Users/me/worktrees/my-project"`
- 탐색 순서: `settings.local.json` → `settings.json` (프로젝트 → 글로벌)

## 디렉토리 구조

기본값 (설정 없을 때):
```
<repo-parent>/
├── marketplace/        ← 원본 레포
└── PLAT-101/           ← sibling 워크트리 (worktree-PLAT-101 브랜치)
```

rebase + fast-forward 머지이므로 커밋은 피처 브랜치에 그대로 남습니다. cleanup 시 워크트리와 브랜치만 삭제합니다.

---

## 설치

```
/plugin marketplace add FlaSh2493/marketplace
/plugin install autopilot@flash-plugins
/autopilot:init
/plugin marketplace update
```

### 의존성 (Dependencies)

- **`jq`**: 세션 상태 추적 훅에서 JSON 파싱을 위해 사용합니다. (`brew install jq`)
- [code-review-graph](https://github.com/tirth8205/code-review-graph) (선택 — 없으면 fallback 탐색으로 동작)

---

## 세션 상태 추적 (Session Tracking)

Claude Code 세션의 busy/idle 생애주기를 실시간으로 파일에 기록합니다. 이를 통해 tmux status bar, 시스템 알림, 또는 외부 GUI 앱이 세션 상태를 사이드 채널로 구독할 수 있습니다.

### 상태 파일 위치
모두 레포 루트 기준 `tasks/.state/` 디렉토리에 생성됩니다.

- `tasks/.state/current`: 가장 최근 활동이 있는 세션의 `status.json` 심볼릭 링크.
- `tasks/.state/sessions/<session_id>/status.json`: 해당 세션의 현재 상태 (busy/idle).
- `tasks/.state/sessions/<session_id>/log.jsonl`: 세션 내 모든 상태 변경 이력.
- `tasks/.state/by-pid/<pid>.id`: 실행 중인 Claude 프로세스 ID로 세션 ID를 조회할 때 사용.
