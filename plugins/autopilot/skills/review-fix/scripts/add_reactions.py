#!/usr/bin/env python3
"""
여러 코멘트에 일괄적으로 reaction을 추가한다.
Usage: python3 add_reactions.py {owner_repo} {comment_ids_json} {content}
Example: python3 add_reactions.py FlaSh2493/marketplace '[123, 456]' '+1'
"""
import argparse, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

def run_gh_api(owner_repo, comment_id, content):
    cmd = f"gh api repos/{owner_repo}/pulls/comments/{comment_id}/reactions -f content='{content}' --silent"
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return comment_id, r.returncode == 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("owner_repo")
    parser.add_argument("comment_ids_json")
    parser.add_argument("content", default="+1")
    args = parser.parse_args()

    try:
        comment_ids = json.loads(args.comment_ids_json)
    except:
        print(json.dumps({"status": "error", "reason": "Invalid JSON for comment_ids"}, ensure_ascii=False))
        sys.exit(1)

    success_count = 0
    failed_ids = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_gh_api, args.owner_repo, cid, args.content) for cid in comment_ids]
        for future in futures:
            cid, success = future.result()
            if success:
                success_count += 1
            else:
                failed_ids.append(cid)

    print(json.dumps({
        "status": "ok",
        "success_count": success_count,
        "failed_count": len(failed_ids),
        "failed_ids": failed_ids
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
