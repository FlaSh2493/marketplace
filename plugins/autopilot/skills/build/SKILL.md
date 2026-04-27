---
name: build
description: (명시적 커맨드 실행 전용) /autopilot:build 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# Build Skill

Plan 산출물(`tasks/{issue_key}/plan.md`)을 입력으로 받아 Phase 단위로 구현한다.

## 워크플로우

### 1. Plan 로드
- `tasks/{issue_key}/plan.md` 읽기
- Phase 의존성 그래프(`## Phase 의존성`) 파싱
- 실행 순서 결정

### 2. Phase별 반복

각 Phase에 대해 아래 절차를 수행한다:

#### 분기 결정
Phase 메타(`depends_on`, `scope`, `output_shape`)를 확인하여 자동 결정:
- `depends_on=[]` && `scope ≥ medium` && `output_shape=interface`
  → **서브에이전트 위임**
- 그 외 → **메인 처리**

#### 구현
- `templates/impl-prompt.md` 형식으로 구현 요청을 구성한다.
- 의존 Phase가 있는 경우, 해당 Phase의 종결 요약(`phase-summary.md`)을 포함한다.
- **메인 처리**: 현재 세션에서 직접 구현 코드를 출력한다.
- **서브에이전트 위임**: `autopilot-builder` 등 전용 에이전트에게 위임하고 결과(인터페이스/결정사항)만 회수한다.

#### 종결
- `templates/phase-summary.md` 형식으로 해당 Phase의 결과를 요약한다.
- 사용자에게 요약을 출력한다.
- 다음 Phase가 있는 경우 **"새 세션에서 시작"**을 강력히 권장하는 안내 문구를 출력한다.

### 3. 종료
- 모든 Phase 완료 후 전체 변경 파일 목록을 출력한다.
- 적용된 Phase 번호와 요약 내용을 최종 정리하여 보고한다.

## 행동 규율 (P0 - 필수)

1. **출력 형식 고정**: 코드만 출력한다. 설명은 금지하며, 변경된 파일은 반드시 전체 내용을 출력한다.
2. **범위 이탈 차단**: Plan에 명시되지 않은 리팩토링, import 정리, 시그니처 변경, 주석 추가를 엄격히 금지한다.
3. **계획 충실성**: Plan이 모호하거나 부족하면 임의로 보강하지 말고 즉시 멈추고 사용자에게 질문한다.
4. **Phase 경계 강제**: 한 번에 한 Phase만 처리한다. 여러 Phase를 묶어서 처리하지 않는다.

## 컨텍스트 위생 (P2)

- **Phase 종료 요약**: 각 Phase 완료 시 반드시 정해진 형식으로 요약하여 컨텍스트 부채를 줄인다.
- **세션 분리 권장**: Phase 전환 시 새 세션 사용을 안내하여 불필요한 시행착오 기록이 다음 단계로 넘어가지 않게 한다.
