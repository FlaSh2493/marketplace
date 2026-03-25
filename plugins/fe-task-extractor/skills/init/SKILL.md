---
name: fe-task-extractor-init
description: 현재 브랜치 이름을 기반으로 프론트엔드 작업 명세 디렉토리(.docs/task/{브랜치명}/)를 초기화하는 스킬. "태스크 초기화해줘", "브랜치 기준으로 폴더 만들어줘" 등을 요청할 때 사용한다.
---

# Frontend Task Init (Branch to Markdown)

현재 Git 브랜치 이름을 분석하여 표준화된 작업 명세 디렉토리 구조를 생성한다.

---

## 1. 브랜치 이름 분석 및 피처명 추출

Git 명령(`git rev-parse --abbrev-ref HEAD`)을 사용하여 현재 브랜치 이름을 가져온다.
브랜치 이름 전체를 피처명으로 사용한다. (슬래시 `/`를 포함한 전체 경로 유지)

- **브랜치명 예시**: `feature/login-ui` -> 피처명: `feature/login-ui`
- **브랜치명 예시**: `feature/auth/login` -> 피처명: `feature/auth/login`
- **브랜치명 예시**: `fix/bug-123` -> 피처명: `fix/bug-123`

---

## 🛠️ 경로 관리 가이드 (중요)

이 플러그인의 스크립트는 **플러그인 설치 폴더 내부의 `scripts/` 디렉토리**에 위치합니다.
에이전트는 이 `SKILL.md` 파일의 위치를 기준으로 상위 폴더들을 탐색하여 `scripts/` 폴더 내의 스크립트(`init_task_dir.py`)를 찾아야 합니다.

커맨드 실행 시, **스크립트의 절대 경로**를 확보하여 실행하십시오. (예: `${CLAUDE_PLUGIN_ROOT}/scripts/init_task_dir.py`)
현재 작업 디렉토리(CWD) 하위에 `scripts/`나 `plugins/` 폴더가 없을 수도 있으므로, 반드시 `${CLAUDE_PLUGIN_ROOT}/scripts/` 경로를 기반으로 스크립트를 찾아야 합니다.

---

## 2. 파일 생성 및 초기화

### Step 1: 파일 경로 결정
에이전트는 이 플러그인의 `${CLAUDE_PLUGIN_ROOT}/scripts/` 디렉토리 내의 `init_task_dir.py`를 찾아 실행한다:
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_task_dir.py "{피처명}"`
을 실행하여 저장할 마크다운 파일 경로를 확보한다.

### Step 2: 디렉토리 생성
해당 경로에 디렉토리가 없는 경우, 디렉토리와 `assets/` 하위 디렉토리를 함께 생성한다.

생성되는 구조:
```
.docs/task/{브랜치명}/
└── assets/
```

이미 디렉토리가 존재하는 경우, "이미 디렉토리가 존재합니다: {경로}" 메시지를 출력한다.

---

## 3. 실행 완료 보고

초기화가 완료되면 아래 형식으로 보고한다.

### ✅ 작업 명세 디렉토리 초기화 완료

- **브랜치명**: `{브랜치명}`
- **생성된 경로**: `.docs/task/{브랜치명}/`

이제 `/fe-task-extractor:extract` 또는 `/fe-task-extractor:fetch`를 사용하여 이슈별 md 파일을 생성할 수 있습니다.
