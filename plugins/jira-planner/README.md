# Jira Planner Plugin for Claude Code - v4 (Final)

요구사항 분석부터 Jira 이슈 생성, 순차적 구현 및 자동 문서화까지 지원하는 워크플로우 자동화 플러그인입니다.

## 주요 기능
- **이슈 자동 분할**: 원본 요구사항을 분석하여 독립적으로 구현 가능한 이슈 단위로 분할하고 요구사항을 재작성합니다.
- **의존성 기반 순서화**: 이슈 간 파일 의존성을 분석하여 최적의 구현 순서를 결정합니다.
- **자동 연결(Auto-chaining)**: 한 이슈가 완료되면 자동으로 다음 이슈의 컨텍스트를 로드하여 흐름이 끊기지 않게 합니다.
- **자동 문서화**: 구현 완료 시 `plan.md` 등을 자동으로 생성하여 이력을 관리합니다.

## 설치 및 설정
`plugins/jira-planner` 폴더를 프로젝트에 포함시키면 Claude Code가 자동으로 인식합니다.

### Atlassian MCP 연결
Jira REST API 사용을 위해 Atlassian MCP 서버가 연결되어 있어야 합니다.
`.mcp.json` 예시:
```json
{
  "atlassian": {
    "command": "npx",
    "args": ["-y", "@anthropic-ai/atlassian-mcp-server"],
    "env": {
      "JIRA_BASE_URL": "https://your-company.atlassian.net",
      "JIRA_EMAIL": "user@company.com",
      "JIRA_API_TOKEN": "your-token"
    }
  }
}
```

## 사용 방법
1. `/jira-create spec.md`: 요구사항 분석 및 이슈 생성
2. `/jira-start spec-name`: 작업 시작 (이슈 간 자동 전환)
3. 구현 완료 후 "ㅇ" 입력: 다음 이슈로 자동 전환
4. `/jira-status`: 현재 진행 상황 확인

## 디렉토리 구조
```
jira-planner/
├── skills/          # 명령어 및 자동 로직
├── agents/          # 분석 및 분할 에이전트
└── README.md
```

작업 산출물은 사용자가 지정한 `{workDir}/jira-planner/specs/` 하위에 저장됩니다.
