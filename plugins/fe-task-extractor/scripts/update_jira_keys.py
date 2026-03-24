import os
import sys
import json
import argparse
import re

def main():
    parser = argparse.ArgumentParser(description='Update Jira keys in markdown file.')
    parser.add_argument('md_path', help='Path to the markdown file')
    parser.add_argument('keys_json', help='JSON string mapping task IDs to Jira keys')
    parser.add_argument('--project', help='Jira project key')
    args = parser.parse_args()

    try:
        keys_map = json.loads(args.keys_json)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON for keys mapping: {args.keys_json}", file=sys.stderr)
        sys.exit(1)

    if not args.md_path or not os.path.exists(args.md_path):
        print(f"Error: Markdown file not found at {args.md_path}", file=sys.stderr)
        sys.exit(1)

    with open(args.md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update individual task Jira fields
    for task_id, jira_key in keys_map.items():
        # Match ## FE-01. {Title} ... jira: {anything}
        pattern = rf"(## {task_id}\..*?\n- jira:) .*?(?=\n|$)"
        replacement = rf"\1 {jira_key}"
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # Update summary Jira field at the top
    if args.project:
        content = re.sub(r"(- jira:) 미생성", rf"\1 {args.project}", content)

    with open(args.md_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Successfully updated Jira keys in {args.md_path}")

if __name__ == "__main__":
    main()
