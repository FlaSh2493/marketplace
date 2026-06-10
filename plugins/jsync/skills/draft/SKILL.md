---
name: jsync-draft
description: 요구사항을 받아 task.md의 description 본문을 작성/보강합니다. 이슈 키를 주면 기존 task.md의 description을 새 요구사항과 지능적으로 병합하고, 키가 없으면 새 초안(DRAFT-*)을 만듭니다. "요구사항 정리해줘", "이 내용 task.md에 반영해줘", "초안 만들어줘" 같은 요청에 실행됩니다.
---

사용자가 입력한 요구사항(산문)을 구조화된 description 본문으로 작성·병합해 task.md에 반영한다.
**작문·병합은 에이전트(너)가 하고**, frontmatter·read-only 섹션 보존과 파일 I/O는 helper 스크립트가 처리한다.

모든 명령은 아래 형태로 실행한다.

```
cd <plugin-root>/scripts && python draft.py <SUBCOMMAND> ...
```

## 모드 판별

- 입력에 이슈 키(`MKT-142` 형태)가 있으면 → **보강 모드** (기존 task.md의 description 갱신)
- 키가 없으면 → **새 초안 모드** (`DRAFT-*` task.md 생성)

## 보강 모드 (키 있음)

1. 현재 description 본문만 읽는다.
   ```
   python draft.py extract <KEY>
   ```
   - 출력이 비어 있고 `<KEY>/task.md`가 없으면, 사용자에게 `/jsync:fetch <KEY>`를 먼저 실행하라고 안내하고 중단한다.
2. **extract로 받은 기존 본문 + 사용자 요구사항을 지능적으로 병합**해 새 description 본문을 작성한다.
   - 전체 덮어쓰기 금지. 기존 구조와 내용을 보존하면서 추가·갱신한다.
   - **중복 추가 금지**: 이미 있는 항목은 다시 넣지 말고 기존 항목을 갱신한다 (여러 번 실행해도 누적되지 않게).
3. 작성한 본문을 stdin으로 splice 한다.
   ```
   python draft.py splice <KEY>   # 새 본문을 stdin(heredoc 등)으로 전달
   ```
4. frontmatter, `## Subtasks/Comments/Worklog/Attachments`, `## New Comment`는 **절대 직접 수정하지 않는다.** splice가 바이트 그대로 보존한다.

## 새 초안 모드 (키 없음)

1. 요구사항에서 한 줄 summary를 도출한다.
2. 초안을 스캐폴딩한다 (본문은 stdin으로 함께 넣거나, 이후 splice로 채운다).
   ```
   python draft.py scaffold "<summary>" [--issuetype Task]   # 본문 stdin 선택
   ```
   - 저장 위치는 `~/Documents/tasks/DRAFT-<slug>/task.md`. 출력된 디렉토리명을 기억한다.
3. (scaffold에 본문을 안 넣었다면) description 본문을 작성해 splice 한다.
   ```
   python draft.py splice DRAFT-<slug>
   ```

## 이미지

- **파일 경로로 받은 경우에만** attachments/에 저장한다.
  ```
  python draft.py addimage <KEY|DRAFT-x> <이미지경로>
  ```
  반환된 상대경로(`attachments/...`)를 description 본문에 `![설명](attachments/...)`로 삽입한다 (splice 입력에 포함).
- **인라인으로 붙여넣은 이미지는 파일로 저장할 수 없다** (픽셀만 보일 뿐 파일 바이트가 없음). 이 경우 이미지 내용을 글로 풀어 description에 반영하거나, 사용자에게 파일 경로 제공을 요청한다.
- 저장된 이미지의 실제 Jira 업로드는 이후 `/jsync:update <KEY>`가 처리한다.

## 결과 처리

- 스크립트 stdout(1줄 요약)만 사용자에게 보여준다.
- **raw.json, meta.json은 절대 Read하지 않는다.** 에이전트는 description 본문 텍스트만 주고받는다.
- Jira 반영은 이후 `/jsync:update <KEY>`.
- 새 초안(`DRAFT-*`)을 Jira 새 이슈로 생성하는 것은 update가 아니라 별도 기능이다. update는 raw.json을 요구하므로 `DRAFT-*`에 직접 실행하면 안 된다.
