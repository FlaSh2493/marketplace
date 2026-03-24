#!/usr/bin/env python3
import json
import os
import sys

def main():
    # 1. Determine Project Root and Plugin Root
    # In the Claude workspace, CLAUDE_PROJECT_DIR and CLAUDE_PLUGIN_ROOT are usually set.
    project_root = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
    # If we are running this from /worktree-flow/scripts/install_hooks.py, 
    # the plugin root is two levels up.
    default_plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', default_plugin_root)

    # 2. Paths to relevant files
    settings_dir = os.path.join(project_root, '.claude')
    settings_file = os.path.join(settings_dir, 'settings.json')
    plugin_hooks_file = os.path.join(plugin_root, 'hooks/hooks.json')

    # Ensure .claude directory exists
    if not os.path.exists(settings_dir):
        os.makedirs(settings_dir)

    # 3. Load Plugin Hooks
    if not os.path.exists(plugin_hooks_file):
        print(f"Error: Plugin hooks file not found at {plugin_hooks_file}")
        sys.exit(1)

    with open(plugin_hooks_file, 'r', encoding='utf-8') as f:
        plugin_hooks_data = json.load(f)

    # 4. Load/Create Project Settings
    settings_data = {}
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Failed to parse {settings_file}. Starting with empty settings.")

    # 5. Merge Hooks
    if 'hooks' not in settings_data:
        settings_data['hooks'] = {}

    for event, actions in plugin_hooks_data.get('hooks', {}).items():
        if event not in settings_data['hooks']:
            settings_data['hooks'][event] = []
        
        # Avoid duplicate registration
        existing_actions = settings_data['hooks'][event]
        for action in actions:
            # We check if an action with the same command already exists
            cmd = action.get('command')
            if not any(a.get('command') == cmd for a in existing_actions):
                # Ensure the path is correct
                # Actually, in hooks.json, it's already ${CLAUDE_PLUGIN_ROOT}/scripts/wip_commit.sh
                existing_actions.append(action)
                print(f"Registered {event} hook for worktree-flow.")
            else:
                print(f"{event} hook for worktree-flow already exists. Skipping.")

    # 6. Save Settings
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings_data, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print(f"Hooks successfully registered in {settings_file}")

if __name__ == '__main__':
    main()
