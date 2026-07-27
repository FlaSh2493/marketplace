# cruise

> 이슈 단위 개발 사이클 자동화 — 플랜·구현·검사·커밋·머지·PR·리뷰·회고 + Jira 동기화

CWD의 git HEAD가 단일 진실. 메인 체크아웃과 워크트리 동등 동작.
산출물은 `~/Documents/tasks/{KEY}/`(기본값, `config.json`에서 변경 가능) 에 `.md`로만 남긴다.

---

## 설정 (config.json)

Jira 인증·팀 공통값은 **단일 파일** `~/.config/cruise/config.json` 로 관리한다
(경로 우선순위: `$CRUISE_HOME` > `$XDG_CONFIG_HOME/cruise` > `~/.config/cruise`).
비밀값을 담으므로 레포 밖에 두고 `600` 권한으로 저장한다.

설정·수정·확인은 대화형 스크립트로 한다 (비밀값은 `getpass` — **본인 터미널에서** 실행):

```bash
python3 scripts/setup_config.py            # 전체 대화형 설정 (Enter=기존값 유지)
python3 scripts/setup_config.py set KEY    # 특정 키만 수정
python3 scripts/setup_config.py show       # 현재값 표시 (비밀 마스킹)
python3 scripts/setup_config.py delete KEY # 키 삭제 (--all: 전체 삭제)
```

| 블록 | 키 | 필수 | 설명 |
|------|----|------|------|
| credentials | `email` | ✅ | Jira 계정 이메일 |
| credentials | `jira_api_token` | ✅ | Jira API 토큰 |
| settings | `base_url` | | Jira 베이스 URL (기본 `https://madup.atlassian.net`) |
| settings | `default_project` | | plan 신규 이슈 생성 기본 프로젝트 키 (없으면 create 비활성) |
| settings | `tasks_root` | | 산출물 저장 루트 (기본 `~/Documents/tasks`) |

`settings` 값은 생략 시 코드 내 기본값이 적용된다. 형식은 [`config.json.example`](./config.json.example) 참고.

---

## 스킬

| 스킬 | 명령어 | 설명 |
|------|--------|------|
| plan | `/cruise:plan` | 이슈 명세 분석 → 코드베이스 영향 탐색 → plan.md 생성 |
| build | `/cruise:build` | plan.md Phase 단위 구현 + lint/type/test 검사 + 요구사항 검증(미구현 시 인메모리 재구현). 종료 시 브랜치 전체 요약 summary.md 갱신 |
| commit | `/cruise:commit` | 변경사항 도메인별 그룹핑 → Conventional Commits 형식 커밋 |
| merge | `/cruise:merge` | 현재 브랜치로 소스 브랜치 머지 (항상 `git merge`) |
| pr | `/cruise:pr` | PR 제목·본문 자동 생성 → 확인 후 push + PR 생성 |
| review | `/cruise:review` | CodeRabbit 리뷰 대기 → 코멘트 적용 → 검증 → push |
| result | `/cruise:result` | task 종료 후 회고 result.md 작성 (결과·잘된 점·실패·결정). 소비자가 읽어 활용 |
| log | `/cruise:log` | cruise 산출물(plan/summary/review/result) + gh 조회 commit·PR을 모아 Jira 이슈에 '작업 로그' 댓글 1건으로 기록 |
| update | `/cruise:update` | 로컬에서 편집한 task.md 를 Jira에 반영 (변경 필드만 diff·PUT) |

모든 스킬은 명시적 호출 전용 (`disable-model-invocation: true`).

---

## 워크플로우

```
plan → build → commit → merge → pr → review → result
```

각 스킬은 독립적으로 호출 가능. 의존성 없음.
`result`는 task 종료 후 회고 `result.md`를 남긴다 — `/cruise:log` 등 소비자가 읽어 이슈 댓글 등에 활용한다.

---

## 산출물

모든 스킬 종료 시 `~/Documents/tasks/{KEY}/{skill}.md` 기록.
재호출해도 누락 없이 갱신 또는 append.

```
~/Documents/tasks/{KEY}/
├── task.md      ← 이슈 명세 (Jira fetch 또는 cruise-inline)
├── plan.md
├── summary.md   ← build 유일 산출물. 브랜치 전체(base 대비) 변경 요약 + 검사·요구사항 검증 결과. build마다 덮어쓰기
├── review.md    ← iterations[] append
└── result.md    ← 회고. 1회 작성·덮어쓰기. 소비자(cruise:log 등)가 읽음
```

> 커밋·PR·머지는 산출물 파일로 남기지 않는다 (CONTRACT v6·v7). 진실 원천은 git 이력과 GitHub이며,
> result·cruise:log 는 `gh pr list`·`git log --merges` 로 직접 조회한다.

frontmatter는 모든 파일이 동일한 공통 필드(CONTRACT v9: 5필드)를 가진다 (인덱싱 균일성).

산출물의 안정적 on-disk 스키마는 [`CONTRACT.md`](./CONTRACT.md) 에 정의되어 있다.

---

## 이슈 없이 동작

브랜치명에서 `[A-Z]+-\d+` 패턴 추출 실패 시 `key = slug(branch)`.
산출물은 `~/Documents/tasks/{slug}/` 에 저장.

`plan` 스킬: task.md 없으면 대화 컨텍스트에서 자동 추출.
`build / commit / merge / pr / review / result`: 이슈 키 없이도 단독 동작.

---

## Jira 연동

cruise가 Jira REST API로 직접 이슈를 동기화한다 (구 jsync 기능 흡수). 인증·기본값은 `config.json`으로 관리한다(위 설정 섹션).

- **plan** — 브랜치명에 Jira 키가 있으면 **매번 새로 fetch**해 `~/Documents/tasks/{KEY}/task.md` 를 명세로 쓴다. 키가 없으면 대화 내용으로 **이슈를 생성**(게이트 승인)하고 그 키로 브랜치를 잡은 뒤 fetch한다.
- **update** (`/cruise:update {KEY}`) — 로컬에서 편집한 task.md 변경분을 Jira에 반영 (변경 필드만 PUT, 상태 전이·댓글·워크로그·링크·이미지 처리).
- **log** (`/cruise:log {KEY}`) — cruise 산출물 + commit·PR 이력을 '작업 로그' 댓글 1건으로 이슈에 기록.

---

## 회고 (result)

task 종료 후 `/cruise:result` → 회고 `result.md` 작성:
`## 결과`·`## 잘된 점`·`## 어려웠던 점 / 실패`·`## 결정`·`## 사용 기술`·`## 후속 작업`.

- 1회 작성·덮어쓰기. frontmatter 필드는 `scripts/result/gather.py`가 형제 산출물에서 결정적으로 수집.
- 소비자(예: `/cruise:log`)가 CONTRACT.md §5 스키마만 보고 읽어 Jira 이슈 댓글 등에 활용한다.

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
