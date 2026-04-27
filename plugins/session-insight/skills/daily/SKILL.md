---
name: session-insight-daily
description: |
  지정 날짜(또는 --from/--to 범위, 생략 시 어제) 의 모든 세션을 8항목 루브릭으로
  분석하여 `<cwd>/.claude/session-insight/daily/<YYYY-MM-DD>.md` 로 저장한다.
  collect_daily.py 가 raw jsonl → 구조화 markdown 으로 변환해 주면, 에이전트가
  그 markdown 을 입력으로 8항목 루브릭을 채운다.
---

# session-insight:daily

```
/session-insight:daily                                       # 어제
/session-insight:daily 2026-04-27                            # 그 날짜
/session-insight:daily --from 2026-04-20 --to 2026-04-24     # 범위 (각 일자별 독립 리포트)
```

## 절차

1. 인자에서 처리할 **날짜 목록** 결정:
   - `--from A --to B` 가 주어지면 A부터 B까지(양끝 포함) 매일을 목록으로
   - 단일 날짜가 주어지면 그 날짜 하나
   - 둘 다 생략이면 **어제** 하나:
     ```bash
     # macOS (BSD date)
     date -v-1d +%F
     # 또는 GNU date
     date -d 'yesterday' +%F
     ```

   범위 펼치기 헬퍼:
   ```bash
   python3 -c "
   import datetime, sys
   a = datetime.date.fromisoformat(sys.argv[1])
   b = datetime.date.fromisoformat(sys.argv[2])
   step = datetime.timedelta(days=1 if a <= b else -1)
   d = a
   while True:
       print(d)
       if d == b: break
       d += step
   " <FROM> <TO>
   ```

2. **목록의 각 날짜에 대해 독립적으로** 다음 단계를 반복한다 (각 날짜마다 별개 리포트 파일 생성):

   1. 일간 raw 데이터 markdown 생성:
      ```bash
      python3 "${CLAUDE_PLUGIN_ROOT}/scripts/collect_daily.py" "$(pwd)" <YYYY-MM-DD>
      ```

   2. 출력 markdown 을 **읽고 판단**. 스크립트 제공 섹션:
      - 헤더 (세션 수·총 토큰)
      - 세션 목록 표
      - 스킬별 집계 표
      - 고부하 turn 섹션 (세션별 다지표 union Top 5, user_text 앞 300자 + thinking 본문 전체)
      - 직접입력 목록

   3. **8항목 루브릭** 을 채운다. turn/세션 인용을 근거로 첨부. 관찰 없으면 "해당 없음" 명시.

   4. `<cwd>/.claude/session-insight/daily/<YYYY-MM-DD>.md` 로 저장. 디렉토리 없으면 생성. 같은 파일이 이미 있으면 **덮어쓰기**.

   5. 그 날짜에 세션이 없다는 스크립트 출력이 보이면 그 날짜는 스킵하고 다음 날짜로 진행.

3. 모든 날짜 처리 끝나면 사용자에게 생성·갱신된 파일 목록을 짧게 보고.

## 8항목 루브릭

```
1. 토큰 부하       — 가장 무거운 스킬 Top3 + 추정 원인, cache hit 낮은 스킬
2. 시행착오        — thinking 기반 번복·재고
3. 이상 반응       — tool 에러·반복 호출·비정상 짧은 출력
4. 입력 품질       — 모호한 user_text → 긴 작업, 좋은 입력 사례
5. 도구 사용 패턴  — 비효율 시퀀스, tool_chars 큰 turn 정체
6. 최적화 제안     — 근거 인용 필수
7. 신규 스킬 후보  — 근거 인용 필수
8. 반복 요구사항   — direct_inputs 군집 (의도별 묶고 빈도·대표 인용)
```

## 출력 양식

```markdown
# 일간 분석: YYYY-MM-DD

(헤더 한 줄 — 세션 수·총 토큰)

## 1. 토큰 부하
…
## 8. 반복 요구사항
…
```

## 에러 처리

| 상황 | 대응 |
|------|------|
| 해당 날짜 세션 없음 | 단일 날짜면 알리고 종료. 범위 처리 중이면 그 날짜만 스킵하고 계속 |
| `--from > --to` 또는 잘못된 날짜 | 사용법 안내 후 종료 |
| 스크립트 실패 | stderr 표시 + `CLAUDE_PLUGIN_ROOT` 확인 안내 |
