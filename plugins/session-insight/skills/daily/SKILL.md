---
name: session-insight-daily
description: |
  지정 날짜(생략 시 어제) 의 `.filtered/<date>/*.jsonl` 세션을 8항목 루브릭으로
  분석하여 `<cwd>/.claude/session-insight/daily/<YYYY-MM-DD>.md` 로 저장한다.
  collect_filtered.py 가 인덱스+jsonl → 구조화 markdown 으로 변환해 주면, 에이전트가
  그 markdown 을 입력으로 8항목 루브릭을 채운다. 다른 tier markdown 에 의존하지 않는다.
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

# session-insight:daily

```
/session-insight:daily                 # 어제
/session-insight:daily 2026-04-27      # 그 날짜
```

## 절차

1. 날짜 결정. 인자 생략 시 어제:
   ```bash
   date -v-1d +%F            # macOS
   date -d 'yesterday' +%F   # GNU
   ```

2. 일간 raw 데이터 markdown 생성:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/collect_filtered.py" "$(pwd)" --tier daily --date <YYYY-MM-DD>
   ```

3. 출력 markdown 을 읽고 8항목 루브릭을 채운다. 스크립트가 제공하는 섹션:
   - 헤더 (필터 통과율·총 토큰·점수 분포·드롭 시그널 합산)
   - 드롭된 세션 메타 표 (양적 시그널)
   - 세션 목록 표
   - 스킬별 집계 표
   - 고부하 turn 섹션 (세션별 다지표 union Top 5, user_text 앞 300자)
   - 직접입력 목록

4. 본문 작성 후, 마지막에 "대표 세션 ID 3개" 섹션을 추가한다 (input/output/edits 등 가장 흥미로운 세션). 상위 tier 가 드릴다운할 수 있게.

5. atomic write — 임시 파일 `daily/<YYYY-MM-DD>.md.tmp` 에 작성 후 `mv` 로 rename:
   ```bash
   mkdir -p .claude/session-insight/daily
   # Write 도구로 .tmp 작성
   mv .claude/session-insight/daily/<YYYY-MM-DD>.md.tmp .claude/session-insight/daily/<YYYY-MM-DD>.md
   ```

6. "필터 통과 세션 0" 또는 "인덱스 항목 없음" 이면 종료 (파일 생성 안 함).

## 출력 양식

```markdown
# 일간 분석: YYYY-MM-DD

(헤더 한 줄 — 필터 통과율·총 토큰)

## 1. 토큰 부하
…
## 8. 반복 요구사항
…

## 대표 세션 ID

- `<short-id>` — 한 줄 사유
- `<short-id>` — 한 줄 사유
- `<short-id>` — 한 줄 사유
```

## 에러 처리

| 상황 | 대응 |
|------|------|
| 인덱스 없음 (훅 미실행) | 스크립트 안내 메시지 그대로 출력 후 종료 |
| 해당 날짜 통과 세션 0 | 알리고 종료 (파일 생성 안 함) |
| 잘못된 날짜 형식 | 사용법 안내 후 종료 |
| 스크립트 실패 | stderr 표시 + `CLAUDE_PLUGIN_ROOT` 확인 안내 |
