import os
import sys
import json
import argparse
import re

def main():
    parser = argparse.ArgumentParser(description='Update Jira keys in markdown files and rename FE-XX.md to JIRA-KEY.md.')
    parser.add_argument('dir_path', help='Path to the task directory containing FE-XX.md files')
    parser.add_argument('keys_json', help='JSON string mapping task IDs to Jira keys (e.g., \'{"FE-01":"PROJ-101"}\')')
    parser.add_argument('--project', help='Jira project key for header-level jira field')
    args = parser.parse_args()

    try:
        keys_map = json.loads(args.keys_json)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON for keys mapping: {args.keys_json}", file=sys.stderr)
        sys.exit(1)

    if not args.dir_path or not os.path.isdir(args.dir_path):
        print(f"Error: Directory not found at {args.dir_path}", file=sys.stderr)
        sys.exit(1)

    results = []

    for task_id, jira_key in keys_map.items():
        # 기존 폴더 찾기: FE-XX/
        old_dir = os.path.join(args.dir_path, task_id)
        old_file = os.path.join(old_dir, f"{task_id}.md")

        if not os.path.exists(old_dir):
            results.append({"task_id": task_id, "jira_key": jira_key, "status": "file_not_found", "old": task_id})
            continue

        # 파일 내용 읽기
        with open(old_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 1. 제목의 FE-XX를 JIRA-KEY로 교체
        content = re.sub(
            rf"^# {re.escape(task_id)}: ",
            f"# {jira_key}: ",
            content,
            flags=re.MULTILINE
        )

        # 2. jira 필드 업데이트: - jira: 미생성 → - jira: PROJ-101
        content = re.sub(
            r"(- jira:) 미생성",
            rf"\1 {jira_key}",
            content
        )

        # 3. 파일명 변경: FE-01.md → PROJ-101.md (폴더 안에서)
        new_file = os.path.join(old_dir, f"{jira_key}.md")
        with open(new_file, 'w', encoding='utf-8') as f:
            f.write(content)
        if new_file != old_file:
            os.remove(old_file)

        # 4. 폴더 리네임: FE-01/ → PROJ-101/
        new_dir = os.path.join(args.dir_path, jira_key)
        if os.path.exists(new_dir):
            results.append({"task_id": task_id, "jira_key": jira_key, "status": "rename_conflict", "old": task_id, "new": jira_key})
            continue

        os.rename(old_dir, new_dir)
        results.append({"task_id": task_id, "jira_key": jira_key, "status": "success", "old": task_id, "new": jira_key})

    print(json.dumps({"results": results}, ensure_ascii=False))

if __name__ == "__main__":
    main()
