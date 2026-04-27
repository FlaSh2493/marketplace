import os
import json
import argparse
from pathlib import Path

def detect_nodejs(root: Path):
    package_json_path = root / "package.json"
    if not package_json_path.exists():
        return None

    with open(package_json_path, "r") as f:
        data = json.load(f)
    
    scripts = data.get("scripts", {})
    
    config = {}
    
    # 1. Lint
    if "lint" in scripts:
        config["lint"] = "npm run lint"
    elif (root / ".eslintrc.js").exists() or (root / "eslint.config.js").exists():
        config["lint"] = "npx eslint ."
    
    # 2. Check-types (TSC)
    if "check-types" in scripts:
        config["check-types"] = "npm run check-types"
    elif "typecheck" in scripts:
        config["check-types"] = "npm run typecheck"
    elif (root / "tsconfig.json").exists():
        config["check-types"] = "npx tsc --noEmit"
        
    # 3. Test
    if "test" in scripts:
        config["test"] = "npm run test"
    elif (root / "vitest.config.ts").exists() or (root / "vitest.config.js").exists():
        config["test"] = "npx vitest run"
    elif (root / "jest.config.js").exists():
        config["test"] = "npx jest"
    
    return config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Project root directory")
    parser.add_argument("--issue", help="Issue key for caching")
    parser.add_argument("--out", help="Explicit output path for config")
    args = parser.parse_args()

    root = Path(args.root)
    
    config = detect_nodejs(root)
    
    if not config:
        print("Error: No Node.js project detected (missing package.json)")
        return

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"Config saved to {out_path}")
    else:
        print(json.dumps(config, indent=2))

if __name__ == "__main__":
    main()
