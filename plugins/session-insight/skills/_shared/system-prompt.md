<!--
session-insight 3 tier (daily / weekly / monthly) 가 동일하게 인용하는 공통 분석 규약.
SessionStop 안에서 직렬 호출될 때 prompt cache 적중을 위해 **바이트 단위로 동일** 해야 한다.
각 SKILL.md 도입부에 이 파일 내용을 그대로 복사한다 (include 메커니즘 없음).
-->

## 8항목 루브릭

```
1. 토큰 부하       — 가장 무거운 스킬 Top3 + 추정 원인, cache hit 낮은 스킬
2. 시행착오        — error_retry / abort / 같은 도구 반복
3. 이상 반응       — tool 에러·반복 호출·비정상 짧은 출력
4. 입력 품질       — 모호한 user_text → 긴 작업, 좋은 입력 사례
5. 도구 사용 패턴  — 비효율 시퀀스, tool_chars 큰 turn 정체
6. 최적화 제안     — 근거 인용 필수
7. 신규 스킬 후보  — 근거 인용 필수
8. 반복 요구사항   — direct_inputs 군집 (의도별 묶고 빈도·대표 인용)
```

## 출력 규칙

- 헤더 한 줄 — 필터 통과율·총 토큰·점수 분포
- 각 항목은 근거 인용(turn/세션 ID, 일자, 또는 직속 하위 tier 키) 첨부
- 관찰 없으면 "해당 없음" 명시
- 모든 산출물은 atomic write: 임시 파일에 쓰고 rename
- 같은 파일이 이미 있으면 덮어쓰기

## 손실 보완

daily.md 마지막에 "대표 세션 ID 3개" 섹션을 추가한다 (상위 tier 가 필요 시 드릴다운).
