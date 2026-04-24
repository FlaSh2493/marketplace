---
name: session-insight-analyze
description: 현재 프로젝트 세션에서 실제 사용한 스킬·플러그인별 토큰 부하를 기간별로 분석하고 최적화 가이드를 제공한다.
---

# session-insight:analyze

현재 프로젝트의 필터된 세션 로그(`.filtered.jsonl`)를 분석하여 스킬별 토큰 부하를 파악하고 최적화 방향을 제시한다.

## 옵션

```
/session-insight:analyze              # 기본: 최근 30일
/session-insight:analyze --days 7
/session-insight:analyze --from 2026-04-01 --to 2026-04-25
/session-insight:analyze --all
```

## 동작 절차

1. `CLAUDE_PLUGIN_ROOT` 환경변수로 스크립트 위치를 확인한다.
2. 아래 명령을 실행하여 통계 JSON을 얻는다:
   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analyze_tokens.py <cwd> [옵션]
   ```
   - `<cwd>`: 현재 작업 디렉토리 (사용자가 지정하지 않으면 `pwd` 결과)
   - 옵션은 사용자가 전달한 플래그를 그대로 전달
3. 통계 JSON의 `sessions` 배열에서 `total_tokens` 기준 상위 3개 세션의 `.filtered.jsonl` 파일을 읽는다.
   - 경로: `~/.claude/projects/<encoded-cwd>/<session_id>.filtered.jsonl`
   - `<encoded-cwd>`: cwd의 `/`를 `-`로 치환 (예: `/Users/madup/my/marketplace` → `-Users-madup-my-marketplace`)
4. 아래 두 가지 형식으로 결과를 출력한다.

## 출력 형식

### [타입 1] 개별 인사이트 (세션 × 대화 단위)

각 고부하 세션의 고부하 turn에 대해 다음을 명시한다:
- **몇 번째 대화(turn)**에서 발생했는지
- **스킬명** (없으면 "직접 입력")
- **input_tokens / output_tokens** 수치
- **원인 분석**: tool_results_total_chars, tool_results_count, cache_hit_rate, user_text_length를 근거로 구체적으로 서술

예시:
```
세션 abc123 — turn 3~7
  turn 3 | /autopilot:build | input: 52,000 / output: 2,100 | cache: 10%
    원인: tool_result 4개, 총 18,000자 (truncated 미적용 원본). Read 반복으로 캐시 미적중.
  turn 5 | /autopilot:check | input: 38,000 / output: 900 | cache: 0%
    원인: tool_result 6개, 총 24,000자. lint 오류 전체 출력이 잘리지 않고 전달됨.
```

### [타입 2] 전체 일괄 요약

```
## 분석 기간: YYYY-MM-DD ~ YYYY-MM-DD
## 총 세션: N개 | 총 input: X토큰 | 총 output: Y토큰

### 스킬별 토큰 사용량
| 스킬 | 호출 수 | avg input | avg output | cache hit |
|------|---------|-----------|------------|-----------|
| /autopilot:build | 12 | 42,000 | 1,800 | 30% |
| ...              |    |        |            |     |

### 고부하 원인 공통 패턴
- ...

### 최적화 제안
- ...
```

## 에러 처리

- `.filtered.jsonl` 파일이 없으면: "아직 필터된 세션 로그가 없습니다. 세션을 종료하면 자동으로 생성됩니다." 안내
- 해당 기간에 세션이 없으면: 기간 안내 후 `--all` 옵션 제안
- 스크립트 실행 실패 시: stderr 출력을 그대로 표시하고 진단 가이드 제공
