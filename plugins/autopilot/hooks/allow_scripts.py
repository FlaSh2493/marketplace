#!/usr/bin/env python3
"""
PermissionRequest 훅: autopilot 스크립트 경로의 Bash 명령은 자동 승인.
다른 경로는 건드리지 않음.
"""
import json, os, sys


def main():
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").rstrip("/")
    if not plugin_root:
        sys.exit(0)

    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")

    scripts_path = os.path.join(plugin_root, "scripts")
    if scripts_path in command:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "permissionDecision": "allow",
                "permissionDecisionReason": "autopilot 플러그인 스크립트"
            }
        }))

    sys.exit(0)


if __name__ == "__main__":
    main()
