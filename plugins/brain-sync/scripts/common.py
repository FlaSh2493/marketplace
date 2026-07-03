#!/usr/bin/env python3
"""brain-sync 공통 유틸 — 경로·frontmatter·슬러그·해시.

cruise 코드를 import하지 않는다. cruise 산출물은 CONTRACT.md (contract_version 1)
스키마만 보고 읽는다.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

CONTRACT_VERSION = 2          # 읽는 대상 cruise 계약 버전 (feature/worktree/issue_keys 포함)
VAULT_SCHEMA_VERSION = 2      # brain vault 스키마 버전 (features 노드 포함)
BRAIN_SYNC_VERSION = "0.2.0"

# 노드 타입 → vault 하위 폴더
NODE_FOLDERS = {
    "feature": "features",
    "work-item": "work-items",
    "pattern": "patterns",
    "decision": "decisions",
    "incident": "incidents",
    "technology": "technologies",
}

# source_hash 계산에 기여하는 cruise 산출물 (이 파일들이 바뀌면 재동기화)
SOURCE_FILES = ["task.md", "result.md", "summary.md", "pr.md", "commit.md"]

JIRA_KEY_RE = re.compile(r"^[A-Z]+-\d+$")


def tasks_root() -> Path:
    return Path(os.environ.get("CRUISE_TASKS_ROOT",
                               str(Path.home() / "Documents" / "tasks")))


def brain_root() -> Path:
    return Path(os.environ.get("BRAIN_ROOT",
                               str(Path.home() / "Documents" / "brain")))


def node_dir(node_type: str) -> Path:
    return brain_root() / NODE_FOLDERS[node_type]


def node_path(node_type: str, slug: str) -> Path:
    return node_dir(node_type) / f"{slug}.md"


def node_id(node_type: str, slug: str) -> str:
    return f"{NODE_FOLDERS[node_type]}/{slug}"


def manifest_path() -> Path:
    return brain_root() / "_manifest.json"


def meta_path() -> Path:
    return brain_root() / "_meta.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def require_yaml():
    if yaml is None:
        raise SystemExit(json.dumps(
            {"error": "MISSING_DEP", "detail": "PyYAML 필요: pip install pyyaml"}))


def slugify(text: str, fallback: str = "untitled") -> str:
    """ascii kebab 슬러그. 비ASCII 제거. 빈 결과는 fallback."""
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or fallback


def is_jira_key(key: str) -> bool:
    return bool(JIRA_KEY_RE.match(key))


def parse_frontmatter_scalars(path: Path) -> dict:
    """--- ... --- 사이 최상위 스칼라 라인만 (중첩/리스트 무시). cruise 산출물 읽기용."""
    if not path.exists():
        return {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    fm = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line[:1] in (" ", "\t"):
            continue
        m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        fm[key] = val
    return fm


def split_frontmatter(text: str):
    """(frontmatter_dict, body_str) 반환. brain 노드 파일 읽기용 (PyYAML)."""
    require_yaml()
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        return {}, text
    head = parts[0][3:]  # strip leading ---
    rest = parts[1]
    if rest.startswith("\n"):
        rest = rest[1:]
    # rest 시작이 줄바꿈 직후 본문. 첫 줄 '---' 잔여 제거
    body = rest.lstrip("\n")
    fm = yaml.safe_load(head) or {}
    return fm, body


def read_node(path: Path):
    if not path.exists():
        return None
    return split_frontmatter(path.read_text(encoding="utf-8"))


def write_node(path: Path, frontmatter: dict, body: str):
    require_yaml()
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).rstrip()
    body = (body or "").strip()
    path.write_text(f"---\n{fm}\n---\n\n{body}\n", encoding="utf-8")


def content_hash(payload) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def source_hash(task_dir: Path) -> str:
    h = hashlib.sha256()
    for name in SOURCE_FILES:
        p = task_dir / name
        if p.exists():
            h.update(name.encode("utf-8"))
            h.update(b"\0")
            h.update(p.read_bytes())
            h.update(b"\0")
    return "sha256:" + h.hexdigest()[:16]
