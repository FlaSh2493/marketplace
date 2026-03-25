---
name: fe-task-extractor-fetch
description: Jira에서 나에게 할당된 미완료 이슈들을 가져와서 프론트엔드 작업 명세(.docs/task/{브랜치명}/ 하위 개별 md 파일)로 생성하거나 업데이트하는 스킬. "내 지라 이슈 가져와줘", "내 할 일 불러와", "지라 기준으로 명세서 업데이트해" 등을 요청할 때 사용한다.
---

# Frontend Task Fetch (Jira to Markdown)

Jira에 등록된 이슈 중 **본인에게 할당된 미완료 작업**들을 불러와서, **이슈별 개별 마크다운 파일**로 변환하여 저장하는 스킬이다.

---

## 🚨 절대 준수 사항 (Strict Adherence)

이 스킬은 단순히 작업을 수행하는 것이 아니라, **정해진 표준화 절차를 100% 준수**해야 한다. 아래 사항을 어길 경우 후속 플러그인(`worktree-flow`)에서 데이터 로딩에 실패할 수 있다.

1.  **템플릿 우선 (Template First)**: 파일 생성/수정 전 **반드시** `templates/fe-task-template.md`를 `view_file`로 읽고, 헤더 필드 순서(`jira`, `상태`, `담당자` 등 6개)와 구분선(`---`) 형식을 완벽히 일치시킨다.
2.  **요약 금지 (No Summary)**: Jira의 Description은 요약하지 않는다. ADF를 마크다운 전문으로 변환하여 `## 설명` 섹션에 보존한다.
3.  **스크립트 실행 (Use Scripts)**: 경로 생성 시 `mkdir` 대신 `${CLAUDE_PLUGIN_ROOT}/scripts/init_task_dir.py`를 찾아 실행한다.
4.  **인터랙티브 선택**: Jira에서 가져올 이슈 목록을 반드시 **번호가 붙은 테이블**로 보여주고 사용자에게 선택받는다.

---

## 1. 대상 이슈 식별 및 필터링

이 스킬은 항상 다음 JQL 조건을 기본으로 하여 이슈를 검색한다:
- **Assignee**: `assignee = currentUser()` (본인에게 할당된 것만)
- **Status**: `statusCategory != Done` (완료되지 않은 것만)

사용자로부터 추가적인 범위를 입력받을 수 있다:
- **최근 이슈**: 위 기본 조건에 해당하는 최근의 스토리들
- **Project Key**: 특정 프로젝트 내 본인의 미완료 스토리 (`project = {KEY} AND ...`)
- **Epic Key**: 특정 에픽 하위의 본인의 미완료 스토리 (`"Epic Link" = {KEY} AND ...`)

---

## 2. 데이터 수집

### Step 1: Jira 데이터 조회
JQL(`assignee = currentUser() AND statusCategory != Done`)을 사용하여 대상 이슈들의 정보를 가져온다.
- **전체 조회**: 페이지네이션을 고려하여 **모든 이슈**를 누락 없이 가져온다 (필요시 `startAt` 반복 호출).

### Step 2: 대상 이슈 선택 (Interactive Selection)
조회된 이슈 목록을 **번호가 붙은 테이블** 형식으로 사용자에게 보여주고, 어떤 이슈들을 가져올지 선택받는다.

| 번호 | Jira Key | 작업 제목 | 상태 |
| :--- | :--- | :--- | :--- |
| 1 | {KEY} | {제목} | {상태} |

**선택 방식**:
- 인덱스 번호(예: "1, 3, 5") 또는 범위(예: "1-5")를 입력받아 다중 선택이 가능해야 한다.
- "전체" 또는 "all" 입력 시 모든 이슈를 선택한다.
- 사용자가 선택한 이슈들만 다음 단계로 넘어간다.

---

## 3. 이슈별 상세 데이터 수집

선택된 각 이슈에 대해 **상세 정보를 추가 조회**한다:

### 3-1. Description (전문)
- `jiraGetIssue` 등을 사용하여 Description 전체를 가져온다.
- Jira ADF(Atlassian Document Format)를 **마크다운으로 변환**한다.
- **요약하지 않는다.** 원본 구조(리스트, 테이블, 코드블록 등)를 보존한다.

### 3-2. 첨부파일 및 이미지
- 이슈의 `attachments` 필드에서 첨부파일 목록을 가져온다.
- **이미지 파일** (png, jpg, gif, svg, webp): 다운로드하여 `assets/` 폴더에 저장
  - 파일명 형식: `{JIRA-KEY}-{원본파일명}` (예: `PROJ-101-screenshot.png`)
  - 다운로드가 불가능한 경우 Jira 원본 URL을 기재
