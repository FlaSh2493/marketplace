# cruise

> 이슈 단위 개발 사이클 자동화 — 플랜·구현·검사·커밋·머지·PR·리뷰

CWD의 git HEAD가 단일 진실. 메인 체크아웃과 워크트리 동등 동작.
산출물은 `~/Documents/tasks/{KEY}/` 에 `.md`로만 남긴다.

---

## 스킬

| 스킬 | 명령어 | 설명 |
|------|--------|------|
| plan | `/cruise:plan` | 이슈 명세 분석 → 코드베이스 영향 탐색 → plan.md 생성 |
| build | `/cruise:build` | plan.md Phase 단위 구현. 종료 시 브랜치 전체 변경 요약 summary.md 갱신 |
| check | `/cruise:check` | lint → type → test 순차 실행. 실패 시 자동 수정 (최대 3회) |
| commit | `/cruise:commit` | 변경사항 도메인별 그룹핑 → Conventional Commits 형식 커밋 |
| merge | `/cruise:merge` | 현재 브랜치로 소스 브랜치 머지 (항상 `git merge`) |
| pr | `/cruise:pr` | PR 제목·본문 자동 생성 → 확인 후 push + PR 생성 |
| review | `/cruise:review` | CodeRabbit 리뷰 대기 → 코멘트 적용 → 검증 → push |

모든 스킬은 명시적 호출 전용 (`disable-model-invocation: true`).

---

## 워크플로우

```
plan → build → check → commit → merge → pr → review
```

각 스킬은 독립적으로 호출 가능. 의존성 없음.

---

## 산출물

모든 스킬 종료 시 `~/Documents/tasks/{KEY}/{skill}.md` 기록.
재호출해도 누락 없이 갱신 또는 append.

```
~/Documents/tasks/{KEY}/
├── task.md      ← 이슈 명세 (jsync 또는 cruise-inline)
├── plan.md
├── build.md     ← ## Run append 로그
├── summary.md   ← 브랜치 전체(base 대비) 변경 요약. build마다 덮어쓰기
├── check.md
├── commit.md
├── merge.md     ← entries[] append
├── pr.md
└── review.md    ← iterations[] append
```

frontmatter는 모든 파일이 동일한 9개 공통 필드를 가진다 (인덱싱 균일성).

---

## 이슈 없이 동작

브랜치명에서 `[A-Z]+-\d+` 패턴 추출 실패 시 `key = slug(branch)`.
산출물은 `~/Documents/tasks/{slug}/` 에 저장.

`plan` 스킬: task.md 없으면 대화 컨텍스트에서 자동 추출.
`check / commit / merge / pr / review`: 이슈 키 없이도 단독 동작.

---

## jsync 연동

`/jsync:fetch MKT-142` 로 생성된 `~/Documents/tasks/MKT-142/task.md` 를
`/cruise:plan` 이 자동으로 감지해 명세로 사용한다.

---

## 머지 정책

- 항상 `git merge`. rebase / force-push / `pull --rebase` 일체 금지.
- push는 `pr` · `review` 스킬 또는 사용자 수동.

---

## 설치

```bash
/plugin marketplace add FlaSh2493/marketplace
/plugin install cruise@flash-plugins
```
