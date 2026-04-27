---
name: session-insight-weekly
description: |
  지정 날짜(생략 시 지난 주) 가 속한 ISO 주의 일간 리포트를 읽어 동일한 8항목
  루브릭으로 주간 리포트를 작성하고 `<cwd>/.claude/session-insight/weekly/<YYYY-Www>.md`
  로 저장한다. raw jsonl 은 만지지 않는다 — daily/ 만 읽는다.
---

# session-insight:weekly

```
/session-insight:weekly              # 지난 주 (직전 완료 주)
/session-insight:weekly 2026-04-27   # 그 날짜가 속한 ISO 주
```

## 절차

1. 인자에서 기준 날짜를 결정. 생략 시 **지난 주의 임의 날짜 = 7일 전**:

   ```bash
   # macOS
   date -v-7d +%F
   # GNU
   date -d '7 days ago' +%F
   ```

2. 그 날짜가 속한 ISO 주 라벨과 7일 범위를 계산:

   ```bash
   # ISO 주 (예: 2026-W17)
   python3 -c "import datetime,sys; d=datetime.date.fromisoformat(sys.argv[1]); y,w,_=d.isocalendar(); print(f'{y}-W{w:02d}')" <YYYY-MM-DD>

   # 그 주의 월요일·일요일
   python3 -c "import datetime,sys; d=datetime.date.fromisoformat(sys.argv[1]); mon=d-datetime.timedelta(days=d.weekday()); print(mon, mon+datetime.timedelta(days=6))" <YYYY-MM-DD>
   ```

3. `<cwd>/.claude/session-insight/daily/<YYYY-MM-DD>.md` 에서 그 주 7일치 중 존재하는 일간 리포트만 읽는다. 0개면 "먼저 `/session-insight:daily` 를 돌리세요" 안내 후 종료.

4. 일간 리포트들을 입력으로 **같은 8항목 루브릭** 을 채운다. 일간과 다른 점:
   - 1–7번: **일별 변화·추세·새로 등장한 패턴** 명시
   - 8번: 일간 direct_inputs 군집의 **일별 추세** (어느 날 처음, 며칠에 걸쳐 반복)

5. `<cwd>/.claude/session-insight/weekly/<YYYY-Www>.md` 로 저장.

## 8항목 루브릭 (일간과 동일 정의)

```
1. 토큰 부하       — 가장 무거운 스킬 Top3 + 추정 원인, cache hit 낮은 스킬
2. 시행착오        — thinking 기반 번복·재고
3. 이상 반응       — tool 에러·반복 호출
4. 입력 품질       — 모호한 user_text → 긴 작업
5. 도구 사용 패턴  — 비효율 시퀀스
6. 최적화 제안     — 근거 인용 필수
7. 신규 스킬 후보  — 근거 인용 필수
8. 반복 요구사항   — 일별 추세
```

각 항목에서 단순 합산 금지 — **일별 변화**·추세·신규 패턴 강조.

## 출력 양식

```markdown
# 주간 분석: YYYY-Www (YYYY-MM-DD ~ YYYY-MM-DD)

읽은 일간 리포트: N/7
주간 총량 한 줄 요약

## 1. 토큰 부하
…(일별 추세)
…
## 8. 반복 요구사항
…
```

## 에러 처리

| 상황 | 대응 |
|------|------|
| 해당 주 일간 리포트 0개 | `/session-insight:daily` 안내 후 종료 |
| 일부만 존재 | 헤더에 "읽은 일간 리포트: N/7" 명시 |
