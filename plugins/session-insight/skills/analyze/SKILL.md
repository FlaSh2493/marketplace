---
name: session-insight-analyze
description: |
  현재 프로젝트 세션 로그를 분석하여 다음을 제공한다:
  - 스킬·플러그인별 토큰 부하 및 개선방향 (기간별)
  - thinking 블록에서 실패 시도·시행착오·자주 막힌 지점 추출
  - 유저 입력 패턴과 에이전트 이상 반응의 상관관계
  - 최적화 가이드 및 신규 스킬 후보 추천
---

# session-insight:analyze

분석 대상:

- `.filtered.jsonl` — 토큰 수치, 유저 입력 패턴, 이상 반응 감지
- 원본 `.jsonl` — thinking 블록 기반 시행착오 추출

## 옵션

```
/session-insight:analyze              # 기본: 최근 30일
/session-insight:analyze --days 7
/session-insight:analyze --from 2026-04-01 --to 2026-04-25
/session-insight:analyze --all
```

## 동작 절차

1. 스크립트를 실행한다:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/analyze_insights.py" "$(pwd)" [옵션]
   ```

   옵션은 사용자가 전달한 플래그를 그대로 전달한다.

2. 스크립트의 stdout 출력을 그대로 사용자에게 표시한다. 파일을 직접 읽지 않는다.

## 에러 처리

| 상황                     | 대응                                                       |
| ------------------------ | ---------------------------------------------------------- |
| `.filtered.jsonl` 없음   | 스크립트 출력 그대로 표시                                  |
| 해당 기간 세션 없음      | 스크립트 출력 후 `--all` 옵션 제안                         |
| 스크립트 실패 (exit ≠ 0) | stderr 출력 표시 + `CLAUDE_PLUGIN_ROOT` 환경변수 확인 안내 |
