# Jira Dev Auto Plugin

Jira 티켓 조회부터 코드 병합까지 전체 개발 생명주기를 자동화하는 Claude Code 플러그인.

## 전체 워크플로우

```
/jira auto
  PHASE 0: 워크스페이스 초기화
  PHASE 1: Jira 티켓 조회 & 캐시
  PHASE 2: 도메인 분류 & 의존성 분석
  PHASE 3: 요구사항 정제 (7항목 규격)
  PHASE 4: 구현 계획 수립
  PHASE 5: 코드 구현 (병렬/순차)
  PHASE 6: 변경 감지 & 재동기화 (체크포인트)
  PHASE 7: 병합
  PHASE 8: 상태 조회
```

## 실행 계층 원칙

```
CLI   → 가능하면 CLI로 (토큰 0, 즉시)
MCP   → 외부 데이터가 필요하면 (Jira, Slack, GitHub)
Skill → 판단 기준이 필요하면 (해당 단계 것만, 지연 로드)
LLM   → 분석/생성이 필요할 때만 (최소 컨텍스트)
```

## 사용 방법

### 전체 자동화
```
/jira auto
```

### 단계별 실행
```
/jira init              워크스페이스 생성
/jira fetch             Jira 티켓 조회
/jira analyze           도메인 분류
/jira plan              구현 계획 수립
/jira implement         구현 시작
/jira merge             병합
/jira status            전체 현황
/jira status PROJ-123   개별 티켓 상세
```

### 변경 감지
```
/jira refresh           모든 활성 티켓 재조회
/jira refresh PROJ-123  특정 티켓만
/jira diff PROJ-123     PIN vs 최신 차이
```

### 복구 & 관리
```
/jira resume                      중단 복구
/jira resume --workspace hotfix   특정 워크스페이스 복구
/jira worktrees                   worktree 목록
/jira worktrees --unmerged        미병합만
/jira cleanup                     완료 worktree 정리
```

## 디렉토리 구조 (사용자 프로젝트)

```
프로젝트 루트/
├── .docs/
│   └── {workspace}/              # /jira init 시 생성
│       ├── _index.yaml
│       ├── _cache/
│       │   ├── PROJ-123.snapshot.json
│       │   ├── PROJ-123.latest.json
│       │   └── PROJ-123.diff.json
│       └── {domain}/
│           ├── PROJ-123.requirement.yaml
│           ├── PROJ-123.plan.yaml
│           └── PROJ-123.status.yaml
├── .claude/
│   ├── skills/                   # references/ 파일들을 복사
│   ├── commands/                 # 명령어 정의
│   └── settings.yaml
└── ../worktrees/
    └── PROJ-123/
```

## 서브에이전트
- `jira-orchestrator`: `/jira auto` 전체 흐름 진행
- `jira-implementer`: 개별 티켓 코드 구현 (최소 컨텍스트)

## 스킬 목록
| 스킬 | 역할 |
|---|---|
| `jira-init` | 워크스페이스 초기화 |
| `jira-fetch` | Jira 조회 & 캐시 |
| `jira-analyze` | 도메인 분류 |
| `jira-refine` | 요구사항 정제 |
| `jira-plan` | 구현 계획 수립 |
| `jira-implement` | 코드 구현 |
| `jira-merge` | 병합 & 충돌 해결 |
| `jira-refresh` | 변경 감지 & 재동기화 |
| `jira-status` | 상태 조회 (토큰 0) |
| `jira-resume` | 중단 복구 |
