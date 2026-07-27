---
name: cruise-log
description: (명시적 커맨드 실행 전용) /cruise:log 명령이 입력된 경우에만 활성화한다. cruise 하네스가 남긴 단계별 산출물(plan/build→summary/review)과 회고(result.md)를 모아 Jira 이슈에 '작업 로그' 댓글 1건으로 기록한다. 이슈 댓글 타임라인만 봐도 작업 진행과 회고(결과·잘된 점·실패·결정)를 이해할 수 있게 이력을 남긴다.
disable-model-invocation: true
---

사용자가 cruise 작업 이력을 Jira 이슈에 남기려 하면 아래 명령을 실행한다.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/log.py <KEY>
```

## 동작 규칙

- 단건만 지원. `KEY`는 `MKT-142` 형태의 **Jira 이슈 키**여야 한다.
- `~/Documents/tasks/<KEY>/` 의 cruise 산출물을 파싱해 **통합 댓글 1건**을 조합·POST한다.
- 존재하는 산출물의 섹션만 댓글에 포함된다 (없는 산출물은 건너뜀).
- commit·PR·merge는 산출물 파일이 아니다 — 스크립트가 `gh pr list`·`git log --merges`로 직접 조회해 포함한다.
- 재실행 시 마지막 로그 이후 산출물 변경이 없으면 댓글을 다시 남기지 않는다 (`no changes`).
- **산출물(plan.md 등), raw.json, meta.json을 직접 Read하지 않는다.** 스크립트가 전담한다.
- POST 전 미리 확인하려면 `--dry-run`으로 조합된 다이제스트만 출력할 수 있다.
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/log.py <KEY> --dry-run
  ```

## 결과 처리

- 성공 시 stdout 1줄: `logged MKT-142: plan, build, pr, review (4 sections)`
- 변경 없으면: `no changes  MKT-142`
- 산출물 없으면: `no artifacts  MKT-142`
- 실패 시 1줄 에러 + 상세 로그는 `~/Documents/tasks/<KEY>/.log`
- stdout 1줄만 사용자에게 보여준다.

## 대상 제약

- cruise가 브랜치명에서 Jira 키를 찾지 못해 만든 **slug 디렉토리**(예: `feat-xxx`)는 대상이 아니다.
  Jira 이슈 키 형태가 아니면 에러로 종료한다.
- 반영된 댓글은 `/cruise:plan`이 다음 실행에서 다시 fetch할 때 task.md `## Comments` 섹션에서 확인할 수 있다.
