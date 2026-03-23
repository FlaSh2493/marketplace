---
name: e2e-testid-parse
description: .docs/e2e/ 폴더의 요구사항 파일을 파싱하여 구조화된 JSON을 생성합니다.
---

이 스킬은 사용자가 준비한 비정규 요구사항 파일을 읽고, `e2e-parser` 서브에이전트를 통해 시스템이 이해할 수 있는 데이터 구조로 변환합니다.

## 작업 (Tasks)

1. `.docs/e2e/{YYYYMMDD}/` 폴더 내의 요구사항 파일들을 읽습니다.
2. `e2e-parser` 서브에이전트를 호출하여 내용을 분석합니다.
3. `.docs/e2e/{YYYYMMDD}/parsed-requirements.json` 파일을 생성합니다.
4. 파싱 결과를 요약 보고하고, 모호한 항목(`ambiguous`)이 있는 경우 사용자에게 확인을 요청합니다.

성공적으로 파싱이 완료되면 `e2e-testid-sync` 스킬을 통해 실제 코드에 반영할 수 있습니다.
