# Listing Schema Reference

본 문서는 `e2e-testid-sync` 스킬의 단계별 JSON 산출물 스키마를 정의합니다.

## 1. Parsed Requirements (Phase 1 Output)
`parsed-requirements.json`

| 필드 | 타입 | 설명 |
| :--- | :--- | :--- |
| `meta` | `object` | 전체 요약 정보 (sourceFiles, totalItems, ambiguousCount 등) |
| `items` | `array` | 파싱된 개별 요구사항 객체 배열 |
| `items[].id` | `string` | 요구사항 ID (예: REQ-001) |
| `items[].rawText` | `string` | 원본 텍스트 |
| `items[].dataTestId` | `string` | 권장되는 test-id 값 |
| `items[].targetFile` | `string` | 추론된 대상 파일 경로 |
| `items[].targetElement`| `string` | 추론된 대상 요소 (Selector 또는 태그) |
| `items[].ariaBusy` | `boolean` | aria-busy 삽입 여부 |
| `items[].parseReasoning`| `string` | 파싱/추론 근거 (리스팅 단계에서 참조) |
| `items[].status` | `string` | `parsed` \| `ambiguous` |

## 2. Listing Item (Phase 3 Output)
`listing.json`

| 필드 | 타입 | 설명 |
| :--- | :--- | :--- |
| `id` | `string` | 리스팅 고유 ID (예: LST-001) |
| `reqId` | `string` | 원본 요구사항 ID |
| `dataTestId` | `string` | 최종 삽입할 test-id |
| `targetFile` | `string` | 검증된 대상 파일 경로 |
| `targetLine` | `number` | 요소가 위치한 라인 번호 |
| `oldStr` | `string` | `str_replace`에서 `old_str`로 사용할 정확한 문자열 |
| `newStr` | `string` | `str_replace`에서 `new_str`로 사용할 삽입 후 문자열 |
| `status` | `string` | `actionable` \| `ambiguous` \| `skip` \| `error` |
| `confidence` | `number` | 매칭 신뢰도 (0.0 ~ 1.0) |
| `ariaBusy` | `boolean` | aria-busy 삽입 여부 |
| `ariaBusyBinding` | `string` | (ariaBusy인 경우) 바인딩할 상태값 (예: `{isLoading}`) |
| `questions` | `array` | `ambiguous`일 때 사용자에게 할 질문 목록 |
| `matchReasoning` | `string` | 프로젝트 코드 매칭 근거 |

## 3. Injection Result (Phase 4 Output)
`injection-result.json`

| 필드 | 타입 | 설명 |
| :--- | :--- | :--- |
| `meta` | `object` | 삽입 결과 요약 (totalProcessed, success, failure 등) |
| `items` | `array` | 처리 결과 상세 리스트 |
| `items[].id` | `string` | 리스팅 ID |
| `items[].result` | `string` | `success` \| `failure` \| `skipped` |
| `items[].reason` | `string` | 실패 또는 스킵 사유 |
| `items[].retried` | `boolean` | 재시도 여부 |
