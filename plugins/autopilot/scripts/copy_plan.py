#!/usr/bin/env python3
"""Copy Claude plan file to tasks/{issue}/plan.md."""
import argparse
import json
import os
import shutil
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_path", required=True, help="Source plan file path")
    parser.add_argument("--issue-doc-root", required=True, help="Issue doc root directory")
    parser.add_argument("--issue", required=True, help="Issue key (e.g. SPT-3711)")
    args = parser.parse_args()

    src = args.from_path
    if not os.path.isfile(src):
        print(json.dumps({"status": "error", "reason": f"Source file not found: {src}"}))
        sys.exit(1)

    dest_dir = os.path.join(args.issue_doc_root, "tasks", args.issue)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, "plan.md")

    shutil.copy2(src, dest)
    print(json.dumps({"status": "ok", "dest": dest}))


if __name__ == "__main__":
    main()
