---
name: brain-sync-status
description: (명시적 커맨드 실행 전용) /brain-sync:status 명령이 입력된 경우에만 활성화한다. cruise task 저장소와 Brain vault의 동기화 상태를 dry-run으로 보고한다. 쓰기·LLM 없음.
disable-model-invocation: true
---

# Brain Sync — Status (dry-run)

cruise task 저장소를 스캔해 **무엇이 동기화 대상인지**만 보고한다. **노드를 쓰지 않고, LLM 종합도 하지 않는다.**

> **금지:** 어떤 파일도 쓰지 않는다. extract/sync 를 호출하지 않는다. 보고 후 [STOP].

---

## STEP 1 — 인벤토리 스캔

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scan.py
```

(Jira 키 task만 보려면 `--jira-only` 추가.)

출력 JSON: `tasks_root, brain_root, total, counts{new,changed,unchanged,no_result}, tasks[]`.

## STEP 2 — 매니페스트 요약

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/manifest.py --show
```

출력: `brain_root, tasks_synced, features, tasks_assigned, tasks_unassigned, technologies,
counts{features,work-items,patterns,...}, meta`.

## STEP 3 — 보고

다음을 표로 간결히 보고한다:
- 총 task 수 / new / changed / unchanged / no_result
- 다음 `/brain-sync:sync` 실행 시 처리될 대상 = **new + changed** 개수
- 현재 vault 노드 카운트(features 포함), 마지막 동기화 시각(`meta.last_sync`)
- **feature 수 / assigned·unassigned task 수** — feature는 result.md 권위값 있는 task만 묶임
- `unassigned` task 목록(있으면) — `/cruise:result` 를 돌리면 feature가 정확히 채워짐을 안내
- `no_result` task 목록(있으면) — work-item 만 생성되고 파생·feature 노드는 생략됨을 안내

표 출력 후 [STOP].
