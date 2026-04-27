---
name: session-insight-monthly
description: |
  지정 날짜(생략 시 지난 달) 가 속한 월의 .filtered/ 세션을 직접 읽어 동일한 8항목
  루브릭으로 월간 리포트를 작성하고 `<cwd>/.claude/session-insight/monthly/<YYYY-MM>.md`
  로 저장한다. **weekly/ 마크다운에 의존하지 않는다 — 인덱스에서 직접 한 달치 세션을 합산한다.**
---

# session-insight:monthly

```
/session-insight:monthly              # 지난 달 (직전 완료 월)
/session-insight:monthly 2026-04-27   # 그 날짜가 속한 월
```

## 절차

1. 인자에서 기준 날짜를 결정. 생략 시 **지난 달의 임의 날짜 = 1개월 전**:
   ```bash
   date -v-1m +%F             # macOS
   date -d '1 month ago' +%F  # GNU
   ```

2. 그 날짜가 속한 월 라벨(`YYYY-MM`) 을 계산:
   ```bash
   python3 -c "import datetime,sys; d=datetime.date.fromisoformat(sys.argv[1]); print(d.strftime('%Y-%m'))" <YYYY-MM-DD>
   ```

3. 월간 raw 데이터 markdown 생성 (인덱스에서 그 월에 속하는 세션 직접 합산):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/collect_filtered.py" "$(pwd)" --tier monthly --month <YYYY-MM>
   ```

4. 출력 markdown 을 입력으로 **같은 8항목 루브릭** 을 채운다. 주간과 다른 점:
   - 1–7번: **주별 추세** 와 **월 단위로 굳어진 패턴** 명시. 한 주만의 일회성 노이즈는 배제
   - 8번: direct_inputs 의 **주별 추세** — 며칠에서 며칠로 확산, 사라짐, 신규 등장

5. `<cwd>/.claude/session-insight/monthly/<YYYY-MM>.md` 로 저장. 같은 파일 있으면 **덮어쓰기**.

## 8항목 루브릭

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

(헤더 한 줄 — 필터 통과율·총 토큰·드롭 시그널)

## 1. 토큰 부하
…(주별 추세, 월간 누적)
…
## 8. 반복 요구사항
…
```

## 에러 처리

| 상황 | 대응 |
|------|------|
| 인덱스 없음 (훅 미실행) | 스크립트 안내 메시지 출력 후 종료 |
| 해당 월 통과 세션 0 | 헤더에 명시하고 가능한 항목만 채움 |
