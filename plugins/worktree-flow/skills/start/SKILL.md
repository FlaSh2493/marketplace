---
name: worktree-flow-start
description: 현재 워크트리 또는 선택한 워크트리에 대한 작업 기획 정보를 가져와서 기획 단계(Plan mode)를 준비합니다.
---

# Worktree Start

현재 워크트리에서 작업을 시작하기 위해 로컬 작업 명세 디렉토리(`.docs/task/{feature}/`) 또는 Jira에서 상세 정보를 가져옵니다.

## 사용법

1. **메인 저장소에서 실행**: 활성화된 워크트리 목록 중 하나를 선택합니다.
   `/worktree-flow:start`
2. **워크트리 내부에서 실행**: 현재 워크트리의 이슈 번호를 사용하여 정보를 가져옵니다.
   `/worktree-flow:start`

## 실행

아래 스크립트를 실행하여 워크트리 정보를 확인하세요:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/start_worktree.py
```

## 2. 결과 처리 및 단계별 실행 (Strict Protocol)

### 🚨 STEP 1: 워크트리 식별 및 정보 추출
- **입력**: 스크립트 실행 결과.
- **실행**: 
  - 목록(`mode: selection`) 출력 시, `AskUserQuestion`으로 사용자에게 선택 요청.
  - 선택된 워크트리의 이슈 번호(Jira Key)와 피처 브랜치명을 확정.
- **검증**: `ls -d .docs/task/{feature}/` 경로 존재 여부 확인.
- **[LOCK]** 여기서 멈추고 선택된 작업 정보를 사용자에게 보고하십시오.

### 🚨 STEP 2: 환경 준비 및 WIP 설정 검증
- **상태 체크**: 
  - `.claude/settings.json` 내 `Stop` 훅 등록 여부 확인.
  - 현재 워크트리 루트에 `.wip-active` 파일 존재 여부 확인.
- **실행 (분기)**:
  - **Case A (미설정 시)**: 훅이 없거나 WIP가 꺼져 있다면, `AskUserQuestion`을 사용하여 **훅 등록 및 WIP 활성화(wip on)를 현재 즉시 수행할지** 물어보십시오.
  - **Case B (승인 시)**: `install_hooks.py` 실행 및 `touch .wip-active`를 통해 설정을 완료하십시오.
- **다음 단계**: 
  - 환경 준비가 완료되면 `task_boundary`를 통해 **기획(PLANNING) 모드**로 진입하십시오.
- **증거**: `.claude/settings.json`의 훅 내역과 `.wip-active` 생성 확인.
- **[LOCK]** 환경 설정에 대한 사용자의 승인 응답이 있을 때까지 대기하십시오.

### 🚨 STEP 3: 기획 수립 및 마크다운 기록 (PLANNING Mode Only)
- **전제 조건**: `task_boundary`를 통해 이미 **기획(PLANNING) 모드**에 진입한 상태여야 함.
- **실행**:
  - 현재 워크트리의 컨텍스트와 요구사항을 토대로 **상세 기획안(implementation_plan.md)** 작성.
  - **파일 동기화**: `fe-task-extractor`의 템플릿을 `view_file`로 읽은 뒤, `.docs/task/{feature}/{jira}.md` 파일의 `### 플랜` 섹션을 해당 내용으로 업데이트.
- **필수 출력**: 수립된 `implementation_plan.md`의 전체 내용을 **채팅창에 마크다운으로 출력**하여 가시성 확보.
- **[LOCK/GATE]** `notify_user(BlockedOnUser: true)`를 호출하여 **승인 버튼**을 노출하고, 사용자의 명시적 승인이 있을 때까지 대기하십시오.

### 🚨 STEP 4: 구현 시작 (Execution)
- **전제 조건**: 사용자가 'build'라고 입력하거나 승인 버튼을 누름.
- **실행**: `task_boundary`를 통해 **수행(EXECUTION) 모드**로 전환.
- **후속**: 실제 코드 수정을 시작하십시오.

## 3. 알림 (처음 사용하는 경우)

워크트리를 처음 시작했거나 훅을 등록하지 않은 경우, 다음을 안내하십시오:
1. **훅 등록**: `install_hooks.py` 실행 안내.
2. **WIP 활성화**: `/worktree-flow:wip on` 실행 권고.
해야 함을 강조하세요.
