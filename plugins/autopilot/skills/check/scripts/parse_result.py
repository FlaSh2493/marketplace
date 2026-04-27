import json
import re
import sys

def parse_tsc(output):
    # Regex for TSC output: file(line,col): error TSXXXX: message
    # Or: file:line:col - error TSXXXX: message
    pattern = re.compile(r"^(.*?)[(:](?P<line>\d+)[, :](?P<col>\d+)\)?(?: -|:) error (?P<code>TS\d+): (?P<msg>.*)$")
    errors = []
    for line in output.splitlines():
        match = pattern.match(line)
        if match:
            errors.append({
                "file": match.group(1),
                "line": int(match.group("line")),
                "col": int(match.group("col")),
                "code": match.group("code"),
                "message": match.group("msg")
            })
    return errors

def parse_eslint_json(output):
    try:
        data = json.loads(output)
        errors = []
        for file_entry in data:
            file_path = file_entry.get("filePath", "")
            for msg in file_entry.get("messages", []):
                if msg.get("severity") == 2: # Error
                    errors.append({
                        "file": file_path,
                        "line": msg.get("line"),
                        "col": msg.get("column"),
                        "code": msg.get("ruleId"),
                        "message": msg.get("message")
                    })
        return errors
    except:
        return []

def parse_generic(output):
    # Fallback for other tools (like vitest/jest if they don't output JSON)
    errors = []
    # Try to find common file:line patterns
    pattern = re.compile(r"^(.*?):(\d+):(\d+):? (.*)$")
    for line in output.splitlines():
        match = pattern.match(line)
        if match:
            errors.append({
                "file": match.group(1),
                "line": int(match.group(2)),
                "col": int(match.group(3)),
                "message": match.group(4)
            })
    return errors

def main():
    if len(sys.argv) < 3:
        print("Usage: parse_result.py <tool> <output_file>")
        sys.exit(1)
    
    tool = sys.argv[1]
    output_file = sys.argv[2]
    
    with open(output_file, "r") as f:
        output = f.read()
    
    errors = []
    if tool == "tsc":
        errors = parse_tsc(output)
    elif tool == "eslint":
        errors = parse_eslint_json(output)
    else:
        errors = parse_generic(output)
    
    result = {
        "tool": tool,
        "passed": len(errors) == 0,
        "error_count": len(errors),
        "errors": errors[:10],
        "shown": min(len(errors), 10)
    }
    
    if len(errors) > 10:
        result["truncated"] = f"{len(errors) - 10} more errors omitted"
        
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
