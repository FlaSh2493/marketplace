---
name: work-mode-selector
description: "이슈의 규모와 복잡도에 따라 최적의 작업 모드를 결정합니다 (Single Session, Sub-agent, Claude Team)"
---

## 판단 기준
1. **Single Session**: 1개 이슈, 3개 이하의 파일 수정, 간단한 리팩토링이나 버그 수정
2. **Sub-agent**: 2~3개 이슈, 연관된 5~10개 파일 수정, 새로운 기능 추가나 모듈 분리
3. **Claude Team**: 4개 이상의 이슈, 10개 이상의 파일 수정, 대규모 아키텍처 변경

## 결과
- state.json의 `mode` 필드에 기록
- 사용자에게 추천 모드 제시
