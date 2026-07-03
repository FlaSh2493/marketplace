#!/usr/bin/env python3
"""한 task를 brain 노드로 멱등 변환·적재.

facts(결정적) + node plan(LLM 창의) 을 합쳐 노드를 쓰고 매니페스트를 갱신한다.

Usage:
  python3 sync.py <KEY> --auto             work-item 만 (결정적, LLM 없음)
  python3 sync.py <KEY> --plan <file.json> 전체 (work-item + 파생 + technology)
  python3 sync.py <KEY> --plan -           plan 을 stdin 으로
Output: JSON {key, source_hash, created, updated, unchanged, archived, nodes}
"""
import json
import sys
from pathlib import Path

import common as C
import manifest as M
import nodeio
from extract import extract_facts


def wl(node_id: str) -> str:
    return f"[[{node_id}]]"


def build_work_item(facts: dict, plan_wi: dict, link_ids: list, feature_id):
    ident = facts["identity"]
    exe = facts["execution"]
    res = facts["result"]
    key = facts["key"]

    title = (plan_wi.get("title") or ident.get("summary") or key).strip()
    background = plan_wi.get("background") or res.get("background") or ""
    goal = plan_wi.get("goal") or ""
    result_summary = plan_wi.get("result_summary") or res.get("result_text") or ""
    change_summary = plan_wi.get("change_summary") or ""
    if not change_summary and exe.get("files_changed") is not None:
        change_summary = (f"{exe.get('files_changed')} files changed, "
                          f"+{exe.get('insertions')} / -{exe.get('deletions')}")

    technologies = [C.slugify(t) for t in res.get("technologies", []) if t]

    extras = {
        "jira_key": key if ident.get("shape") == "jira" else None,
        "feature": feature_id or "unassigned",   # features/<slug> 또는 unassigned
        "outcome": res.get("outcome"),
        "branch": exe.get("branch") or "",
        "repo": exe.get("repo") or "",
        "base_branch": exe.get("base_branch") or "",
        "pr_url": exe.get("pr_url") or "",
        "pr_number": exe.get("pr_number"),
        "commits_count": exe.get("commits_count") or 0,
        "technologies": technologies,
    }

    # feature 링크는 권위값 있을 때만 links/본문에 포함
    all_links = ([feature_id] if feature_id else []) + link_ids

    parts = [f"# Work Item — {key}", ""]
    if feature_id:
        parts += ["## 상위 기능", "", f"- {wl(feature_id)}", ""]
    if background:
        parts += ["## 배경", "", background, ""]
    if goal:
        parts += ["## 목표", "", goal, ""]
    parts += ["## 결과", "", result_summary or "- 없음", ""]
    if change_summary:
        parts += ["## 변경 요약", "", change_summary, ""]
    parts += ["## 연결", ""]
    parts += [f"- {wl(i)}" for i in link_ids] if link_ids else ["- 없음"]
    body = "\n".join(parts)
    return title, extras, all_links, body, ("active" if res.get("outcome") != "abandoned"
                                            else "archived")


