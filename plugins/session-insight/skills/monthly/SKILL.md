---
name: session-insight-monthly
description: |
  지정 월(`YYYY-MM`, 생략 시 지난 달) 의 `weekly/<YYYY-MM-W*>.md` 들을 합산해 동일 8항목
  루브릭으로 월간 리포트를 작성하고 `<cwd>/.claude/session-insight/monthly/<YYYY-MM>.md`
  로 저장한다. daily/raw 는 보지 않는다 — weekly 마크다운만 입력으로 사용한다.
---

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

# session-insight:monthly

```
/session-insight:monthly             # 지난 달
/session-insight:monthly 2026-04     # 명시적 월
/session-insight:monthly 2026-04-27  # 그 날짜가 속한 월
```

## 절차

1. 인자에서 `YYYY-MM` 결정. 인자 생략 시 지난 달:
   ```bash
   date -v1d -v-1m +%Y-%m       # macOS
   date -d "$(date +%Y-%m-01) -1 day" +%Y-%m  # GNU
   ```

2. 그 월에 속한 weekly 키들을 glob 으로 수집:
   ```bash
   ls .claude/session-insight/weekly/<YYYY-MM>-W*.md 2>/dev/null
   ```

3. 각 weekly.md 파일을 Read 도구로 읽는다.
   - 파일이 0개면 종료 (파일 생성 안 함)
   - daily/raw 는 절대 보지 않는다

4. 합산한 weekly 마크다운들을 입력으로 8항목 루브릭을 채운다. 주간과 다른 점:
   - 1–7번: 주별 추세 + 월 단위로 굳어진 패턴 명시. 한 주만의 일회성 노이즈는 배제
   - 8번: direct_inputs 의 주별 추세 — 어느 주에 처음, 확산, 사라짐, 신규 등장

5. atomic write 로 `<cwd>/.claude/session-insight/monthly/<YYYY-MM>.md` 저장:
   ```bash
   mkdir -p .claude/session-insight/monthly
   # Write 도구로 .tmp 작성
   mv .claude/session-insight/monthly/<YYYY-MM>.md.tmp .claude/session-insight/monthly/<YYYY-MM>.md
   ```

## 출력 양식

```markdown
# 월간 분석: YYYY-MM

(헤더 한 줄 — weekly 합산 통계)

## 1. 토큰 부하
…(주별 추세, 월간 누적)
…
## 8. 반복 요구사항
…
```

## 에러 처리

| 상황 | 대응 |
|------|------|
| 해당 월 weekly.md 0개 | 헤더에 명시하고 파일 생성 안 함 |
| 잘못된 형식 | 사용법 안내 후 종료 |
