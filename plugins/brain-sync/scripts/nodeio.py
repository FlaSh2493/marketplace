#!/usr/bin/env python3
"""brain 노드 파일 멱등 read/merge/write (라이브러리).

sync.py가 본문·링크를 조립해서 넘기면, nodeio는 frontmatter 표준화·created 보존·
content_hash 기반 변경 감지·source_keys 병합·고아 archive 만 책임진다.
"""
import common as C


def _common_fm(node_type, slug, title, source_keys, created, status, links, tags, chash):
    return {
        "id": C.node_id(node_type, slug),
        "type": node_type,
        "title": title,
        "slug": slug,
        "status": status,
        "source_keys": sorted(set(source_keys)),
        "created": created,
        "updated": C.now_iso(),
        "brain_sync_version": C.BRAIN_SYNC_VERSION,
        "cruise_contract_version": C.CONTRACT_VERSION,
        "content_hash": chash,
        "links": sorted(set(links or [])),
        "tags": tags or [],
    }


def upsert(node_type, slug, title, extras, body, links, source_keys,
           status="active", tags=None, merge_source_keys=True):
    """노드를 생성/갱신.

    merge_source_keys=True: source_keys 를 기존 것과 합집합(공유 노드 머지; technology용).
    merge_source_keys=False: source_keys 를 주어진 값으로 **교체**(권위 멤버십; feature용).

    반환: (node_id, action)  action ∈ created | updated | unchanged
    """
    path = C.node_path(node_type, slug)
    nid = C.node_id(node_type, slug)
    existing = C.read_node(path)

    merged_keys = set(source_keys)
    created = C.now_iso()
    if existing:
        efm = existing[0]
        if merge_source_keys:
            merged_keys |= set(efm.get("source_keys", []))
        created = efm.get("created", created)

    payload = {
        "type": node_type, "slug": slug, "title": title,
        "extras": extras, "body": body.strip(),
        "links": sorted(set(links or [])),
        "source_keys": sorted(merged_keys), "status": status,
    }
    chash = C.content_hash(payload)

    if existing and existing[0].get("content_hash") == chash \
            and existing[0].get("status") == status:
        return nid, "unchanged"

    fm = _common_fm(node_type, slug, title, merged_keys, created, status,
                    links, tags, chash)
    fm.update(extras or {})
    # content_hash 는 frontmatter 변경(updated 등)과 무관하게 payload 기준이어야 하므로 마지막에 고정
    fm["content_hash"] = chash
    C.write_node(path, fm, body)
    return nid, ("updated" if existing else "created")


def remove_source_key(node_id: str, key: str):
    """노드에서 한 task 참조 제거. 비면 archive (하드삭제 안 함).

    반환: action ∈ updated | archived | unchanged | missing
    """
    folder, slug = node_id.split("/", 1)
    node_type = next((t for t, f in C.NODE_FOLDERS.items() if f == folder), None)
    if node_type is None:
        return "missing"
    path = C.node_path(node_type, slug)
    existing = C.read_node(path)
    if not existing:
        return "missing"
    fm, body = existing
    keys = [k for k in fm.get("source_keys", []) if k != key]
    if keys == fm.get("source_keys", []):
        return "unchanged"
    fm["source_keys"] = keys
    fm["updated"] = C.now_iso()
    if not keys:
        fm["status"] = "archived"
        C.write_node(path, fm, body)
        return "archived"
    C.write_node(path, fm, body)
    return "updated"
