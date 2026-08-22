---
name: cruise-log
description: (명시적 커맨드 실행 전용) /cruise:log 명령이 입력된 경우에만 활성화한다. cruise 하네스가 남긴 단계별 산출물(plan/build→summary/review)과 회고(result.md)를 모아 Jira 이슈에 '작업 로그' 댓글 1건으로 기록한다. 이슈 댓글 타임라인만 봐도 작업 진행과 회고(결과·잘된 점·실패·결정)를 이해할 수 있게 이력을 남긴다.
disable-model-invocation: true
---

사용자가 cruise 작업 이력을 Jira 이슈에 남기려 하면 아래 명령을 실행한다.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/log.py <KEY>
```

발화에 따라 플래그를 고른다.

| 사용자 발화 | 실행 |
|-------------|------|
| "로그 남겨줘", "작업내역 남겨줘" | `log.py <KEY>` — **델타**(아직 보고 안 한 완료 항목만) |
| "이전 작업까지 전부 다시", "전체 다시 로그" | `log.py <KEY> --all` — `[x]` 전량 재보고 |
| "POST 전에 미리 보여줘" | `log.py <KEY> --dry-run` |

## 동작 규칙

- 단건만 지원. `KEY`는 `MKT-142` 형태의 **Jira 이슈 키**여야 한다.
- `{task_dir}/` 의 cruise 산출물을 파싱해 **작업내역 댓글 1건**을 조합·POST한다.
  (`{task_dir}` 는 `config.json` 의 `settings.tasks_root` 기준 — 리터럴 경로를 쓰지 않는다.)
- 존재하는 산출물의 섹션만 댓글에 포함된다 (없는 산출물은 건너뜀).
- commit·PR·merge는 산출물 파일이 아니다 — 스크립트가 `gh pr list`·`git log --merges`로 직접 조회해 포함한다.
- **`완료한 작업`은 델타다.** plan.md는 사이클을 거듭하며 누적되는 산출물이라 `[x]` 전량을 매번 실으면
  이미 보고한 항목이 반복된다. 아직 보고한 적 없는 항목만 싣는다.
  - 매칭 키는 R-ID가 아니라 **요구사항 문장의 해시**다. plan을 전면 재작성해 R 번호가 1부터 다시 붙어도
    같은 문장은 다시 실리지 않고, 문장을 개정하면 해시가 달라져 다시 실린다.
  - 보고 이력은 `{task_dir}/.jsync-log.json` 의 `logged: [{"rid","hash"}, …]` 에 쌓인다
    (`last_hash`·`last_posted_at`은 그대로 유지). `logged` 키가 없는 기존 상태 파일은 최초 1회 전량 보고 후 시드한다.
  - 상태 갱신은 **POST 성공 뒤에만** 일어난다 — `--dry-run`과 실패는 상태를 건드리지 않는다.
- **새로 완료된 항목이 0건이면 POST하지 않는다** (`no changes`). `해결한 문제`·`상태`만 남은 껍데기 댓글을 막는다.
- `--all` 이면 델타와 `last_hash` 중복 방지를 모두 우회해 `[x]` 전량을 다시 보고하고, 전체를 상태에 재시드한다
  (다음 호출부터는 다시 델타).
- 재실행 시 마지막 로그 이후 산출물 변경이 없으면 댓글을 다시 남기지 않는다 (`no changes`).
- **산출물(plan.md 등), raw.json, meta.json을 직접 Read하지 않는다.** 스크립트가 전담한다.
- 댓글은 **작업내역 4블록**으로 조합된다 (스킬·산출물 이름을 노출하지 않는다):

  | 블록 | 출처 |
  |------|------|
  | `해결한 문제` | `task.md` `## 배경` (없으면 `summary.md` `## 개요`) |
  | `완료한 작업` | `plan.md` `## 요구사항` 의 `[x]` 항목 중 **아직 보고 안 한 것만** (철회 제외, R-ID 접두 제거) |
  | `미해결` | 같은 섹션의 `[ ]` **전량** (철회 제외) — 미체크는 사건이 아니라 현재 상태라 매번 스냅샷으로 싣는다 |
  | `상태` | 브랜치 · 검사 결과 · PR · 리뷰 반영 횟수 |

  파일 변경 내역·통계·커밋 목록·교훈(결정·잘된 점·어려웠던 점)은 담지 않는다.
  변경 상세는 PR diff, 교훈은 로컬 `result.md` 가 진실 원천이다.
- POST 전 미리 확인하려면 `--dry-run`으로 조합된 다이제스트만 출력할 수 있다.
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/log.py <KEY> --dry-run
  ```

## 결과 처리

- 성공 시 stdout 1줄: `logged MKT-142: 문제, 작업, 미해결, 상태 (4 sections)  https://…/browse/MKT-142`
  (이슈 URL을 함께 낸다 — 사용자가 바로 확인할 수 있도록)
- 변경 없거나 새로 완료된 항목이 없으면: `no changes  MKT-142`
- 산출물 없으면: `no artifacts  MKT-142`
- 실패 시 1줄 에러 + 상세 로그는 `{task_dir}/.log`
- stdout 1줄만 사용자에게 보여준다.

## 대상 제약

- cruise가 브랜치명에서 Jira 키를 찾지 못해 만든 **slug 디렉토리**(예: `feat-xxx`)는 대상이 아니다.
  Jira 이슈 키 형태가 아니면 에러로 종료한다.
- 반영된 댓글은 `/cruise:plan`이 다음 실행에서 다시 fetch할 때 task.md `## Comments` 섹션에서 확인할 수 있다.
