---
name: jira-analyze
description: 코드베이스 구조와 Jira 티켓을 분석하여 도메인 그룹과 의존성을 분류합니다.
---

이 스킬은 CLI로 코드베이스 구조를 추출한 뒤 LLM으로 도메인 분류와 의존성을 분석합니다.

## 사전 조건
- `jira-fetch` 완료 (`.docs/{workspace}/_cache/{KEY}.snapshot.json` 존재)
- `references/domain-mapping.md` 판단 기준 로드

## 작업 (Tasks)

1. **코드베이스 구조 추출** (CLI, 1 tool call 배치):
   ```bash
   tree -L 2 -d --noreport src/ 2>/dev/null || tree -L 2 -d --noreport . 2>/dev/null
   find src -name "index.ts" -o -name "index.tsx" 2>/dev/null | head -30 | xargs head -15 2>/dev/null
   ```
   결과를 `/tmp/jira-structure.txt`에 저장. 전체 소스가 아닌 **이 요약만** LLM에 전달.

2. **Skill 로드**: `references/domain-mapping.md`

3. **LLM 도메인 분류**:
   - 입력: 구조 요약 + 선택된 티켓 요약 (각 `summary`, `labels`, `components`)
   - 출력: 각 티켓의 도메인 할당

4. **LLM 의존성 분석**:
   - 입력: 티켓 `linkedIssues` + 분류 결과
   - 출력: 도메인 간 의존 순서

5. **도메인 그룹 파일 생성** (CLI):
   `.docs/{workspace}/_index.yaml` 갱신:
   ```yaml
   domains:
     auth:
       tickets: [PROJ-123]
       can_parallelize: true
       complexity: medium
     payment:
       tickets: [PROJ-456]
       can_parallelize: true
       complexity: medium
     api:
       tickets: [PROJ-789]
       can_parallelize: false
       depends_on: [auth, payment]
       complexity: high
   ```

## 토큰 절약
- 코드베이스 구조: 전체 소스(~50k tok) 대신 tree + exports 요약(~500 tok)
- 티켓: summary + labels + components만 전달 (description 제외)

## 출력
- `.docs/{workspace}/_index.yaml` (domains 섹션 추가)

## 다음 단계
분류 완료 후 `jira-refine` 스킬로 티켓별 요구사항 정제를 진행한다.
