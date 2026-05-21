import json
import sys
from base64 import b64encode
from pathlib import Path

import requests

from common import get_env, log_file

_session = None


def _get_session():
    global _session
    if _session is None:
        env = get_env()
        _session = requests.Session()
        creds = b64encode(f"{env['email']}:{env['token']}".encode()).decode()
        _session.headers.update({
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        _session.base_url = env["base_url"]
    return _session


def _url(path: str) -> str:
    s = _get_session()
    return f"{s.base_url}/rest/api/3/{path.lstrip('/')}"


def _log(key: str, msg: str):
    try:
        with open(log_file(key), "a") as f:
            from datetime import datetime
            f.write(f"[{datetime.utcnow().isoformat()}] {msg}\n")
    except Exception:
        pass


def _raise(resp, context: str, key: str = ""):
    msg = f"{context}: {resp.status_code} {resp.text[:200]}"
    if key:
        _log(key, msg)
    print(f"error: {context}: {resp.status_code}", file=sys.stderr)
    if resp.status_code == 400:
        try:
            errs = resp.json().get("errors", {})
            for field, err in errs.items():
                print(f"  {field}: {err}", file=sys.stderr)
        except Exception:
            pass
    sys.exit(1)


def get_issue(key: str) -> dict:
    resp = _get_session().get(_url(f"issue/{key}"), params={"expand": "editmeta,renderedFields"})
    if not resp.ok:
        _raise(resp, f"GET issue/{key}", key)
    return resp.json()


def get_editmeta(key: str) -> dict:
    resp = _get_session().get(_url(f"issue/{key}/editmeta"))
    if not resp.ok:
        return {}
    return resp.json().get("fields", {})


def search_issues(jql: str, fields: str = "*all") -> list[dict]:
    results = []
    start = 0
    while True:
        resp = _get_session().post(_url("search"), json={
            "jql": jql,
            "fields": fields.split(",") if "," in fields else [fields],
            "maxResults": 100,
            "startAt": start,
        })
        if not resp.ok:
            _raise(resp, f"search jql={jql[:60]}")
        data = resp.json()
        results.extend(data.get("issues", []))
        total = data.get("total", 0)
        start += len(data.get("issues", []))
        if start >= total:
            break
    return results


def list_transitions(key: str) -> list[dict]:
    resp = _get_session().get(_url(f"issue/{key}/transitions"))
    if not resp.ok:
        _raise(resp, f"GET transitions/{key}", key)
    return resp.json().get("transitions", [])


def transition_issue(key: str, status_name: str) -> bool:
    transitions = list_transitions(key)
    match = next((t for t in transitions if t["name"].lower() == status_name.lower()), None)
    if not match:
        available = ", ".join(t["name"] for t in transitions)
        print(f"error: status '{status_name}' not available. options: {available}", file=sys.stderr)
        sys.exit(1)
    resp = _get_session().post(_url(f"issue/{key}/transitions"), json={"transition": {"id": match["id"]}})
    if not resp.ok:
        _raise(resp, f"POST transition/{key}/{status_name}", key)
    _log(key, f"transitioned to '{status_name}'")
    return True


def update_issue(key: str, fields: dict) -> bool:
    if not fields:
        return False
    resp = _get_session().put(_url(f"issue/{key}"), json={"fields": fields})
    if not resp.ok:
        _raise(resp, f"PUT issue/{key}", key)
    _log(key, f"updated fields: {list(fields.keys())}")
    return True


def get_comments(key: str) -> list[dict]:
    resp = _get_session().get(_url(f"issue/{key}/comment"), params={"maxResults": 100})
    if not resp.ok:
        return []
    return resp.json().get("comments", [])


def add_comment(key: str, body_adf: dict) -> bool:
    resp = _get_session().post(_url(f"issue/{key}/comment"), json={"body": body_adf})
    if not resp.ok:
        _raise(resp, f"POST comment/{key}", key)
    _log(key, "added comment")
    return True


def get_worklogs(key: str) -> list[dict]:
    resp = _get_session().get(_url(f"issue/{key}/worklog"))
    if not resp.ok:
        return []
    return resp.json().get("worklogs", [])


def add_worklog(key: str, time_spent: str, comment: str = "") -> bool:
    payload = {"timeSpent": time_spent}
    if comment:
        payload["comment"] = {
            "type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}],
        }
    resp = _get_session().post(_url(f"issue/{key}/worklog"), json=payload)
    if not resp.ok:
        _raise(resp, f"POST worklog/{key}", key)
    _log(key, f"added worklog: {time_spent}")
    return True


def get_issue_links(key: str) -> list[dict]:
    issue = get_issue(key)
    return issue.get("fields", {}).get("issuelinks", [])


def add_issue_link(inward_key: str, outward_key: str, link_type: str = "Relates"):
    resp = _get_session().post(_url("issueLink"), json={
        "type": {"name": link_type},
        "inwardIssue": {"key": inward_key},
        "outwardIssue": {"key": outward_key},
    })
    if not resp.ok:
        _raise(resp, f"POST issueLink {inward_key}->{outward_key}")


def delete_issue_link(link_id: str):
    resp = _get_session().delete(_url(f"issueLink/{link_id}"))
    if not resp.ok:
        _raise(resp, f"DELETE issueLink/{link_id}")


def get_watchers(key: str) -> list[str]:
    resp = _get_session().get(_url(f"issue/{key}/watchers"))
    if not resp.ok:
        return []
    return [w.get("emailAddress", w.get("accountId", "")) for w in resp.json().get("watchers", [])]


def add_watcher(key: str, account_id: str):
    resp = _get_session().post(_url(f"issue/{key}/watchers"), json=account_id)
    if not resp.ok:
        _raise(resp, f"POST watcher/{key}")


def remove_watcher(key: str, account_id: str):
    resp = _get_session().delete(_url(f"issue/{key}/watchers"), params={"accountId": account_id})
    if not resp.ok:
        _raise(resp, f"DELETE watcher/{key}")


def lookup_account(email: str) -> str | None:
    resp = _get_session().get(_url("user/search"), params={"query": email})
    if not resp.ok or not resp.json():
        return None
    return resp.json()[0].get("accountId")
