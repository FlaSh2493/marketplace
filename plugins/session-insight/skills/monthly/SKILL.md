---
name: session-insight-monthly
description: |
  지정 날짜(생략 시 지난 달) 가 속한 월의 주간 리포트(들)를 읽어 동일한 8항목
  루브릭으로 월간 리포트를 작성하고 `<cwd>/.claude/session-insight/monthly/<YYYY-MM>.md`
  로 저장한다. raw jsonl·daily/ 는 만지지 않는다 — weekly/ 만 읽는다.
---

# session-insight:monthly

```
/session-insight:monthly              # 지난 달 (직전 완료 월)
/session-insight:monthly 2026-04-27   # 그 날짜가 속한 월
```

## 절차

1. 인자에서 기준 날짜를 결정. 생략 시 **지난 달의 임의 날짜 = 1개월 전**:

   ```bash
   # macOS
   date -v-1m +%F
   # GNU
   date -d '1 month ago' +%F
   ```

2. 그 날짜가 속한 월 라벨(`YYYY-MM`)과 그 월에 걸치는 ISO 주들을 계산:

   ```bash
   # 월 라벨
   python3 -c "import datetime,sys; d=datetime.date.fromisoformat(sys.argv[1]); print(d.strftime('%Y-%m'))" <YYYY-MM-DD>

   # 그 월의 모든 ISO 주 (목요일이 그 월에 속하면 해당 월의 주로 간주)
   python3 -c "
   import datetime, sys, calendar
   y, m = map(int, sys.argv[1].split('-'))
   weeks = set()
   for day in range(1, calendar.monthrange(y, m)[1] + 1):
       d = datetime.date(y, m, day)
       thursday = d + datetime.timedelta(days=3 - d.weekday())
       if thursday.year == y and thursday.month == m:
           iy, iw, _ = d.isocalendar()
           weeks.add(f'{iy}-W{iw:02d}')
   for w in sorted(weeks): print(w)
   " <YYYY-MM>
   ```

3. `<cwd>/.claude/session-insight/weekly/<YYYY-Www>.md` 에서 그 월에 속하는 주간 리포트만 읽는다. 0개면 `/session-insight:weekly` 안내 후 종료.

4. 주간 리포트들을 입력으로 **같은 8항목 루브릭** 을 채운다. 주간과 다른 점:
   - 1–7번: **주별 추세** 와 **월 단위로 굳어진 패턴** 명시. 한 주만의 일회성 노이즈는 배제
   - 8번: 주간 8번에서 추출된 반복 요구사항의 **주별 추세** — 며칠에서 며칠로 확산, 사라짐, 신규 등장

5. `<cwd>/.claude/session-insight/monthly/<YYYY-MM>.md` 로 저장.

## 8항목 루브릭 (일간·주간과 동일 정의)

```
1. 토큰 부하       — 월간 누적·주별 추세
2. 시행착오        — 굳어진 시행착오 패턴
3. 이상 반응       — 반복적으로 발생한 이상
4. 입력 품질       — 월간 흐름
5. 도구 사용 패턴  — 굳어진 비효율
6. 최적화 제안     — 월 단위 의사결정용
7. 신규 스킬 후보  — 한 달 동안 누적된 반복으로 정당화
8. 반복 요구사항   — 주별 추세
```

## 출력 양식

```markdown
# 월간 분석: YYYY-MM

읽은 주간 리포트: N/M (M = 그 월에 걸치는 ISO 주 수)
월간 총량·핵심 변화 한 단락

## 1. 토큰 부하
…(주별 추세, 월간 누적)
…
## 8. 반복 요구사항
…
```

## 에러 처리

| 상황 | 대응 |
|------|------|
| 해당 월 주간 리포트 0개 | `/session-insight:weekly` 안내 후 종료 |
| 일부만 존재 | 헤더에 "읽은 주간 리포트: N/M" 명시 |
