---
name: session-insight-weekly
description: |
  지정 날짜(생략 시 지난 주) 가 속한 ISO 주의 .filtered/ 세션을 직접 읽어 동일한 8항목
  루브릭으로 주간 리포트를 작성하고 `<cwd>/.claude/session-insight/weekly/<YYYY-Www>.md`
  로 저장한다. **daily/ 마크다운에 의존하지 않는다 — 인덱스에서 직접 7일치 세션을 합산한다.**
---

# session-insight:weekly

```
/session-insight:weekly              # 지난 주 (직전 완료 주)
/session-insight:weekly 2026-04-27   # 그 날짜가 속한 ISO 주
```

## 절차

1. 인자에서 기준 날짜를 결정. 생략 시 **지난 주의 임의 날짜 = 7일 전**:
   ```bash
   date -v-7d +%F            # macOS
   date -d '7 days ago' +%F  # GNU
   ```

2. 그 날짜가 속한 ISO 주 라벨을 계산:
   ```bash
   python3 -c "import datetime,sys; d=datetime.date.fromisoformat(sys.argv[1]); y,w,_=d.isocalendar(); print(f'{y}-W{w:02d}')" <YYYY-MM-DD>
   ```

3. 주간 raw 데이터 markdown 생성 (인덱스에서 그 주에 속하는 세션 직접 합산):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/collect_filtered.py" "$(pwd)" --tier weekly --week <YYYY-Www>
   ```

4. 출력 markdown 을 입력으로 **같은 8항목 루브릭** 을 채운다. 일간과 다른 점:
   - 1–7번: **일별 변화·추세·새로 등장한 패턴** 명시
   - 8번: direct_inputs 군집의 **일별 추세** (어느 날 처음, 며칠에 걸쳐 반복)

5. `<cwd>/.claude/session-insight/weekly/<YYYY-Www>.md` 로 저장. 같은 파일 있으면 **덮어쓰기**.

## 8항목 루브릭 (일간과 동일 정의)

```
1. 토큰 부하       — 가장 무거운 스킬 Top3 + 추정 원인, cache hit 낮은 스킬
2. 시행착오        — error_retry/abort 추세
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

(헤더 한 줄 — 필터 통과율·총 토큰·드롭 시그널)

## 1. 토큰 부하
…(일별 추세)
…
## 8. 반복 요구사항
…
```

## 에러 처리

| 상황 | 대응 |
|------|------|
| 인덱스 없음 (훅 미실행) | 스크립트 안내 메시지 출력 후 종료 |
| 해당 주 통과 세션 0 | 헤더에 명시하고 가능한 항목만 채움. 드롭 메타가 있으면 정량 시그널만 활용 |
