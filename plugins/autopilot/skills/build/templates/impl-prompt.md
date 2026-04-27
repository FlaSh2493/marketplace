# Phase {N}: {제목}

## 메타
- depends_on: {depends_on}
- scope: {scope}
- output_shape: {output_shape}
- 처리 방식: {처리 방식}

## 작업
{Plan의 해당 Phase 섹션 내용}

## 의존 Phase 결과
{의존 Phase의 종결 요약 또는 "없음"}

## 출력 형식 (필수)
- 변경 파일별 전체 내용 출력
- 코드 외 설명 금지
- 새 파일과 수정 파일을 명확히 구분

## 금지 사항
- Plan에 없는 리팩토링
- 무관한 import 정리
- 시그니처 변경 (Plan 명시 외)
- 주석 추가 (Plan 명시 외)

## 멈춤 조건
- Plan이 모호한 부분이 있으면 임의 보강하지 말고 사용자에게 질문
