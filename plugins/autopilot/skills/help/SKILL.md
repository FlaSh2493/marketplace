---
name: help
description: (명시적 커맨드 실행 전용) /autopilot:help 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# Autopilot Help

**실행 주체: Main Session**

## 사용법
`/autopilot:help`

## 실행 절차

`${CLAUDE_PLUGIN_ROOT}/HELP.txt` 파일을 Read하여 내용을 그대로 출력한다.


[TERMINATE]