- **기타 파일** (pdf, xlsx 등): 다운로드 URL을 기재 (로컬 저장하지 않음)

### 3-3. 댓글
- `jiraGetIssueComments` 등을 사용하여 전체 댓글을 가져온다.
- **시간순 정렬** (오래된 것 → 최신)
- 작성자, 작성 시각, 내용을 기록
- 댓글 내용도 ADF → 마크다운 변환 적용

---

## 4. 마크다운 변환 및 저장

### Step 1: 저장 디렉토리 결정

현재 Git 브랜치명을 가져와서 디렉토리를 생성한다:

```bash
# 현재 브랜치명 확인
git rev-parse --abbrev-ref HEAD

# 플러그인 스크립트로 디렉토리 생성 (디렉토리 경로 반환)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_task_dir.py "{브랜치명}"
```

반환된 `dir` 경로에 이슈별 파일을 저장한다.

### Step 2: 템플릿 로드

**반드시** `templates/fe-task-template.md` 파일을 `view_file`로 읽고, 해당 템플릿의 구조·필드 순서·규칙을 **정확히** 따른다.

```
${CLAUDE_PLUGIN_ROOT}/templates/fe-task-template.md
```

### Step 3: 이슈별 마크다운 파일 생성

선택된 각 이슈에 대해 개별 md 파일을 생성한다:

- **파일명**: `{JIRA-KEY}.md` (예: `PROJ-101.md`)
- **저장 경로**: `{프로젝트 루트}/.docs/task/{브랜치명}/{JIRA-KEY}.md`
- **이미지 저장**: `{프로젝트 루트}/.docs/task/{브랜치명}/assets/{JIRA-KEY}-{파일명}`

**Jira 필드 → 템플릿 매핑:**

| 템플릿 필드 | Jira 소스 |
|------------|----------|
| `JIRA-KEY` | 이슈 Key (예: PROJ-101) |
| `작업 제목` | Summary |
| `상태` | Status |
| `담당자` | Assignee displayName |
| `생성일` | created date |
| `최근 업데이트` | 현재 시간 |
| `출처` | `jira-fetch` (고정) |
| `설명` | Description **전문** (마크다운 변환, 요약 금지) |
| `deps` | Description 내 '선행/후행' 정보 파싱. 없으면 `없음` |
| `api` | Description 내 'API' 정보 파싱. 없으면 `없음` |
| `states` | Description 내 'UI 상태' 정보 파싱. 없으면 `없음` |
| `첨부 이미지` | attachments 중 이미지 파일 → `./assets/` 참조 |
| `첨부 파일` | attachments 중 비이미지 파일 → URL 링크 |
| `댓글` | 전체 댓글 시간순 |

### Step 4: 포맷 검증 (저장 전 필수)

각 파일 저장 직전에 `templates/fe-task-template.md`의 **포맷 검증 체크리스트**를 모두 통과하는지 확인한다. 하나라도 불일치하면 수정한 뒤 저장한다.

### Step 5: 기존 파일 처리

동일한 `{JIRA-KEY}.md` 파일이 이미 존재하는 경우, 최신 Jira 정보로 덮어쓸지 사용자에게 묻는다.

---

## 5. 실행 완료 보고

가져오기가 완료되면 아래 형식으로 보고한다.

### ✅ Jira 이슈 가져오기 완료

| Jira Key | 작업 제목 | 상태 | 파일 |
| :--- | :--- | :--- | :--- |
| [{KEY}](URL) | {제목} | {상태} | `{JIRA-KEY}.md` |

**관련 정보**:
- **저장 경로**: `.docs/task/{브랜치명}/`
- **생성된 파일**: {N}개
- **가져온 기준**: {Project/Epic/Issue Keys}

---

## 6. 주의사항

- **다중 타입 지원**: `Story` 뿐만 아니라 `Task`, `Bug` 등 본인에게 할당된 모든 미완료 이슈를 대상으로 한다.
- **이미 있는 파일**: 동일 Jira Key 파일이 이미 존재하면 덮어쓸지 사용자에게 묻는다.
- **이미지 다운로드 실패**: 다운로드가 불가능한 경우 Jira 원본 URL을 대신 기재하고, 파일 내에 `<!-- 이미지 다운로드 실패: {URL} -->` 주석을 남긴다.
- **저장 경로 절대 준수**: 반드시 `.docs/task/{현재 브랜치명}/` 경로에 저장한다. 이 규칙을 위반하지 않는다.
