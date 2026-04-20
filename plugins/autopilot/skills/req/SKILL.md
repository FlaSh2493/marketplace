---
name: autopilot-req
description: 현재 대화에서 추가 요구사항을 추출하여 이슈 문서에 기록한다. 이슈키를 지정하거나 생략하면 .autopilot에서 자동 감지한다.
---

# Requirement Record

**실행 주체: Main Session**

## 사용법
```
/autopilot:req [이슈키]
```
- 이슈키 생략 시: `.autopilot`에서 이슈 목록 자동 감지

---

## STEP 0.5: 프로젝트 커스텀 지침 참조

[_shared/CUSTOM_INSTRUCTIONS.md](../_shared/CUSTOM_INSTRUCTIONS.md)에 따라 다음 명령을 실행하여 프로젝트 지침을 확인한다.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_custom_instructions.py req
```

- **필수 참조**: 로드된 지침을 **반드시 준수**하며, 표준 절차를 왜곡하지 않고 행동한다.

---

## 실행 절차

STEP 0: 이슈키 확보
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_worktree.py
  ```
  - `status == "ok"` → `data`의 `issues`, `worktree_path` 보관.
  - 인자로 이슈키가 주어지면 해당 이슈키 사용.
  - 이슈키가 없고 `issues`가 비어있으면: "기록할 이슈가 없습니다." 출력 후 [STOP].
  - 이슈키가 없고 `issues`가 여러 개면: 대화 맥락 분석하여 판단 또는 AskUserQuestion으로 선택.


STEP 1: 요구사항 추출
  현재 대화 전체를 검토하여 아래 기준으로 추가 요구사항 후보 추출:
  - 사용자가 새로 언급한 기능/동작 조건
  - 기존 명세에 없는 제약·예외 처리
  - 구현 중 합의된 변경사항
  이미 이슈 명세(`## 설명`)에 있는 내용은 제외

  추출 결과가 없으면: "추가 요구사항이 없습니다." 출력 후 [STOP]

STEP 2: 사용자 확인
  추출한 항목을 보여주고 확인:
  ```
  아래 내용을 [{이슈키}] 추가 요구사항으로 기록할까요?

  - {항목1}
  - {항목2}
  ...

  (수정할 내용이 있으면 말씀해주세요. 기록하려면 'ok')
  ```
  [GATE] AskUserQuestion
  사용자가 수정 요청 시: 반영 후 재확인
  'ok' 또는 확인 응답 시: STEP 3 진행

STEP 3: API 목록 추출
  이슈 설명과 추가 요구사항에서 도메인 키워드 추출 → 코드베이스에서 관련 API 호출 탐색:
  ```
  cd {worktree_path} && rg -n "(fetch|axios|apiClient|useMutation|useQuery|useInfiniteQuery)\(" --type ts -l | head -20
  ```
  키워드와 관련된 파일만 Read → 실제 호출되는 엔드포인트 경로·메서드 수집.
  추출 결과를 STEP 4에서 문서에 기록한다.

STEP 4: 이슈 문서에 기록
  ```bash
  python3 scripts/load_issue.py {이슈키} → md_path 확보
  python3 scripts/extract_requirements.py upsert-doc {md_path} --req-items {항목들} --api-rows {API 목록 표 데이터}
  ```
  실패 시 경고 출력 후 [STOP].


  완료 출력:
  ```
  [{이슈키}] 추가 요구사항 {N}건 기록 완료 / 사용 API {M}건 기록 완료
  ```

[TERMINATE]
