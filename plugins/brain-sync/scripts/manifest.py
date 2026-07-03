#!/usr/bin/env python3
"""brain vault 매니페스트·메타 로드/저장 (멱등 원장).

_manifest.json:
{
  "version": 1,
  "tasks": { "<KEY>": {"source_hash","synced_at","outcome","nodes":[...]} },
  "tech_index": { "<tech-slug>": ["<KEY>", ...] }
}

_meta.json:
{ "vault_schema_version", "brain_sync_version", "cruise_contract_version",
  "last_sync", "counts": {...} }

CLI:
  python3 manifest.py --show          매니페스트 요약 JSON 출력
  python3 manifest.py --finalize      _meta.json 갱신 (last_sync, counts)
"""
import json
import sys

import common as C


def load_manifest() -> dict:
    p = C.manifest_path()
    if p.exists():
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            m = {}
    else:
        m = {}
    m.setdefault("version", 1)
    m.setdefault("tasks", {})
    m.setdefault("tech_index", {})
    m.setdefault("features", {})
    return m


def save_manifest(m: dict):
    p = C.manifest_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")


def load_meta() -> dict:
    p = C.meta_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_meta(meta: dict):
    p = C.meta_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def count_nodes() -> dict:
    counts = {}
    for ntype, folder in C.NODE_FOLDERS.items():
        d = C.brain_root() / folder
        counts[folder] = len(list(d.glob("*.md"))) if d.exists() else 0
    return counts


def finalize() -> dict:
    meta = load_meta()
    meta.update({
        "vault_schema_version": C.VAULT_SCHEMA_VERSION,
        "brain_sync_version": C.BRAIN_SYNC_VERSION,
        "cruise_contract_version": C.CONTRACT_VERSION,
        "last_sync": C.now_iso(),
        "counts": count_nodes(),
    })
    save_meta(meta)
    return meta


def summary() -> dict:
    m = load_manifest()
    assigned = sum(1 for t in m["tasks"].values() if t.get("feature"))
    unassigned = sum(1 for t in m["tasks"].values() if not t.get("feature"))
    return {
        "brain_root": str(C.brain_root()),
        "tasks_synced": len(m["tasks"]),
        "features": len(m["features"]),
        "tasks_assigned": assigned,
        "tasks_unassigned": unassigned,
        "technologies": len(m["tech_index"]),
        "counts": count_nodes(),
        "meta": load_meta(),
    }


def main():
    if "--finalize" in sys.argv:
        print(json.dumps(finalize(), ensure_ascii=False))
    else:
        print(json.dumps(summary(), ensure_ascii=False))


if __name__ == "__main__":
    main()
