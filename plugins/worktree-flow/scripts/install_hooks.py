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

    for event, entries in plugin_hooks_data.get('hooks', {}).items():
        if event not in settings_data['hooks']:
            settings_data['hooks'][event] = []
        
        existing_entries = settings_data['hooks'][event]
        for incoming_entry in entries:
            # Determine the commands (both raw and resolved) for this incoming entry
            raw_cmds = []
            resolved_cmds = []
            
            # Create a copy to modify for resolution
            resolved_entry = json.loads(json.dumps(incoming_entry))
            
            for action in resolved_entry.get('actions', []):
                if 'command' in action:
                    raw_cmd = action['command']
                    raw_cmds.append(raw_cmd)
                    
                    resolved_cmd = raw_cmd.replace('${CLAUDE_PLUGIN_ROOT}', plugin_root)
                    action['command'] = resolved_cmd
                    resolved_cmds.append(resolved_cmd)

            # Avoid duplicate registration
            # Check if any existing entry has the same matcher and same set of commands (either raw or resolved)
            is_duplicate = False
            for existing_entry in existing_entries:
                if existing_entry.get('matcher') == incoming_entry.get('matcher'):
                    existing_cmds = [a.get('command') for a in existing_entry.get('actions', []) if 'command' in a]
                    
                    # Check if existing commands match either the raw or resolved versions
                    if set(existing_cmds) == set(raw_cmds) or set(existing_cmds) == set(resolved_cmds):
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                existing_entries.append(resolved_entry)
                print(f"Registered {event} hook for worktree-flow.")
            else:
                print(f"{event} hook for worktree-flow already exists. Skipping.")


    # 6. Save Settings
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings_data, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print(f"Hooks successfully registered in {settings_file}")
    print("\nNext step: Run '/worktree-flow:wip on' to enable automatic WIP commits.")


if __name__ == '__main__':
    main()
