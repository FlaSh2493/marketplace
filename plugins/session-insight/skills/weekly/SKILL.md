---
name: session-insight-weekly
description: |
  지정 month-week 키(`YYYY-MM-WN`) 또는 날짜의 `daily/<YYYY-MM-DD>.md` 7개를 합산해
  동일 8항목 루브릭으로 주간 리포트를 작성하고
  `<cwd>/.claude/session-insight/weekly/<YYYY-MM-WN>.md` 로 저장한다.
  raw 세션은 보지 않는다 — daily 마크다운만 입력으로 사용한다.
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

# session-insight:weekly

```
/session-insight:weekly                  # 직전 완료된 month-week
/session-insight:weekly 2026-04-W5       # 명시적 month-week 키
/session-insight:weekly 2026-04-27       # 그 날짜가 속한 month-week
```

## 주차 정의 (month-week)

- W1 = 그 달 1일이 속한 주 (1일 ~ 그 주의 일요일, 월~일 구획)
- W2 ~ = 다음 월요일부터 시작
- 마지막 주는 월말 일자로 잘림 (월 경계 부분 주는 양쪽 월에 분리 파일 생성)

예: 4/29~5/3 한 주 → `2026-04-W5.md` (4/27~4/30) + `2026-05-W1.md` (5/1~5/3)

## 절차

1. 인자에서 week_key (`YYYY-MM-WN`) 결정. 입력 형태:
   - `YYYY-MM-WN` 그대로 → 그 키 사용
   - `YYYY-MM-DD` 날짜 → 그 날짜의 month-week 계산
   - 생략 → 어제 날짜의 month-week (직전 완료된 주가 됨)

   날짜 → week_key 변환:
   ```bash
   python3 - <<'PY' <YYYY-MM-DD>
   import sys
   sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/scripts")
   from datetime import date
   from _session_common import month_week_of
   d = date.fromisoformat(sys.argv[1])
   ym, wn = month_week_of(d)
   print(f"{ym}-W{wn}")
   PY
   ```

2. 그 month-week 에 속한 일자 목록을 산출 (월 경계 시 부분 일수만):
   ```bash
   python3 - <<'PY' <YYYY-MM> <WN>
   import sys
   sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/scripts")
   from _session_common import days_in_month_week
   for d in days_in_month_week(sys.argv[1], int(sys.argv[2])):
       print(d.isoformat())
   PY
   ```

3. 각 일자의 `<cwd>/.claude/session-insight/daily/<YYYY-MM-DD>.md` 를 Read 도구로 읽는다.
   - 파일 없으면 그 날 통과 세션 0으로 간주하고 스킵
   - raw `.filtered/` 는 절대 보지 않는다

4. 합산한 daily 마크다운들을 입력으로 8항목 루브릭을 채운다. 일간과 다른 점:
   - 1–7번: 일별 변화·추세·새로 등장한 패턴 명시
   - 8번: direct_inputs 군집의 일별 추세 (어느 날 처음, 며칠에 걸쳐 반복)

5. atomic write 로 `<cwd>/.claude/session-insight/weekly/<YYYY-MM-WN>.md` 저장:
   ```bash
   mkdir -p .claude/session-insight/weekly
   # Write 도구로 .tmp 작성
   mv .claude/session-insight/weekly/<KEY>.md.tmp .claude/session-insight/weekly/<KEY>.md
   ```

6. 모든 daily 가 없으면 종료 (파일 생성 안 함).

## 출력 양식

```markdown
# 주간 분석: YYYY-MM-WN (YYYY-MM-DD ~ YYYY-MM-DD)

(헤더 한 줄 — daily 합산 통계)

## 1. 토큰 부하
…(일별 추세)
…
## 8. 반복 요구사항
…
```

## 에러 처리

| 상황 | 대응 |
|------|------|
| 해당 주 daily.md 0개 | 헤더에 명시하고 파일 생성 안 함 |
| 잘못된 키 형식 | 사용법 안내 후 종료 |
