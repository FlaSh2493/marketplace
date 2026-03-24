import os
import sys
import json
import argparse

def find_project_root(start_path):
    current_path = os.path.abspath(start_path)
    while current_path != os.path.dirname(current_path):
        if any(os.path.exists(os.path.join(current_path, marker)) for marker in ['package.json', '.git', 'tsconfig.json']):
            return current_path
        current_path = os.path.dirname(current_path)
    return None

def main():
    parser = argparse.ArgumentParser(description='Initialize task directory and return file path.')
    parser.add_argument('feature_name', help='Feature name in kebab-case or space-separated')
    parser.add_argument('--root', help='Optional project root path')
    args = parser.parse_args()

    project_root = args.root if args.root else find_project_root(os.getcwd())
    
    if not project_root:
        print(json.dumps({"error": "Project root not found"}), file=sys.stderr)
        sys.exit(1)

    task_dir = os.path.join(project_root, '.docs', 'task')
    os.makedirs(task_dir, exist_ok=True)

    # Convert feature name to kebab-case for filename
    kebab_name = args.feature_name.lower().replace(' ', '-')
    filename = f"{kebab_name}.md"
    file_path = os.path.join(task_dir, filename)

    print(json.dumps({"path": file_path}))

if __name__ == "__main__":
    main()
