#!/usr/bin/env python3
"""
ExitPlanMode가 저장한 플랜 파일을 목적지로 복사.
Usage: python3 save_plan.py <src> <dest>
"""
import json, os, shutil, sys

def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)

if len(sys.argv) != 3:
    error("USAGE", "Usage: save_plan.py <src> <dest>")

src, dest = sys.argv[1], sys.argv[2]

if not os.path.exists(src):
    error("SRC_NOT_FOUND", f"소스 파일 없음: {src}")

os.makedirs(os.path.dirname(dest), exist_ok=True)
shutil.copy2(src, dest)
ok({"src": src, "dest": dest})
