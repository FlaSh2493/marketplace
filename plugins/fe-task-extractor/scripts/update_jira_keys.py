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
        # 기존 파일 찾기: FE-XX.md
        old_filename = f"{task_id}.md"
        old_path = os.path.join(args.dir_path, old_filename)

        if not os.path.exists(old_path):
            results.append({"task_id": task_id, "jira_key": jira_key, "status": "file_not_found", "old": old_filename})
            continue

        # 파일 내용 읽기
        with open(old_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 1. 제목의 FE-XX를 JIRA-KEY로 교체: # FE-01: {제목} → # PROJ-101: {제목}
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

        # 3. 파일 저장
        with open(old_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 4. 파일 리네임: FE-01.md → PROJ-101.md
        new_filename = f"{jira_key}.md"
        new_path = os.path.join(args.dir_path, new_filename)

        if os.path.exists(new_path):
            results.append({"task_id": task_id, "jira_key": jira_key, "status": "rename_conflict", "old": old_filename, "new": new_filename})
            continue

        os.rename(old_path, new_path)
        results.append({"task_id": task_id, "jira_key": jira_key, "status": "success", "old": old_filename, "new": new_filename})

    print(json.dumps({"results": results}, ensure_ascii=False))

if __name__ == "__main__":
    main()
