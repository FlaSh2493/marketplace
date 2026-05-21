#!/usr/bin/env python3
"""
단일 검사 도구를 실행하고 구조화된 결과를 반환한다.
Usage: python3 run_check.py {tool} {cmd} --cwd {dir} [--auto-fix]
"""
import argparse
import json
import os
import re
import subprocess
import sys


def run_command(cmd, cwd):
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=cwd,
    )
    stdout, stderr = process.communicate()
    return stdout, stderr, process.returncode


def try_auto_fix(actual_tool, cmd, cwd):
    if actual_tool == "eslint":
        fix_cmd = cmd.replace("--format json", "").strip() + " --fix"
        _, _, rc = run_command(fix_cmd, cwd)
        return rc != 127
    elif actual_tool == "biome":
        fix_cmd = cmd.replace("--reporter=json", "").strip()
        fix_cmd = fix_cmd.replace("check", "check --fix") if "check" in fix_cmd else fix_cmd + " --fix"
        _, _, rc = run_command(fix_cmd, cwd)
        return rc != 127
    elif actual_tool == "ruff":
        _, _, rc = run_command(f"ruff check --fix {cwd}", cwd)
        return rc != 127
    return False


def parse_tsc(output):
    pattern = re.compile(
        r"^(.*?)[(:](?P<line>\d+)[, :](?P<col>\d+)\)?(?: -|:) error (?P<code>TS\d+): (?P<msg>.*)$"
    )
    errors = []
    for line in output.splitlines():
        m = pattern.match(line)
        if m:
            errors.append({
                "file": m.group(1), "line": int(m.group("line")),
                "col": int(m.group("col")), "code": m.group("code"),
                "message": m.group("msg"),
            })
    return errors


def parse_eslint_json(output):
    try:
        data = json.loads(output)
        errors = []
        for entry in data:
            for msg in entry.get("messages", []):
                if msg.get("severity") == 2:
                    errors.append({
                        "file": entry.get("filePath", ""),
                        "line": msg.get("line"), "col": msg.get("column"),
                        "code": msg.get("ruleId"), "message": msg.get("message"),
                    })
        return errors
    except Exception:
        return []


def parse_ruff_json(output):
    try:
        data = json.loads(output)
        errors = []
        for item in data:
            loc = item.get("location", {})
            errors.append({
                "file": item.get("filename", ""), "line": loc.get("row"),
                "col": loc.get("column"), "code": item.get("code"),
                "message": item.get("message", ""),
            })
        return errors
    except Exception:
        return []


def parse_pytest(output):
    errors = []
    pattern = re.compile(r"^FAILED\s+(.*?)(?:\s+-\s+(.*))?$")
    for line in output.splitlines():
        m = pattern.match(line)
        if m:
            errors.append({"file": m.group(1), "message": m.group(2) or "Test failed"})
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tool")
    parser.add_argument("cmd")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--auto-fix", action="store_true")
    args = parser.parse_args()

    tool_type = args.tool
    cmd = args.cmd
    cwd = args.cwd

    actual_tool = "unknown"
    if "biome" in cmd:
        actual_tool = "biome"
        if "check" in cmd and "--reporter" not in cmd:
            cmd += " --reporter=json"
    elif "eslint" in cmd or tool_type == "lint":
        actual_tool = "eslint"
        if "--format" not in cmd:
            cmd += " --format json"
    elif "ruff" in cmd:
        actual_tool = "ruff"
    elif "tsc" in cmd or tool_type == "check-types":
        actual_tool = "tsc"
        if "--pretty" not in cmd:
            cmd += " --pretty false"
    elif "pytest" in cmd or tool_type == "test":
        actual_tool = "pytest"
        if "--tb" not in cmd:
            cmd += " --tb=line"

    stdout, stderr, returncode = run_command(cmd, cwd)

    auto_fixed = False
    if args.auto_fix and returncode != 0 and tool_type == "lint" and actual_tool in ("eslint", "biome", "ruff"):
        auto_fixed = try_auto_fix(actual_tool, cmd, cwd)
        if auto_fixed:
            stdout, stderr, returncode = run_command(cmd, cwd)

    output = stdout if stdout.strip() else stderr

    errors = []
    if actual_tool == "tsc":
        errors = parse_tsc(output)
    elif actual_tool == "eslint":
        errors = parse_eslint_json(output)
    elif actual_tool == "ruff":
        errors = parse_ruff_json(output)
    elif actual_tool == "pytest":
        errors = parse_pytest(output)
    else:
        if returncode != 0:
            errors.append({"message": output.strip() or stderr.strip() or "Unknown error"})

    result = {
        "tool": actual_tool,
        "tool_type": tool_type,
        "passed": returncode == 0 and len(errors) == 0,
        "error_count": len(errors),
        "errors": errors[:10],
        "shown": min(len(errors), 10),
        "auto_fixed": auto_fixed,
    }
    if len(errors) > 10:
        result["truncated"] = f"{len(errors) - 10} more errors omitted"

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
