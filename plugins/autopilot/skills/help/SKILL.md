---
name: autopilot-help
description: autopilot 플러그인의 환경설정 방법과 사용법을 안내한다. "autopilot 설정", "autopilot 도움말", "help" 등을 요청할 때 사용한다.
---

# Autopilot Help

**실행 주체: Main Session**

## 사용법
`/autopilot:help`

## 실행 절차

`${CLAUDE_PLUGIN_ROOT}/HELP.txt` 파일을 Read하여 내용을 그대로 출력한다.

## 세션 상태 추적 실무
플러그인이 설치되면 Claude의 모든 요청/응답 시점에 상태가 기록됩니다.

### 레코드 포맷 (busy)
```json
{"state":"busy","session_id":"abc123","pid":12345,"cwd":"/path/to/repo","started":"2026-04-20T14:33:12+09:00","prompt_preview":"/autopilot:check"}
```

### 외부 구독 예시 (Shell)
```bash
# 실시간 구독
fswatch tasks/.state/sessions/<sid>/status.json | while read _; do
  jq -r '"\(.state) \(.prompt_preview // "")"' tasks/.state/sessions/<sid>/status.json
done
```

[TERMINATE]
