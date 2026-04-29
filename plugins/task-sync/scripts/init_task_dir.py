import os
import sys
import json

def find_project_root(start_path):
    current_path = os.path.abspath(start_path)
    while current_path != os.path.dirname(current_path):
        if any(os.path.exists(os.path.join(current_path, marker)) for marker in ['package.json', '.git', 'tsconfig.json']):
            return current_path
        current_path = os.path.dirname(current_path)
    return None

def main():
    search_start = os.getcwd()
    project_root = find_project_root(search_start)

    if not project_root:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = find_project_root(script_dir)

    if not project_root:
        print(json.dumps({"error": "Project root not found"}), file=sys.stderr)
        sys.exit(1)

    task_dir = os.path.join(project_root, '.docs', 'tasks')
    state_dir = os.path.join(task_dir, '.state')
    os.makedirs(task_dir, exist_ok=True)
    os.makedirs(state_dir, exist_ok=True)

    print(json.dumps({"dir": task_dir, "state_dir": state_dir}))

if __name__ == "__main__":
    main()
