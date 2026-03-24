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

    # 브랜치명의 '/'를 폴더 구조로 변환
    parts = args.feature_name.lower().split('/')
    sub_dirs = [p.strip().replace(' ', '-') for p in parts[:-1]]
    filename = f"{parts[-1].strip().replace(' ', '-')}.md"
    
    target_dir = os.path.join(task_dir, *sub_dirs) if sub_dirs else task_dir
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, filename)

    print(json.dumps({"path": file_path}))

if __name__ == "__main__":
    main()
