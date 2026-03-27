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
| `autopilot` | 이슈 단위 워크트리 자동화 — 플랜·구현·검사·머지·PR | `/autopilot:plan`, `/autopilot:work`, `/autopilot:check`, `/autopilot:merge`, `/autopilot:pr`, `/autopilot:status` | 0.1.0 |
| `task-sync` | 작업 명세와 Jira 양방향 동기화 | `/task-sync:extract`, `/task-sync:fetch`, `/task-sync:publish`, `/task-sync:update` | 0.1.0 |
| `gh-sub` | 복수 GitHub 계정 관리 및 저장소별 계정 전환 | `/gh-sub:switch`, `/gh-sub:add`, `/gh-sub:status` | 0.1.0 |
| `e2e-testid-sync` | E2E 테스트를 위한 test-id 및 aria-busy 상태 주입 | N/A | 0.1.0 |

### autopilot 워크플로우

```
plan/work → check → merge → cleanup
                 ↘ pr
```

| 스킬 | 설명 |
|------|------|
| `plan {이슈키}` | Jira 이슈 명세를 로드하여 워크트리 생성 → 플랜 → 구현 |
| `work {이슈키} {요구사항}` | 기존 워크트리에 추가/수정 작업 (이슈 명세 재로드 없이) |
| `check` | 워크트리 내 lint, type-check, test 순차 실행. 오류 시 자동 수정 (최대 3회) |
| `merge {피처브랜치}` | 워크트리를 피처 브랜치에 rebase + fast-forward 머지 |
| `merge-all {피처브랜치}` | 모든 활성 워크트리를 충돌 수 기준 정렬 후 순차 머지 |
| `pr` | 현재 브랜치를 push하고 develop 대상 PR 생성 |
| `cleanup {피처브랜치} {이슈키...}` | 머지 완료된 워크트리 정리 (브랜치 태그 보존 후 삭제) |
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
        ├── scripts/
        └── skills/
            ├── plan/
            │   └── SKILL.md
            ├── check/
            │   └── SKILL.md
            └── ...
```

## 플러그인 기여하기

1. `plugins/` 하위에 새 플러그인 디렉토리를 생성합니다.
2. `.claude-plugin/marketplace.json`의 `plugins` 배열에 항목을 추가합니다.
3. **PR을 제출**합니다. CI에서 자동으로 유효성 검증이 실행됩니다.
