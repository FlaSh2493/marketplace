# 내 프로젝트 Claude Code 플러그인 마켓플레이스

## 프로젝트 개요

내 프로젝트 팀용 Claude Code 플러그인 마켓플레이스. 플러그인을 공유·설치할 수 있는 중앙 저장소.

## 공식 문서

플러그인 개발 시 아래 공식 문서를 항상 따른다.

- 플러그인 생성: https://code.claude.com/docs/en/plugins
- 플러그인 레퍼런스: https://code.claude.com/docs/en/plugins-reference
- 마켓플레이스 배포: https://code.claude.com/docs/en/plugin-marketplaces
- 스킬: https://code.claude.com/docs/en/slash-commands

## 핵심 규칙

### skills를 사용한다 (commands 사용 금지)

- `commands/` 디렉토리를 사용하지 않는다. 모든 명령어는 `skills/`로 작성한다.
- 스킬 구조: `skills/<skill-name>/SKILL.md` (디렉토리 + SKILL.md 형태)
- 스킬은 `/플러그인명:스킬명`으로 직접 호출하거나, 맥락에 맞게 자동 실행된다.
- SKILL.md에는 YAML frontmatter(`name`, `description`)를 반드시 포함한다.

#### 스킬 이름 규칙 — 디렉토리명 vs name 필드

| 항목 | 결정하는 값 | 예시 |
|------|------------|------|
| **슬래시 명령어** (콜론 뒤) | `skills/` 하위 **디렉토리명** | `/jira-report:create` ← 디렉토리가 `create` |
| **검색·목록 표시명** | SKILL.md frontmatter **`name` 필드** | 스킬 검색 시 `jira-report-create`로 표시 |
| **자동 실행 판단** | SKILL.md frontmatter **`description` 필드** | Claude가 맥락에 맞는 스킬인지 판단할 때 사용 |

- **디렉토리명**은 짧고 간결하게 작성한다 (예: `create`, `view`, `sync`)
- **`name` 필드**는 검색 시 사용자에게 보이는 표시명이므로, 플러그인명을 포함하여 맥락을 명확히 한다 (예: `jira-report-create`)
- 디렉토리명과 name 필드는 서로 다를 수 있지만, name 필드가 디렉토리명을 포함하도록 일관성을 유지한다

### 플러그인 디렉토리 구조

```
plugins/<plugin-name>/
├── .claude-plugin/
│   └── plugin.json          ← 플러그인 메타데이터 (필수)
└── skills/
    └── <skill-name>/
        └── SKILL.md         ← 스킬 정의 (필수)
```

### 플러그인 추가 시 체크리스트

1. `plugins/<plugin-name>/` 디렉토리 생성
2. `.claude-plugin/plugin.json` 작성 (name, description, version, author)
3. `skills/<skill-name>/SKILL.md` 작성 (frontmatter + 지시 내용)
4. `.claude-plugin/marketplace.json`의 `plugins` 배열에 항목 추가
5. **README.md 등록된 플러그인 테이블에 행 추가** (플러그인명, 설명, 명령어, 버전)
6. **README.md 플러그인 설치 섹션에 설치 명령어 추가**
7. **plugin.json 내용 확인** — 작성 완료 후 사용자에게 name, description, version, author 값이 맞는지 반드시 질문하고 확인받은 뒤 진행한다
8. **설치·실행 명령어 안내** — 플러그인을 처음 생성하거나 스킬 구조(디렉토리명, plugin.json name 등)가 변경될 때, 아래 형식으로 예상 명령어를 사용자에게 보여준다:
   ```
   마켓플레이스 등록:   /plugin marketplace add <owner>/<repo>
   플러그인 설치:       /plugin install <plugin-name>@<marketplace-name>
   스킬 실행:           /<plugin-name>:<skill-name>

   변경사항 반영 (업데이트):
   /plugin marketplace update
   /plugin uninstall <plugin-name>
   /plugin install <plugin-name>@<marketplace-name>
   ```
   - `<plugin-name>`은 `plugin.json`의 `name` 값
   - `<skill-name>`은 `skills/` 하위 **디렉토리명** (SKILL.md의 `name` 필드가 아님)
   - `<marketplace-name>`은 `marketplace.json`의 `name` 값