def build_feature_node(m: dict, fslug: str):
    """매니페스트 features 인덱스에서 feature 노드를 멱등 재빌드. 멤버 없으면 archive.

    반환: (feature_id, action)  action ∈ created | updated | unchanged | archived
    """
    fid = C.node_id("feature", fslug)
    finfo = m.get("features", {}).get(fslug, {})
    members = finfo.get("members", {})
    feature_branch = finfo.get("feature_branch", "") or fslug

    if not members:
        # 멤버 0 → archive (하드삭제 안 함). source_keys 교체 모드로 비움.
        _, act = nodeio.upsert("feature", fslug, feature_branch,
                               {"feature_branch": feature_branch, "kind": "",
                                "task_count": 0, "worktree_count": 0,
                                "tasks": [], "worktrees": []},
                               f"# Feature — {feature_branch}\n\n(archived: 멤버 없음)",
                               [], [], status="archived", merge_source_keys=False)
        return fid, ("archived" if act != "unchanged" else "unchanged")

    keys = sorted(members)
    worktrees = sorted({members[k]["worktree_name"] for k in keys
                        if members[k].get("worktree_name")})
    kinds = {members[k].get("worktree_kind") for k in keys}
    kind = "worktree" if "worktree" in kinds else ("branch" if "branch" in kinds else "")
    outcomes = {members[k].get("outcome") for k in keys}
    if outcomes <= {"merged"}:
        status = "merged"
    elif outcomes <= {"abandoned"}:
        status = "archived"
    else:
        status = "active"
    base_branch = next((members[k]["base_branch"] for k in keys
                        if members[k].get("base_branch")), "")
    repo = next((members[k]["repo"] for k in keys if members[k].get("repo")), "")

    link_ids = [C.node_id("work-item", k) for k in keys]
    extras = {
        "feature_branch": feature_branch,
        "kind": kind,
        "base_branch": base_branch,
        "repo": repo,
        "task_count": len(keys),
        "worktree_count": len(worktrees),
        "tasks": keys,
        "worktrees": worktrees,
    }
    parts = [f"# Feature — {feature_branch}", "",
             "## 기능 개요", "",
             f"- 브랜치: `{feature_branch}` / kind: {kind or '미상'}", "",
             f"## 구성 task ({len(keys)})", ""]
    parts += [f"- {wl(C.node_id('work-item', k))}" for k in keys]
    parts += ["", f"## 워크트리 ({len(worktrees)})", ""]
    parts += ([f"- {w}" for w in worktrees] if worktrees else ["- 미상"])
    body = "\n".join(parts)

    _, act = nodeio.upsert("feature", fslug, feature_branch, extras, body,
                           link_ids, keys, status=status, merge_source_keys=False)
    return fid, act


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "USAGE: sync.py <KEY> [--auto|--plan F]"}))
        sys.exit(1)
    key = sys.argv[1]
    auto = "--auto" in sys.argv
    plan = {}
    if "--plan" in sys.argv:
        i = sys.argv.index("--plan")
        src = sys.argv[i + 1] if i + 1 < len(sys.argv) else "-"
        raw = sys.stdin.read() if src == "-" else Path(src).read_text(encoding="utf-8")
        plan = json.loads(raw) if raw.strip() else {}

    tdir = C.tasks_root() / key
    if not tdir.exists():
        print(json.dumps({"error": "NO_TASK_DIR", "key": key}))
        sys.exit(1)

    facts = extract_facts(key)
    m = M.load_manifest()
    old_nodes = set(m["tasks"].get(key, {}).get("nodes", []))

    actions = {"created": [], "updated": [], "unchanged": [], "archived": []}
    new_nodes = []
    derived_link_ids = []

    # --- 파생 노드 슬러그/ID 선계산 (work-item 링크용) ---
    patterns = plan.get("patterns", []) if not auto else []
    decisions = plan.get("decisions", []) if not auto else []
    incidents = plan.get("incidents", []) if not auto else []
    technologies = plan.get("technologies", []) if not auto else []

    def reg(nid, action):
        actions[action].append(nid)
        if nid not in new_nodes:
            new_nodes.append(nid)

    # patterns (공유 가능)
    for p in patterns:
        slug = C.slugify(p.get("slug") or p.get("title"), fallback=f"{key}-pattern")
        nid = C.node_id("pattern", slug)
        derived_link_ids.append(nid)
        body = (f"# Pattern — {p.get('title','')}\n\n## 문제\n\n{p.get('problem','')}\n\n"
                f"## 해법\n\n{p.get('solution','')}\n\n{p.get('body','')}\n\n"
                f"## 출처\n\n- {wl(C.node_id('work-item', key))}")
        _, act = nodeio.upsert("pattern", slug, p.get("title", slug),
                               {"problem": p.get("problem", ""),
                                "solution": p.get("solution", "")},
                               body, [C.node_id("work-item", key)], [key])
        reg(nid, act)

    # decisions (task 국소)
    for d in decisions:
        slug = C.slugify(f"{key}-{d.get('name') or d.get('title')}",
                         fallback=f"{key}-decision")
        nid = C.node_id("decision", slug)
        derived_link_ids.append(nid)
        alts = d.get("alternatives", []) or []
        body = (f"# Decision — {d.get('title','')}\n\n## 결정\n\n{d.get('decision','')}\n\n"
                f"## 이유\n\n{d.get('rationale','')}\n\n## 기각된 대안\n\n"
                + ("\n".join(f"- {a}" for a in alts) if alts else "- 없음")
                + f"\n\n{d.get('body','')}\n\n## 출처\n\n- {wl(C.node_id('work-item', key))}")
        _, act = nodeio.upsert("decision", slug, d.get("title", slug),
                               {"decision": d.get("decision", ""),
                                "rationale": d.get("rationale", ""),
                                "alternatives": alts},
                               body, [C.node_id("work-item", key)], [key])
        reg(nid, act)

    # incidents (task 국소)
    for inc in incidents:
        slug = C.slugify(f"{key}-{inc.get('name') or inc.get('title')}",
                         fallback=f"{key}-incident")
        nid = C.node_id("incident", slug)
        derived_link_ids.append(nid)
        body = (f"# Incident — {inc.get('title','')}\n\n## 증상\n\n{inc.get('symptom','')}\n\n"
                f"## 원인\n\n{inc.get('cause','')}\n\n## 해결\n\n{inc.get('resolution','')}\n\n"
                f"## 출처\n\n- {wl(C.node_id('work-item', key))}")
        _, act = nodeio.upsert("incident", slug, inc.get("title", slug),
                               {"severity": inc.get("severity", ""),
                                "symptom": inc.get("symptom", ""),
                                "cause": inc.get("cause", ""),
                                "resolution": inc.get("resolution", "")},
                               body, [C.node_id("work-item", key)], [key])
        reg(nid, act)

    # technologies (공유 머지 노드)
    for t in technologies:
        slug = C.slugify(t.get("slug") or t.get("title"))
        if not slug or slug == "untitled":
            continue
        nid = C.node_id("technology", slug)
        derived_link_ids.append(nid)
        existing = C.read_node(C.node_path("technology", slug))
        usage_lines = {}
        if existing:
            for ln in existing[1].splitlines():
                s = ln.strip()
                if s.startswith("- [[work-items/"):
                    k = s.split("]]")[0].replace("- [[work-items/", "")
                    usage_lines[k] = s
        usage_lines[key] = f"- {wl(C.node_id('work-item', key))} — {t.get('usage','')}"
        body = (f"# Technology — {t.get('title', slug)}\n\n## 사용 이력\n\n"
                + "\n".join(usage_lines[k] for k in sorted(usage_lines)))
        _, act = nodeio.upsert("technology", slug, t.get("title", slug),
                               {"category": t.get("category", "")},
                               body, [], [key])
        reg(nid, act)
        m["tech_index"].setdefault(slug, [])
        if key not in m["tech_index"][slug]:
            m["tech_index"][slug].append(key)

    # --- feature 멤버십 (권위값만, 추측 없음) ---
    fdata = facts.get("feature", {})
    feature_slug = fdata.get("feature_slug")          # None = unassigned
    feature_id = C.node_id("feature", feature_slug) if feature_slug else None

    # --- work-item (허브) ---
    wi_id = C.node_id("work-item", key)
    title, extras, wi_links, body, status = build_work_item(
        facts, plan.get("work_item", {}), derived_link_ids, feature_id)
    _, act = nodeio.upsert("work-item", key, title, extras, body,
                           wi_links, [key], status=status)
    reg(wi_id, act)

    # --- feature 인덱스 갱신 + 멤버십 이동 처리 ---
    feats = m.setdefault("features", {})
    prev_feature = m["tasks"].get(key, {}).get("feature")   # 이전 동기화의 feature_slug
    member_rec = {
        "worktree_name": fdata.get("worktree_name") or "",
        "worktree_kind": fdata.get("worktree_kind") or "",
        "outcome": facts["result"].get("outcome") or "",
        "branch": facts["execution"].get("branch") or "",
        "base_branch": facts["execution"].get("base_branch") or "",
        "repo": facts["execution"].get("repo") or "",
    }
    affected = set()
    # 이전 feature에서 이동/이탈
    if prev_feature and prev_feature != feature_slug:
        if prev_feature in feats:
            feats[prev_feature].get("members", {}).pop(key, None)
            affected.add(prev_feature)
    # 현재 feature에 등록
    if feature_slug:
        f = feats.setdefault(feature_slug, {"feature_branch": fdata.get("feature_branch", ""),
                                            "members": {}})
        f["feature_branch"] = fdata.get("feature_branch", "") or f.get("feature_branch", "")
        f.setdefault("members", {})[key] = member_rec
        affected.add(feature_slug)

    # 영향받은 feature 노드 재빌드(멱등) / 비면 archive
    for fslug in affected:
        fid, fact = build_feature_node(m, fslug)
        if fact == "archived":
            actions["archived"].append(fid)
            feats.pop(fslug, None)
        elif fact in ("created", "updated"):
            actions[fact].append(fid)
        if fslug == feature_slug and feature_id:
            if feature_id not in new_nodes:
                new_nodes.append(feature_id)

    # --- 고아 처리: 이전엔 있었는데 이번엔 안 만든 노드 ---
    for nid in old_nodes - set(new_nodes):
        if nid.startswith("features/"):
            continue  # feature 노드는 위 멤버십 로직이 전담
        res = nodeio.remove_source_key(nid, key)
        if res == "archived":
            actions["archived"].append(nid)
        elif res == "updated":
            actions["updated"].append(nid)
        # tech_index 정리
        if nid.startswith("technologies/"):
            tslug = nid.split("/", 1)[1]
            if tslug in m["tech_index"] and key in m["tech_index"][tslug]:
                m["tech_index"][tslug].remove(key)
                if not m["tech_index"][tslug]:
                    del m["tech_index"][tslug]

    # --- 매니페스트 갱신 ---
    m["tasks"][key] = {
        "source_hash": C.source_hash(tdir),
        "synced_at": C.now_iso(),
        "outcome": facts["result"].get("outcome"),
        "feature": feature_slug,          # None = unassigned
        "nodes": sorted(new_nodes),
    }
    M.save_manifest(m)

    print(json.dumps({
        "key": key,
        "source_hash": m["tasks"][key]["source_hash"],
        "created": actions["created"],
        "updated": actions["updated"],
        "unchanged": actions["unchanged"],
        "archived": actions["archived"],
        "nodes": sorted(new_nodes),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
