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
    parser = argparse.ArgumentParser(description='Initialize task directory and return directory/file path.')
    parser.add_argument('feature_name', help='Branch name or feature name (e.g., feature/login-ui)')
    parser.add_argument('--root', help='Optional project root path')
    args = parser.parse_args()

    # Try to find project root from CWD or script location
    search_start = args.root if args.root else os.getcwd()
    project_root = find_project_root(search_start)
    
    if not project_root:
        # Fallback: search from the script's own location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = find_project_root(script_dir)
    
    if not project_root:
        print(json.dumps({"error": "Project root not found (package.json, .git, or tsconfig.json not found in parent directories)"}), file=sys.stderr)
        sys.exit(1)

    task_dir = os.path.join(project_root, '.docs', 'task')

    # 브랜치명의 '/'를 폴더 구조로 변환
    parts = args.feature_name.strip().split('/')
    sub_dirs = [p.strip().replace(' ', '-') for p in parts]
    
    # 이슈별 개별 파일 구조: 브랜치명 전체를 디렉토리로 사용
    target_dir = os.path.join(task_dir, *sub_dirs)
    os.makedirs(target_dir, exist_ok=True)
    
    # assets 디렉토리도 함께 생성
    assets_dir = os.path.join(target_dir, 'assets')
    os.makedirs(assets_dir, exist_ok=True)

    print(json.dumps({
        "dir": target_dir,
        "assets_dir": assets_dir
    }))

if __name__ == "__main__":
    main()
