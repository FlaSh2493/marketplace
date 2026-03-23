---
name: jira-create
description: "요구사항 파일을 분석하여 이슈별로 분할하고 Jira에 등록합니다. Use when the user provides a spec file or says 'create issues from requirements'."
argument-hint: "<파일경로> (예: login-spec.md)"
disable-model-invocation: true
---

## 동작
1. 파일 읽기 + {workDir}/jira-planner/specs/{name}/spec.md 에 사본 저장
2. **사용자에게 대상 Jira Project Key(예: IET)를 확인합니다.**
3. requirement-splitter 에이전트 호출
   → **전달받은 Project Key와 임시 번호(예: IET-TEMP-1)**를 사용하여 이슈 분할
   → issues/{이슈키}.md 파일 생성
4. 사용자에게 분할 결과 출력 + 수정 기회
5. ✅ Gate 1: 분할 승인
6. dependency-analyzer 에이전트 호출
   → 실행 순서 결정 + 작업 모드 추천
7. ✅ Gate 2: 승인 → Jira 이슈 생성
   a. Jira API(MCP)로 이슈를 실제 생성하고 **반환된 실제 이슈 키(예: IET-105)**를 기록합니다.
   b. **동기화**:
      - `issues/IET-TEMP-1.md` → `issues/IET-105.md`로 파일명 변경
      - `state.json` 및 파일 내용 내의 임시 키를 실제 키로 일괄 교체
8. 완료 메시지 + /jira-start 안내
