---
name: jira-init
description: Jira 플러그인 워크스페이스를 초기화하고 .docs/work/{workspace}/ 폴더 구조를 생성합니다.
---

이 스킬은 `/jira init` 또는 `/jira auto` 최초 실행 시 워크스페이스 환경을 준비합니다.

## 작업 (Tasks)

1. **settings.yaml 확인**: `.claude/settings.yaml`의 `docs.workspace` 값을 읽는다.
   - 값이 있으면 → `.docs/work/{workspace}/` 디렉토리 존재 여부 확인
     - 존재하면 → 기존 워크스페이스 사용, 스킬 종료
     - 미존재하면 → 에러: "workspace 경로 불일치. settings.yaml을 확인하거나 /jira init을 다시 실행하세요."
   - 값이 없으면 → 다음 단계로

2. **워크스페이스 이름 입력받기**: 사용자에게 작업 디렉토리 이름을 요청한다.
   - 예시 제공: `sprint-q2`, `hotfix-prod`, `refactor-auth`
   - `/jira init {name}` 형태로 직접 지정된 경우 그 값을 사용

3. **디렉토리 생성** (CLI):
   ```bash
   mkdir -p .docs/work/{workspace}/_cache
   ```

4. **settings.yaml 기록** (CLI):
   ```yaml
   docs:
     root: ".docs/work"
     workspace: "{workspace}"
   ```
   - 파일이 없으면 생성, 있으면 `docs` 섹션만 갱신

5. **_index.yaml 초기화** (CLI):
   ```yaml
   workspace: "{workspace}"
   created_at: "{ISO8601}"
   tickets: []
   ```

6. **완료 보고**: "워크스페이스 '{workspace}' 생성 완료. `.docs/work/{workspace}/` 경로를 사용합니다."

## 출력
- `.docs/work/{workspace}/_cache/` 디렉토리
- `.docs/work/{workspace}/_index.yaml`
- `.claude/settings.yaml` (docs 섹션 갱신)

## 다음 단계
초기화 완료 후 `jira-fetch` 스킬로 티켓을 조회한다.
