import subprocess
import sys
import os
import json
import argparse
from pathlib import Path

# Import the parsing functions from parse_result (or just copy them if preferred, but importing is cleaner)
# Since they are in the same directory, we can do this:
try:
    from parse_result import parse_tsc, parse_eslint_json, parse_ruff_json, parse_pytest
except ImportError:
    # Fallback if scripts are not in path
    import sys
    sys.path.append(os.path.dirname(__file__))
    from parse_result import parse_tsc, parse_eslint_json, parse_ruff_json, parse_pytest

def run_command(cmd, cwd):
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd
    )
    stdout, stderr = process.communicate()
    return stdout, stderr, process.returncode

def try_auto_fix(actual_tool, cmd, cwd):
    """lint 도구에 한해 --fix 명령을 실행한다.
    --fix는 수정 후에도 unfixable 에러가 남으면 exit non-zero를 반환하므로,
    명령 자체가 실행됐으면(rc != 127) True를 반환해 재검사를 항상 수행한다."""
    if actual_tool == "eslint":
        fix_cmd = cmd.replace("--format json", "").strip() + " --fix"
        _, _, rc = run_command(fix_cmd, cwd)
        return rc != 127  # 명령 없음(not found)이 아니면 재검사
    elif actual_tool == "biome":
        fix_cmd = cmd.replace("--reporter=json", "").strip()
        fix_cmd = fix_cmd.replace("check", "check --fix") if "check" in fix_cmd else fix_cmd + " --fix"
        _, _, rc = run_command(fix_cmd, cwd)
        return rc != 127
    elif actual_tool == "ruff":
        _, _, rc = run_command(f"ruff check --fix {cwd}", cwd)
        return rc != 127
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tool", help="Tool name (lint, typecheck, test)")
    parser.add_argument("cmd", help="Command to run")
    parser.add_argument("--cwd", default=".", help="Working directory")
    parser.add_argument("--auto-fix", action="store_true", help="lint 실패 시 --fix 자동 실행 후 재검사")
    args = parser.parse_args()

    tool_type = args.tool
    cmd = args.cmd
    cwd = args.cwd
    auto_fix = args.auto_fix

    # Augment command for machine output if possible
    actual_tool = "unknown"
    if "eslint" in cmd or tool_type == "lint":
        actual_tool = "eslint"
        if "biome" in cmd:
            actual_tool = "biome"
        elif "eslint" in cmd and "--format" not in cmd:
            cmd += " --format json"
    elif "ruff" in cmd:
        actual_tool = "ruff"
    elif "tsc" in cmd or tool_type == "check-types":
        actual_tool = "tsc"
        if "tsc" in cmd and "--pretty" not in cmd:
            cmd += " --pretty false"
    elif "pytest" in cmd or tool_type == "test":
        actual_tool = "pytest"
        if "pytest" in cmd and "--tb" not in cmd:
            cmd += " --tb=line"

    stdout, stderr, returncode = run_command(cmd, cwd)

    # lint 실패 시 --fix 자동 실행 후 재검사
    auto_fixed = False
    if auto_fix and returncode != 0 and tool_type == "lint" and actual_tool in ("eslint", "biome", "ruff"):
        auto_fixed = try_auto_fix(actual_tool, cmd, cwd)
        if auto_fixed:
            stdout, stderr, returncode = run_command(cmd, cwd)
    
    # We prioritize stdout for JSON formats, but some tools might use stderr
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
        # Generic fallback: if returncode != 0 and no errors parsed, treat whole output as one error
        if returncode != 0 and not errors:
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
        
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
