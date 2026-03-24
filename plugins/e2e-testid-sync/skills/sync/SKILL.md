---
name: e2e-testid-sync
description: 파싱된 요구사항을 바탕으로 React 프로젝트에 data-testid 및 aria-busy 속성을 주입하고 관리합니다. (메인 작업)
---

이 스킬은 이미 구조화된 `parsed-requirements.json` 파일을 바탕으로 실제 프로젝트 코드와 대조하여 속성을 주입하는 핵심 워크플로우를 수행합니다.

## 작업 (Tasks)
1. **작업 범위 선정**: 파싱된 항목 중 이번 세션에서 작업할 Scope(auth, dashboard 등)를 선택합니다.
2. **리스팅 & 매칭**: `e2e-listing` 서브에이전트를 통해 요구사항과 실제 코드 요소를 매칭하고 검증합니다. (20개 단위 배치 처리)
   - 이 과정에서 생성된 `listing-summary.md`를 **반드시 사용자에게 즉시 보여주고 확인**을 받습니다. 가독성 있게 마크다운 테이블로 출력하십시오.

3. **코드 주입 (Injection)**: `e2e-injector` 서브에이전트를 사용하여 `data-testid` 및 `aria-busy` 속성을 코드에 반영합니다. (10개 파일 단위 배치 처리)
4. **검증 및 보고**: `e2e-testid-verify` 스킬을 호출하여 PDF 요구사항과 실제 코드를 1:1 대조하고, `result.json` 및 `summary.md` 산출물을 생성하여 사용자에게 보고합니다.

이 스킬을 실행하기 전, 반드시 `e2e-testid-parse`를 통해 최신 요구사항이 파싱되어 있어야 합니다.
