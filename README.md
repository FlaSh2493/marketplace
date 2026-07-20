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

# 예시
/plugin install cruise@flash-plugins
/plugin install jsync@flash-plugins
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
| `cruise` | 이슈 단위 개발 사이클 자동화 — 플랜·구현·검사·커밋·머지·PR·리뷰 | `/cruise:plan`, `/cruise:build`, `/cruise:check`, `/cruise:commit`, `/cruise:merge`, `/cruise:pr`, `/cruise:review` | 0.4.0 |
| `jsync` | Jira 이슈 REST API 기반 로컬 저장·편집·동기화 (컨텍스트 절약형) | `/jsync:list`, `/jsync:fetch`, `/jsync:draft`, `/jsync:update` | 0.2.0 |
| `gh-sub` | 복수 GitHub 계정 관리 및 저장소별 계정 전환 | `/gh-sub:switch`, `/gh-sub:add`, `/gh-sub:status` | 0.1.0 |
| `e2e-testid-sync` | E2E 테스트를 위한 test-id 및 aria-busy 상태 주입 | N/A | 0.1.0 |

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
    └── <plugin-name>/
        ├── .claude-plugin/
        │   └── plugin.json      ← 플러그인 메타데이터 (필수)
        └── skills/
            └── <skill-name>/
                └── SKILL.md     ← 스킬 정의 (필수)
```

## 플러그인 기여하기

1. `plugins/` 하위에 새 플러그인 디렉토리를 생성합니다.
2. `.claude-plugin/marketplace.json`의 `plugins` 배열에 항목을 추가합니다.
3. **PR을 제출**합니다. CI에서 자동으로 유효성 검증이 실행됩니다.
