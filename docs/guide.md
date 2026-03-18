# 내 프로젝트 Claude Code 플러그인 마켓플레이스 사용 가이드

## 목차

1. [소개](#1-소개)
2. [빠른 시작](#2-빠른-시작)
3. [등록된 플러그인 목록](#3-등록된-플러그인-목록)
4. [플러그인 업데이트 및 관리](#4-플러그인-업데이트-및-관리)
5. [플러그인 만들기 (기여 가이드)](#5-플러그인-만들기-기여-가이드)
6. [스킬 이름 규칙](#6-스킬-이름-규칙)
7. [자동 검증 시스템](#7-자동-검증-시스템)
8. [설정 파일 이해하기](#8-설정-파일-이해하기)

---

## 1. 소개

### 마켓플레이스란?

내 프로젝트 팀이 Claude Code 플러그인을 **공유하고 설치**할 수 있는 중앙 저장소입니다.

### 동작 원리

마켓플레이스의 실체는 **GitHub 저장소**입니다. 별도의 서버나 패키지 레지스트리가 아니라, 저장소 루트의 `.claude-plugin/marketplace.json` 파일이 마켓플레이스 역할을 합니다.

```
GitHub 저장소 (<your-account>/marketplace)
└── .claude-plugin/marketplace.json   ← 이 파일이 플러그인 목록을 정의
└── plugins/                          ← 실제 플러그인 코드가 위치
```

Claude Code가 마켓플레이스를 등록하면 이 저장소를 로컬에 클론하고, `marketplace.json`의 `plugins` 배열을 읽어 설치 가능한 플러그인 목록을 파악합니다.

### 접근 제어 — 인가되지 않은 사용자

마켓플레이스의 접근 권한은 **GitHub 저장소 권한**으로 결정됩니다.

| 상황 | 결과 |
|------|------|
| **저장소 접근 권한 있음** (조직 멤버 등) | 마켓플레이스 등록·플러그인 설치 가능 |
| **저장소 접근 권한 없음** | `marketplace add` 단계에서 실패 — 저장소를 클론할 수 없으므로 플러그인 목록 자체를 가져올 수 없음 |
| **저장소 읽기 전용** (Read 권한) | 플러그인 설치는 가능하나, PR을 통한 기여는 Write 권한 필요 |

즉, **GitHub 저장소에 접근할 수 없는 사용자는 마켓플레이스의 어떤 기능도 사용할 수 없습니다.** 별도의 인증 시스템은 없으며, 모든 접근 제어는 GitHub이 담당합니다.

### 용어 정리

| 용어 | 설명 |
|------|------|
| **마켓플레이스** | 플러그인 목록을 관리하는 GitHub 저장소. `marketplace.json`이 핵심 |
| **플러그인** | 하나 이상의 스킬을 묶은 패키지. `plugin.json`으로 메타데이터 정의 |
| **스킬** | 사용자가 실행할 수 있는 개별 기능 단위. `SKILL.md`로 정의 |
| **슬래시 명령어** | `/플러그인명:스킬명` 형태로 스킬을 직접 호출하는 방법 |

---

## 2. 빠른 시작

### 2.1 마켓플레이스 등록

```bash
/plugin marketplace add <your-account>/marketplace
```

**내부 동작**: Claude Code가 `<your-account>/marketplace` GitHub 저장소를 로컬에 클론합니다. 이 과정에서 **GitHub 인증**이 필요하며, 저장소 접근 권한이 없으면 클론에 실패하고 등록이 거부됩니다.

> 인가되지 않은 사용자는 이 단계에서 차단됩니다. `git clone`이 실패하면 "저장소에 접근할 수 없습니다"와 같은 에러가 발생합니다.

등록이 완료되면 Claude Code는 `marketplace.json`을 읽어 사용 가능한 플러그인 목록을 인식합니다.

### 2.2 플러그인 설치

```bash
/plugin install jira-report@my-project-plugins
```

**내부 동작**: `marketplace.json`의 `plugins` 배열에서 `jira-report`를 찾고, `source` 경로(`./plugins/jira-report`)에 있는 파일들을 로컬 Claude Code 환경에 복사합니다.

- `jira-report` — `plugin.json`의 `name` 값 (플러그인 이름)
- `my-project-plugins` — `marketplace.json`의 `name` 값 (마켓플레이스 이름)

> 마켓플레이스 등록 없이 `install` 명령어를 실행하면, `my-project-plugins`라는 마켓플레이스를 찾을 수 없어 설치에 실패합니다.

### 2.3 스킬 실행

```bash
/jira-report:create
```

**내부 동작**: Claude Code가 설치된 `jira-report` 플러그인의 `skills/create/SKILL.md` 파일을 읽고, 그 안의 지시사항에 따라 동작을 수행합니다.

- `jira-report` — 플러그인 이름 (`plugin.json`의 `name`)
- `create` — 스킬 **디렉토리명** (`skills/create/`)

> 스킬은 슬래시 명령어로 직접 호출하는 것 외에도, Claude가 대화 맥락에서 `description`을 보고 **자동으로 실행**할 수도 있습니다.

### 2.4 설치 확인

설치된 플러그인은 Claude Code의 슬래시 명령어 자동완성에서 확인할 수 있습니다. `/jira-report`를 입력하면 사용 가능한 스킬 목록이 표시됩니다.

---

## 3. 등록된 플러그인 목록

### 플러그인은 어떻게 등록되는가

새 플러그인을 만들면 `CLAUDE.md`에 정의된 **플러그인 추가 시 체크리스트**에 의해 등록 과정이 자동으로 진행됩니다. Claude Code가 이 저장소에서 작업할 때 CLAUDE.md를 읽고, 체크리스트의 각 항목을 순서대로 수행합니다:

1. `plugins/<plugin-name>/` 디렉토리 및 필수 파일 생성
2. `.claude-plugin/marketplace.json`의 `plugins` 배열에 항목 추가
3. `README.md` 플러그인 테이블에 행 추가 및 설치 명령어 추가
4. `plugin.json` 내용을 사용자에게 확인 요청
5. 설치·실행 명령어 안내

즉, **개발자가 "플러그인을 만들어줘"라고 요청하면 Claude Code가 CLAUDE.md의 규칙에 따라 모든 등록 작업을 자동으로 처리**합니다. 수동으로 marketplace.json이나 README.md를 편집할 필요가 없습니다.

> 이 자동화는 CLAUDE.md가 저장소에 커밋되어 있기 때문에 가능합니다. Claude Code는 프로젝트 루트의 CLAUDE.md를 항상 읽고, 그 안의 지시사항을 따릅니다. 팀원 누구든 이 저장소에서 Claude Code를 사용하면 동일한 규칙이 적용됩니다.

### 현재 등록된 플러그인

아래 목록은 `CLAUDE.md` 체크리스트에 의해 자동으로 관리됩니다. 새 플러그인이 추가되면 Claude Code가 이 테이블과 `marketplace.json`, `README.md`에 자동으로 등록합니다.

| 플러그인 | 설명 | 명령어 | 버전 |
|---------|------|--------|------|
| `jira-report` | JIRA 분기별 Kanban 티켓 목록 및 스토리포인트 리포트 | `/jira-report:create` | 0.1.0 |

### jira-report 사용 예시

`/jira-report:create` 실행 시 자연어로 요청할 수 있습니다:

- "이번 분기 내 리포트 만들어줘" → 현재 분기, 현재 사용자 기준으로 자동 실행
- "2025년 Q1 IET 프로젝트 홍길동 리포트" → 모든 옵션이 추론되어 바로 실행
- "지난 분기 리포트" → 지난 분기 + 현재 사용자 기준, 프로젝트만 자동 감지

> 이 스킬은 JIRA/Confluence REST API를 사용합니다. 환경 변수(`JIRA_API_TOKEN` 등)가 설정되어 있지 않으면 설정 안내를 출력하고 종료합니다. API 토큰이 유효하지 않은 사용자는 JIRA/Confluence 데이터에 접근할 수 없습니다.

---

## 4. 플러그인 업데이트 및 관리

### 4.1 변경사항 반영 3단계

마켓플레이스에 있는 플러그인이 업데이트되었을 때, 로컬에 반영하려면 **세 단계를 모두** 수행해야 합니다.

```bash
# 1단계: 마켓플레이스 업데이트
/plugin marketplace update
```

**내부 동작**: 로컬에 클론된 마켓플레이스 저장소에서 `git pull`을 실행하여 원격의 최신 변경사항을 가져옵니다. 이 시점에서도 GitHub 접근 권한이 확인됩니다.

```bash
# 2단계: 기존 플러그인 제거
/plugin uninstall jira-report
```

**내부 동작**: 로컬 Claude Code 환경에 설치된 플러그인 파일을 삭제합니다.

```bash
# 3단계: 플러그인 재설치
/plugin install jira-report@my-project-plugins
```

**내부 동작**: 업데이트된 마켓플레이스에서 최신 플러그인 파일을 다시 복사합니다.

### 4.2 주의사항

- **uninstall 없이 install만 하면 변경사항이 반영되지 않을 수 있습니다.** 반드시 제거 후 재설치하세요.
- **marketplace update만 하고 재설치를 생략하면** 로컬에 설치된 플러그인은 이전 버전 그대로입니다. 마켓플레이스 저장소는 업데이트되었지만, 설치된 파일은 별도이기 때문입니다.

### 4.3 플러그인 제거

더 이상 사용하지 않는 플러그인은 uninstall로 제거합니다:

```bash
/plugin uninstall jira-report
```

---

## 5. 플러그인 만들기 (기여 가이드)

새로운 플러그인을 만들어 마켓플레이스에 기여하는 방법입니다.

### 접근 권한 요구사항

플러그인을 기여하려면 마켓플레이스 GitHub 저장소에 **Write 권한**이 필요합니다. Read 권한만으로는 플러그인을 사용할 수 있지만 기여(PR 제출)는 불가합니다. 조직 외부 사용자는 Fork → PR 방식도 사용할 수 있으나, 리뷰어가 merge해야 반영됩니다.

### 5.1 디렉토리 구조

```
plugins/my-plugin/
├── .claude-plugin/
│   └── plugin.json          ← 플러그인 메타데이터 (필수)
├── skills/                  ← 스킬 디렉토리 (필수)
│   └── my-skill/
│       └── SKILL.md         ← 스킬 정의 파일
├── agents/                  (선택) 에이전트 정의
├── hooks/                   (선택) 훅 스크립트
└── .mcp.json                (선택) MCP 서버 설정
```

> `.claude-plugin/` 안에는 `plugin.json`만 둡니다. skills, agents, hooks는 플러그인 루트에 위치합니다.

### 5.2 plugin.json 작성법

```json
{
  "name": "my-plugin",
  "description": "플러그인 설명",
  "version": "0.1.0",
  "author": {
    "name": "이름",
    "email": "email@example.com"
  }
}
```

| 필드 | 설명 |
|------|------|
| `name` | 플러그인 고유 이름. 슬래시 명령어의 콜론 앞에 사용됨 (`/name:skill`) |
| `description` | 플러그인의 기능 요약 |
| `version` | 시맨틱 버전 (예: `0.1.0`) |
| `author` | 작성자 정보. `name`과 `email` 포함 |

### 5.3 SKILL.md 작성법

```yaml
---
name: my-plugin-create
description: 무언가를 생성합니다. Claude가 자동 실행 여부를 판단할 때 이 설명을 참고합니다.
---

여기에 스킬의 지시 내용을 작성합니다.
Claude가 이 내용을 읽고 동작을 수행합니다.
```

**frontmatter 필드 역할:**

| 필드 | 역할 | 예시 |
|------|------|------|
| `name` | 스킬 검색·목록에서 사용자에게 표시되는 이름 | `jira-report-create` |
| `description` | Claude가 대화 맥락에서 자동 실행 여부를 판단하는 기준 | "JIRA 리포트를 생성합니다" |

**본문**: Claude에게 주는 지시사항입니다. REST API 호출 방법, 실행 흐름, 오류 처리 등을 구체적으로 기술합니다.

### 5.4 marketplace.json 등록

`.claude-plugin/marketplace.json`의 `plugins` 배열에 새 플러그인을 추가합니다:

```json
{
  "plugins": [
    {
      "name": "my-plugin",
      "source": "./plugins/my-plugin",
      "description": "플러그인 설명",
      "version": "0.1.0",
      "category": "카테고리"
    }
  ]
}
```

**내부 동작**: Claude Code는 `install` 명령 실행 시 이 배열에서 `name`으로 플러그인을 찾고, `source` 경로를 기준으로 파일을 복사합니다. 여기에 등록되지 않은 플러그인은 `plugins/` 디렉토리에 존재하더라도 설치할 수 없습니다.

### 5.5 README.md 업데이트

두 곳을 업데이트해야 합니다:

**1) 등록된 플러그인 테이블에 행 추가:**

```markdown
| `my-plugin` | 플러그인 설명 | `/my-plugin:my-skill` | 0.1.0 |
```

**2) 플러그인 설치 섹션에 설치 명령어 추가:**

```bash
/plugin install my-plugin@my-project-plugins
```

### 5.6 체크리스트

커밋 전 아래 항목을 모두 확인하세요. Pre-commit 훅이 자동으로 검증하지만, 미리 확인하면 반려를 줄일 수 있습니다.

- [ ] `skills/<name>/SKILL.md` 구조를 따르는가 (`commands/` 사용 금지)
- [ ] SKILL.md에 YAML frontmatter(`name`, `description`)가 있는가
- [ ] `plugin.json`의 name, description, version, author가 정확한가
- [ ] `marketplace.json`의 plugins 배열에 등록했는가
- [ ] README.md 플러그인 테이블에 추가했는가
- [ ] README.md 설치 섹션에 명령어를 추가했는가

---

## 6. 스킬 이름 규칙

스킬의 이름은 **세 곳**에서 각기 다른 역할을 합니다:

| 결정하는 값 | 역할 | 예시 |
|------------|------|------|
| `skills/` 하위 **디렉토리명** | 슬래시 명령어 (콜론 뒤) | `/jira-report:create` ← 디렉토리가 `create` |
| SKILL.md의 **`name` 필드** | 스킬 검색·목록 표시명 | 검색 시 `jira-report-create`로 표시 |
| SKILL.md의 **`description` 필드** | Claude 자동 실행 판단 | 맥락에 맞으면 자동으로 스킬 실행 |

### 작성 권장사항

- **디렉토리명**: 짧고 간결하게 — `create`, `view`, `sync`, `delete`
- **name 필드**: 플러그인명을 포함하여 명확하게 — `jira-report-create`, `jira-report-delete`
- **description 필드**: Claude가 이해할 수 있도록 기능을 명확히 서술

### 예시: jira-report 플러그인

```
plugins/jira-report/
└── skills/
    └── create/              ← 디렉토리명 → /jira-report:create
        └── SKILL.md
            name: jira-report-create       ← 검색 시 표시
            description: JIRA 분기별 ...    ← 자동 실행 판단
```

---

## 7. 자동 검증 시스템

마켓플레이스는 **두 단계**의 자동 검증으로 플러그인 품질을 보장합니다.

### 7.1 Pre-commit Hook (로컬 검증)

`.claude/settings.json`에 등록된 PreToolUse 훅이 `git commit` 명령을 감지하면 자동으로 실행됩니다.

**내부 동작**: Claude Code가 Bash 도구로 `git commit`을 실행하려 할 때, `.claude/hooks/pre-commit-validate.sh` 스크립트가 먼저 실행됩니다. 검증에 실패하면 `permissionDecision: "deny"`를 반환하여 **커밋 자체를 차단**합니다.

**검증 항목:**

| 검증 | 설명 |
|------|------|
| `commands/` 미사용 | 레거시 `commands/` 디렉토리가 존재하면 차단 |
| 스킬 구조 | `skills/<name>/SKILL.md` 형태가 아니면 차단 (느슨한 .md 파일 감지) |
| frontmatter 검증 | SKILL.md에 `name`, `description` 필드가 없으면 차단 |
| marketplace.json 등록 | `plugins/` 내 플러그인이 marketplace.json에 없으면 차단 |
| README.md 문서화 | 플러그인이 README.md에 언급되지 않으면 차단 |

**검증 실패 시 대응:**

훅이 커밋을 차단하면 에러 메시지에 구체적인 문제가 표시됩니다:

```
커밋 전 검증 실패:
- plugins/my-plugin/commands/ 디렉토리가 존재합니다. skills/로 대체해야 합니다.
- plugins/my-plugin/skills/my-skill/SKILL.md frontmatter에 description 필드가 없습니다.
```

각 에러를 수정한 후 다시 커밋하면 됩니다.

> 이 훅은 `.claude/settings.json`에 정의되어 있으므로, 저장소를 클론하면 별도 설정 없이 자동으로 적용됩니다. 팀 전체에 동일한 검증 규칙이 적용되는 구조입니다.

### 7.2 CI/CD — GitHub Actions (원격 검증)

PR을 제출하면 `.github/workflows/validate.yml`이 자동으로 실행됩니다.

**트리거 조건**: `plugins/**` 또는 `.claude-plugin/marketplace.json` 파일이 변경된 PR

**검증 단계:**

1. `claude plugin validate .` — Claude Code 공식 유효성 검증
2. `marketplace.json` JSON 문법 검증
3. 모든 `plugin.json` 파일의 JSON 문법 검증

**접근 제어와의 관계**: CI 검증은 GitHub Actions가 실행하므로, PR을 제출할 수 있는 사용자(Write 권한 또는 Fork)만 이 검증을 트리거할 수 있습니다. CI 통과 여부와 무관하게, 최종 merge 권한은 저장소 관리자에게 있습니다.

---

## 8. 설정 파일 이해하기

### 8.1 settings.json — 팀 공유 설정

**파일 위치**: `.claude/settings.json`
**커밋 여부**: O (저장소에 포함)

팀 전체에 적용되는 설정을 담습니다. 현재는 pre-commit 검증 훅이 등록되어 있습니다:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/pre-commit-validate.sh"
          }
        ]
      }
    ]
  }
}
```

**내부 동작**: Claude Code가 Bash 도구를 사용할 때마다 이 훅이 실행됩니다. 훅 스크립트 내부에서 `git commit` 명령인지 판별한 후, 커밋이 아니면 즉시 통과시킵니다.

> 저장소를 클론/풀 받으면 별도 설정 없이 바로 적용됩니다. 팀원이 개별적으로 훅을 설치할 필요가 없습니다.

### 8.2 settings.local.json — 개인 설정

**파일 위치**: `.claude/settings.local.json`
**커밋 여부**: X (`.gitignore`에 포함 — **절대 커밋하지 않습니다**)

개인 권한 설정, 로컬 환경 설정 등 개인에게만 해당하는 내용을 담습니다. 예를 들어, 특정 bash 명령어의 자동 허용 등을 설정할 수 있습니다.

> API 토큰 등 민감한 정보를 `settings.local.json`의 `env`에 저장하면 Claude Code가 환경 변수로 인식합니다. 이 파일은 로컬에만 존재하므로 토큰이 외부에 노출되지 않습니다.

### 8.3 병합 동작

Claude Code는 두 설정 파일을 **자동으로 병합(merge)** 하여 사용합니다:

```
settings.json (팀 공유)  +  settings.local.json (개인)  →  최종 설정
```

- 서로 다른 키: 두 파일의 설정이 모두 적용됩니다
- 같은 키가 충돌: `settings.local.json`이 우선합니다

**실무 예시:**

| 설정 | 파일 | 이유 |
|------|------|------|
| Pre-commit 검증 훅 | `settings.json` | 팀 전체 적용 |
| 개인 bash 명령어 허용 | `settings.local.json` | 개인 환경 차이 |
| API 토큰 (env) | `settings.local.json` | 민감 정보 보호 |
