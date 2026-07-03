# brain-sync 계약 고정 (Contract Target)

brain-sync 가 **읽는 입력 계약**과 **쓰는 출력 스키마**를 고정한다.

```yaml
reads:   cruise contract_version 2     # plugins/cruise/CONTRACT.md
writes:  vault_schema_version 2
brain_sync_version 0.2.0
```

## 입력 (cruise 산출물)

- 위치: `~/Documents/tasks/<KEY>/` (env `CRUISE_TASKS_ROOT` 로 override)
- 스키마: `plugins/cruise/CONTRACT.md` (contract_version 2). brain-sync 는 cruise 코드를
  import하지 않고 이 계약만 보고 파일을 읽는다.
- source_hash 기여 파일: `task.md`, `result.md`, `summary.md`, `pr.md`, `commit.md`
  (이 중 하나라도 바뀌면 해당 task 재동기화).
- **feature 멤버십**은 result.md의 권위 필드(`feature`/`worktree`/`issue_keys`)에서만 읽는다.
  `feature` 가 비었거나 result.md 가 없으면 **unassigned** (휴리스틱 추측 안 함 — 정확성 우선).
- cruise contract_version 가 2 미만이면(구버전 result.md) feature 필드가 없어 모두 unassigned 로 처리.

## 출력 (Brain vault)

- 위치: `~/Documents/brain/` (env `BRAIN_ROOT` 로 override)
- 레이아웃:
  ```
  ~/Documents/brain/
  ├── features/     <feature-slug>.md         단위 기능 허브 (권위 feature 있는 task만)
  ├── work-items/   <KEY>.md                  task 노드 (feature 자식 또는 unassigned)
  ├── patterns/     <kebab>.md                재사용 기법 (공유 가능)
  ├── decisions/    <KEY>-<kebab>.md          의사결정 (task 국소)
  ├── incidents/    <KEY>-<kebab>.md          사고 (task 국소)
  ├── technologies/ <slug>.md                 기술 (여러 task 공유 머지 노드)
  ├── _manifest.json                          tasks/features/tech_index 멱등 원장
  └── _meta.json                              버전·last_sync·counts
  ```
- 노드 공통 frontmatter: `id, type, title, slug, status(active|archived), source_keys[],
  created, updated, brain_sync_version, cruise_contract_version, content_hash, links[], tags[]`.
- 엣지: 본문 `[[folder/slug]]` wikilink + frontmatter `links[]` 미러.

## 불변식 (멱등성)

- **work-item id = `work-items/<KEY>`** — KEY 유일 → 재실행 시 항상 동일 파일.
- **feature = 권위 멤버십 노드** — `source_keys`(=멤버 KEY)를 **교체**(union 아님)로 관리.
  멤버는 result.md.feature 가 실제 바뀔 때만 이동. task_count·worktree_count 는 멤버에서 집계.
- **technology = 공유 머지 노드** — `source_keys` 에 여러 KEY 누적(union), `## 사용 이력` 에 KEY별 1줄.
- **content_hash 동일 → 쓰기 skip** (`updated` 보존). feature/work-item 모두 입력 동일 시 멱등.
- **고아 노드** — work-item/technology: KEY 를 `source_keys` 에서 제거, 비면 `status: archived`.
  feature: 멤버 0 이 되면 `status: archived` (하드삭제 안 함).
- **feature 정확성**: 추측 없이 권위값만 투영 → 휴리스틱 base 의 task 는 feature 에 섞이지 않음.
- 단방향: cruise → Brain. Brain 수동 편집은 다음 동기화에서 content_hash 가 다르면 덮어쓰일 수 있다.
