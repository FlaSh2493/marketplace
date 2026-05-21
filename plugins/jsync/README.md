# jsync

Jira 이슈를 REST API로 로컬에 저장하고, 편집 후 Jira에 반영하는 플러그인.
**컨텍스트 절약형**: 응답 본문은 Python 서브프로세스 메모리에서 처리 후 디스크에만 저장됩니다. 에이전트 컨텍스트엔 stdout 1줄만 들어옵니다.

## 환경변수 설정

```bash
export JIRA_BASE_URL=https://yourorg.atlassian.net
export JIRA_EMAIL=you@example.com
export JIRA_API_TOKEN=...
```

`~/.zshrc` 또는 `~/.bashrc`에 추가하면 매 세션마다 자동 적용됩니다.

## 의존성

```bash
pip install requests PyYAML
```

## 명령어

| 명령어 | 설명 |
|--------|------|
| `/jsync:list <PROJECT>` | 활성 스프린트 × 본인 할당 이슈 목록 출력 |
| `/jsync:fetch <PROJECT\|KEY>` | 이슈를 로컬 디스크에 저장 |
| `/jsync:update <KEY>` | 편집한 task.md를 Jira에 반영 |

## 워크플로우

```
1. /jsync:list MKT                     → 어떤 이슈가 있는지 확인
2. /jsync:fetch MKT                    → 활성 스프린트 전체 저장
   /jsync:fetch MKT-142                → 특정 이슈 저장
3. IDE에서 ~/Documents/jsync/MKT-142/task.md 편집 (사용자 직접)
4. /jsync:update MKT-142               → Jira에 반영
```

## 저장 구조

```
~/Documents/tasks/
└── MKT-142/
    ├── task.md      ← 편집 대상 (YAML frontmatter + Markdown 본문)
    ├── raw.json     ← Jira 원본 응답 (스크립트 전용, 에이전트 금지)
    └── meta.json    ← customfield 매핑 (스크립트 전용, 에이전트 금지)
```

> **경로 이행**: 기존 `~/Documents/jsync/` 폴더가 있다면 `mv ~/Documents/jsync/* ~/Documents/tasks/` 로 이동하세요.

## task.md 편집 가이드

| 필드/섹션 | 편집 가능 | 설명 |
|----------|----------|------|
| frontmatter 전체 | ✅ | summary, status, labels 등 |
| 본문 (description) | ✅ | Markdown으로 자유 편집 |
| `## New Comment` | ✅ | 내용 채우면 댓글 POST 후 초기화 |
| `add_worklog` | ✅ | `"2h 작업 설명"` 형식으로 채우면 worklog 추가 |
| `## Subtasks` | ❌ | read-only |
| `## Comments` | ❌ | read-only |
| `## Worklog` | ❌ | read-only |
| `## Attachments` | ❌ | read-only |

## fetch 인자

```bash
python fetch.py MKT              # 프로젝트 — 활성스프린트 × 본인할당
python fetch.py MKT,ADX          # 다중 프로젝트
python fetch.py MKT-142          # 이슈 키 직접
python fetch.py MKT-142,ADX-77   # 다중 이슈 키
python fetch.py MKT --jql "priority = High"   # 추가 JQL 필터
```

## list 인자

```bash
python list.py MKT               # 활성스프린트 × 본인할당
python list.py MKT,ADX           # 다중 프로젝트
python list.py MKT --all         # 스프린트 전체 (할당 제약 해제)
```
