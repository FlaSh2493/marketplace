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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tool", help="Tool name (lint, typecheck, test)")
    parser.add_argument("cmd", help="Command to run")
    parser.add_argument("--cwd", default=".", help="Working directory")
    args = parser.parse_args()

    tool_type = args.tool
    cmd = args.cmd
    cwd = args.cwd

    # Augment command for machine output if possible
    actual_tool = "unknown"
    if "eslint" in cmd or tool_type == "lint":
        actual_tool = "eslint"
        if "eslint" in cmd and "--format" not in cmd:
            cmd += " --format json"
    elif "tsc" in cmd or tool_type == "check-types":
        actual_tool = "tsc"
        if "tsc" in cmd and "--pretty" not in cmd:
            cmd += " --pretty false"
    elif "pytest" in cmd or tool_type == "test":
        actual_tool = "pytest"
        if "pytest" in cmd and "--tb" not in cmd:
            cmd += " --tb=line"

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
        "shown": min(len(errors), 10)
    }
    
    if len(errors) > 10:
        result["truncated"] = f"{len(errors) - 10} more errors omitted"
        
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
