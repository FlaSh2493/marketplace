import os
import sys
from pathlib import Path

REQUIRED_ENV = ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"]
STORE_ROOT = Path.home() / "Documents" / "tasks"


def check_env():
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        print(f"error: missing env vars: {', '.join(missing)}", file=sys.stderr)
        print("  export JIRA_BASE_URL=https://yourorg.atlassian.net", file=sys.stderr)
        print("  export JIRA_EMAIL=you@example.com", file=sys.stderr)
        print("  export JIRA_API_TOKEN=...", file=sys.stderr)
        sys.exit(1)


def get_env():
    check_env()
    return {
        "base_url": os.environ["JIRA_BASE_URL"].rstrip("/"),
        "email": os.environ["JIRA_EMAIL"],
        "token": os.environ["JIRA_API_TOKEN"],
    }


def issue_dir(key: str) -> Path:
    d = STORE_ROOT / key
    d.mkdir(parents=True, exist_ok=True)
    return d


def attachments_dir(key: str) -> Path:
    d = issue_dir(key) / "attachments"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_file(key: str) -> Path:
    return issue_dir(key) / ".log"


def check_deps():
    missing = []
    try:
        import requests  # noqa: F401
    except ImportError:
        missing.append("requests")
    try:
        import yaml  # noqa: F401
    except ImportError:
        missing.append("PyYAML")
    if missing:
        print(f"error: missing Python packages: {', '.join(missing)}", file=sys.stderr)
        print(f"  pip install {' '.join(missing)}", file=sys.stderr)
        sys.exit(1)