### plugin.json 형식

```json
{
  "name": "plugin-name",
  "description": "플러그인 설명",
  "version": "0.1.0",
  "author": {
    "name": "이름",
    "email": "email@example.com"
  }
}
```

### SKILL.md frontmatter 형식

```yaml
---
name: jira-report-create        # 검색·목록에서 표시되는 이름
description: 스킬 설명. Claude가 자동 실행 여부를 판단하는 데 사용된다.
---
```

- `name`: 스킬 검색·목록에서 사용자에게 보이는 표시명. 플러그인명-동작 형태로 작성 권장 (예: `jira-report-create`)
- `description`: Claude가 자동 실행 여부를 판단하는 데 사용. 스킬의 기능을 명확하게 서술한다

## 레거시 감지 및 마이그레이션

기존 플러그인이 공식 문서 기준으로 레거시 방식을 사용하고 있는 경우(예: `commands/` 사용, `skills/` 내 파일이 디렉토리+SKILL.md 구조가 아닌 경우 등), 최신 방식을 안내하고 마이그레이션할지 사용자에게 질문한다. 사용자가 동의하면 마이그레이션을 진행한다.

## 커밋 전 검증

`.claude/settings.json`의 PreToolUse 훅(`.claude/hooks/pre-commit-validate.sh`)이 git commit 명령을 감지하면 자동으로 아래 항목을 검증한다. 하나라도 충족되지 않으면 커밋을 차단하고 사용자에게 알린다.

- [ ] `commands/` 디렉토리가 사용되고 있지 않은가 (skills로 대체되었는가)
- [ ] 스킬이 `skills/<name>/SKILL.md` 구조를 따르는가
- [ ] SKILL.md에 YAML frontmatter(`name`, `description`)가 포함되어 있는가
- [ ] plugin.json의 name, description, version, author 값을 사용자에게 확인받았는가
- [ ] marketplace.json의 plugins 배열에 새 플러그인이 등록되어 있는가
- [ ] README.md 등록된 플러그인 테이블에 해당 플러그인이 추가되어 있는가
- [ ] README.md 플러그인 설치 섹션에 설치 명령어가 추가되어 있는가
- [ ] 레거시 방식이 남아있지 않은가 (있다면 마이그레이션 여부를 사용자에게 질문했는가)

## 설정 파일 구분

| 파일 | 용도 | 커밋 여부 |
|------|------|-----------|
| `.claude/settings.json` | 팀 공유 설정 (hooks 등) | O — 커밋한다 |
| `.claude/settings.local.json` | 개인 설정 (permissions 등) | X — 절대 커밋하지 않는다 (.gitignore) |

- `settings.json`은 프로젝트 레벨 훅, 공유 권한 등 팀 전체에 적용되는 설정을 담는다.
- `settings.local.json`은 개인 권한, 로컬 환경 등 개인에게만 해당하는 설정을 담는다.

## 플러그인 변경 반영 절차

마켓플레이스의 플러그인을 수정(스킬 내용, plugin.json 등)한 뒤 변경사항을 반영하려면 아래 순서를 따른다.

1. **마켓플레이스 업데이트** — 원격 저장소의 최신 변경사항을 로컬 마켓플레이스에 반영
   ```
   /plugin marketplace update
   ```
2. **플러그인 제거** — 기존 설치된 플러그인을 삭제
   ```
   /plugin uninstall <plugin-name>
   ```
3. **플러그인 재설치** — 업데이트된 마켓플레이스에서 플러그인을 다시 설치
   ```
   /plugin install <plugin-name>@<marketplace-name>
   ```

- 마켓플레이스만 업데이트하고 플러그인을 재설치하지 않으면 이전 버전이 그대로 유지된다.
- uninstall 없이 install만 하면 변경사항이 반영되지 않을 수 있다. 반드시 제거 후 재설치한다.

## 주의사항

- `settings.local.json`은 개인 설정이므로 절대 커밋하지 않는다.
- 플러그인 간 의존성을 만들지 않는다. 각 플러그인은 독립적으로 동작해야 한다.
- `.claude-plugin/` 안에는 `plugin.json`만 둔다. skills, agents, hooks는 플러그인 루트에 둔다.
