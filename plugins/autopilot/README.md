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
plan/work → check → merge → pr → cleanup
```

| 스킬 | 설명 |
|------|------|
| `plan {이슈키}` | Jira 이슈 명세를 로드하여 워크트리 생성 → 플랜 → 구현 |
| `work {이슈키} {요구사항}` | 기존 워크트리에 추가/수정 작업 (이슈 명세 재로드 없이) |
| `check` | 워크트리 내 lint, type-check, test 순차 실행. 오류 시 자동 수정 (최대 3회) |
| `merge {피처브랜치}` | 워크트리를 피처 브랜치에 rebase + fast-forward 머지 |
| `merge-all {피처브랜치}` | 모든 활성 워크트리를 충돌 수 기준 정렬 후 순차 머지 |
| `pr` | 현재 브랜치를 push하고 develop 대상 PR 자동 생성 |
| `cleanup {피처브랜치} {이슈키...}` | 머지 완료된 워크트리 정리 (브랜치 태그 보존 후 삭제) |
| `status` | 활성 워크트리 상태 조회 (브랜치, 커밋 수, 마지막 커밋) |
| `init` | 초기 설정 (code-review-graph 확인, 그래프 빌드, 사용법 안내) |

모든 스킬은 완료 후 자연스러운 다음 액션을 추천합니다.

---

## 핵심 기능

### 1. AI 기반 영향 범위 분석 플랜

`/autopilot:plan PLAT-101`을 실행하면:

1. 이슈 명세서에서 변경 예상 파일·컴포넌트·함수명 키워드를 추출
2. **code-review-graph** MCP 도구로 코드 의존성 그래프를 탐색해 실제 영향 파일 목록을 확보
3. 영향 파일 기준으로 필요한 파일만 읽어 플랜을 작성

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

### 5. WIP 히스토리 보존

머지 후 워크트리 브랜치는 삭제되지만, 커밋 히스토리는 태그로 보존됩니다:

```
archive/feat/sprint3/PLAT-101-wip-20260326
```

깔끔한 피처 브랜치 히스토리와 복원 가능한 작업 흔적을 동시에 유지합니다.

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

## 디렉토리 구조

```
.claude/worktrees/
└── PLAT-101/           ← 워크트리 경로 (worktree-PLAT-101 브랜치)
```

머지 후 WIP 히스토리는 git 태그로 보존됩니다:

```bash
# 특정 피처의 모든 이슈 태그 조회
git tag --list 'archive/feat/sprint3/*'

# WIP 이력 조회
git log archive/feat/sprint3/PLAT-101-wip-20260326
```

---

## 설치

```
/plugin marketplace add FlaSh2493/marketplace
/plugin install autopilot@flash-plugins
/autopilot:init
```

의존 플러그인: [code-review-graph](https://github.com/tirth8205/code-review-graph) (선택 — 없으면 fallback 탐색으로 동작)
