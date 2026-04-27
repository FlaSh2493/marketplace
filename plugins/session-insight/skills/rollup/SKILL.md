---
name: session-insight-rollup
description: |
  --from / --to 범위에 대해 일/주/월 분석을 한 번의 LLM 호출로 통합 출력한다.
  collect_filtered.py 가 범위 내 .filtered/ 세션을 한 묶음 markdown 으로 변환해 주면,
  에이전트는 한 번에 일별 요약·주간 패턴·월간 트렌드 세 섹션을 작성하여
  `<cwd>/.claude/session-insight/rollup/<from>_<to>.md` 로 저장한다.
  daily/weekly/monthly 호출과 독립적으로 동작한다 (다른 tier markdown 미참조).
---

# session-insight:rollup

```
/session-insight:rollup --from 2026-04-01 --to 2026-04-27
/session-insight:rollup --from 2026-04-21 --to 2026-04-27   # 사실상 주간 한 번에
```

## 절차

1. `--from`, `--to` 인자 검증 (둘 다 필수, A > B 면 swap).

2. 통합 raw 데이터 markdown 생성:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/collect_filtered.py" "$(pwd)" --tier rollup --from <FROM> --to <TO>
   ```

3. 출력 markdown 을 입력으로 **세 섹션을 동시에** 작성:
   - **일별 요약**: 범위 내 각 날짜별 8항목 루브릭 핵심 (3-4줄/날짜)
   - **주간 패턴**: 범위에 포함되는 ISO 주별 추세·신규 패턴
   - **월간 트렌드**: 월 단위 누적·굳어진 패턴 (범위가 한 달 미만이면 "범위 짧음" 명시)

4. `<cwd>/.claude/session-insight/rollup/<FROM>_<TO>.md` 로 저장. 같은 파일 있으면 **덮어쓰기**.

## 출력 양식

```markdown
# 통합 rollup: YYYY-MM-DD ~ YYYY-MM-DD

(헤더 한 줄 — 필터 통과율·총 토큰·점수 분포)

## 일별 요약

### YYYY-MM-DD
- 토큰 부하: …
- 시행착오: …
- 도구 패턴: …
- 반복 요구사항: …

(반복)

## 주간 패턴 (ISO 주별)

### YYYY-Www
- 일별 변화: …
- 신규 패턴: …
- 최적화 제안: …

(반복)

## 월간 트렌드

- 굳어진 패턴: …
- 주별 추세: …
- 신규 스킬 후보: …
- 월 단위 의사결정 제안: …
```

## 8항목 루브릭 적용 원칙

세 섹션 모두 동일한 8항목 (토큰 부하 / 시행착오 / 이상 반응 / 입력 품질 / 도구 사용 / 최적화 / 신규 스킬 후보 / 반복 요구사항) 을 시간 단위에 맞게 압축. 일별은 핵심만, 주간은 변화·추세, 월간은 굳어진 패턴.

## 에러 처리

| 상황 | 대응 |
|------|------|
| 인덱스 없음 (훅 미실행) | 스크립트 안내 메시지 출력 후 종료 |
| 범위 내 통과 세션 0 | 헤더에 명시하고 드롭 메타 시그널만으로 가능한 정량 분석만 |
| `--from > --to` | 자동 swap 후 정상 처리 |
