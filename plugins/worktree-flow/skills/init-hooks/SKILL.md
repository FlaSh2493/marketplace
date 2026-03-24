---
name: worktree-flow-init-hooks
description: Registers automatic WIP commit hooks in the current project's .claude/settings.json.
---

# Init Hooks

This skill registers the necessary hooks in the current repository to support automatic WIP commits and other functionalities.

## Usage
- `/worktree-flow:init-hooks`

## Execution
Run the following script:
- `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/install_hooks.py`
