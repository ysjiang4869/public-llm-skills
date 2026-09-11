#!/usr/bin/env python3
"""Safe Apollo 2.2.x Portal Open API client for Agent Skills."""

import argparse
import hashlib
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request


class ApolloError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def env_default(name, fallback=None):
    return os.environ.get(name, fallback)


def digest(value):
    if value is None:
        return "missing"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def short_digest(value):
    full = digest(value)
    return full if full == "missing" else f"sha256:{full[:12]}"


def validate_portal_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ApolloError("APOLLO_PORTAL_URL must be an absolute http(s) URL")
    if parsed.username or parsed.password:
        raise ApolloError("credentials must not be embedded in APOLLO_PORTAL_URL")
    if parsed.query or parsed.fragment:
        raise ApolloError("APOLLO_PORTAL_URL must not contain query or fragment")
    return url.rstrip("/")


def path_segment(value):
    return urllib.parse.quote(str(value), safe="")


class ApolloClient:
    def __init__(self, base_url, token, timeout=10.0, ca_file=None):
        self.base_url = validate_portal_url(base_url)
        if not token:
            raise ApolloError("Apollo token environment variable is empty")
        self.token = token
        self.timeout = timeout
        self.ssl_context = ssl.create_default_context(cafile=ca_file) if ca_file else ssl.create_default_context()

    def request(self, method, path, query=None, body=None, allow_not_found=False):
        url = f"{self.base_url}/openapi/v1/{path.lstrip('/')}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        data = None
        headers = {
            "Authorization": self.token,
            "Accept": "application/json",
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": "public-llm-skills/apollo-config",
        }
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout, context=self.ssl_context) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            if allow_not_found and exc.code == 404:
                return None
            raw = exc.read(4096).decode("utf-8", errors="replace").strip()
            detail = raw or exc.reason
            raise ApolloError(f"Apollo Open API returned HTTP {exc.code}: {detail}", exc.code) from None
        except urllib.error.URLError as exc:
            raise ApolloError(f"failed to reach Apollo Portal: {exc.reason}") from None
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApolloError(f"Apollo returned an invalid JSON response: {exc}") from None


def target_path(args):
    values = (args.env, args.app, args.cluster, args.namespace)
    return "envs/{}/apps/{}/clusters/{}/namespaces/{}".format(*(path_segment(value) for value in values))


def namespaces_path(args):
    values = (args.env, args.app, args.cluster)
    return "envs/{}/apps/{}/clusters/{}/namespaces".format(
        *(path_segment(value) for value in values)
    )


def require_target(args):
    missing = [name for name in ("portal_url", "app", "env") if not getattr(args, name)]
    if missing:
        raise ApolloError("missing required setting(s): " + ", ".join(missing))


def require_operator(args):
    if not args.operator:
        raise ApolloError("write operations require --operator or APOLLO_OPERATOR")


def get_item(client, args, key):
    return client.request(
        "GET", f"{target_path(args)}/items/{path_segment(key)}", allow_not_found=True
    )


def list_draft_items(client, args):
    items = []
    page = 0
    size = 100
    while page < 10000:
        result = client.request("GET", f"{target_path(args)}/items", {"page": page, "size": size})
        content = result.get("content", []) if isinstance(result, dict) else result
        if not content:
            break
        items.extend(content)
        if isinstance(result, dict) and len(items) >= result.get("total", len(items)):
            break
        if len(content) < size:
            break
        page += 1
    else:
        raise ApolloError("item pagination exceeded the safety limit")
    return items


def latest_release(client, args):
    return client.request("GET", f"{target_path(args)}/releases/latest", allow_not_found=True)


def draft_map(client, args):
    return {item["key"]: item.get("value", "") for item in list_draft_items(client, args)}


def published_map(client, args):
    release = latest_release(client, args)
    return (release or {}).get("configurations", {}), release


def calculate_diff(draft, published):
    draft_keys = set(draft)
    published_keys = set(published)
    return {
        "added": sorted(draft_keys - published_keys),
        "changed": sorted(key for key in draft_keys & published_keys if draft[key] != published[key]),
        "removed": sorted(published_keys - draft_keys),
        "unchanged": sorted(key for key in draft_keys & published_keys if draft[key] == published[key]),
    }


def render_value(value, show_values):
    return value if show_values else short_digest(value)


def diff_output(draft, published, show_values=False):
    groups = calculate_diff(draft, published)
    details = {}
    for key in groups["added"]:
        details[key] = {"before": "missing", "after": render_value(draft[key], show_values)}
    for key in groups["changed"]:
        details[key] = {
            "before": render_value(published[key], show_values),
            "after": render_value(draft[key], show_values),
        }
    for key in groups["removed"]:
        details[key] = {"before": render_value(published[key], show_values), "after": "missing"}
    return {
        "counts": {name: len(groups[name]) for name in ("added", "changed", "removed", "unchanged")},
        "keys": {name: groups[name] for name in ("added", "changed", "removed")},
        "details": details,
    }


def read_value(args):
    sources = sum(
        (
            args.value is not None,
            args.value_stdin,
            args.value_env is not None,
            args.value_file is not None,
        )
    )
    if sources != 1:
        raise ApolloError(
            "set requires exactly one of --value, --value-stdin, --value-env, or --value-file"
        )
    if args.value is not None:
        return args.value
    if args.value_stdin:
        return sys.stdin.read()
    if args.value_env:
        if args.value_env not in os.environ:
            raise ApolloError(f"value environment variable is not set: {args.value_env}")
        return os.environ[args.value_env]
    try:
        with open(args.value_file, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise ApolloError(f"failed to read value file: {exc}") from None


def command_doctor(client, args):
    envclusters = client.request("GET", f"apps/{path_segment(args.app)}/envclusters")
    namespace = client.request("GET", target_path(args), allow_not_found=True)
    lock = client.request("GET", f"{target_path(args)}/lock", allow_not_found=True)
    return {
        "status": "ok" if namespace is not None else "target-not-found",
        "target": target_dict(args),
        "envclusters": envclusters,
        "namespaceFound": namespace is not None,
        "lock": lock,
    }


def command_namespaces(client, args):
    result = client.request("GET", namespaces_path(args))
    raw_namespaces = result.get("content", []) if isinstance(result, dict) else result
    if not isinstance(raw_namespaces, list):
        raise ApolloError("Apollo returned an invalid namespace list")
    namespaces = []
    for namespace in raw_namespaces:
        if not isinstance(namespace, dict):
            continue
        row = {
            key: namespace[key]
            for key in ("appId", "clusterName", "namespaceName", "comment", "format", "isPublic")
            if key in namespace
        }
        items = namespace.get("items") or []
        row["itemCount"] = len(items) if isinstance(items, list) else 0
        row["keys"] = sorted(
            str(item["key"])
            for item in items
            if isinstance(item, dict) and item.get("key") is not None
        )
        namespaces.append(row)
    return {
        "status": "ok",
        "target": cluster_target_dict(args),
        "namespaceCount": len(namespaces),
        "namespaces": namespaces,
    }


def command_get(client, args):
    if args.view == "draft":
        item = get_item(client, args, args.key)
        if item is None:
            raise ApolloError(f"configuration key not found in draft: {args.key}", 404)
        result = dict(item)
        result["value"] = render_value(item.get("value", ""), args.show_values)
        return {"status": "ok", "view": "draft", "target": target_dict(args), "item": result}
    configurations, release = published_map(client, args)
    if args.key not in configurations:
        raise ApolloError(f"configuration key not found in published release: {args.key}", 404)
    return {
        "status": "ok",
        "view": "published",
        "target": target_dict(args),
        "key": args.key,
        "value": render_value(configurations[args.key], args.show_values),
        "release": release_meta(release),
    }


def command_list(client, args):
    if args.view == "draft":
        items = list_draft_items(client, args)
        rendered = []
        for item in items:
            row = {key: value for key, value in item.items() if key != "value"}
            row["value"] = render_value(item.get("value", ""), args.show_values)
            rendered.append(row)
        return {"status": "ok", "view": "draft", "target": target_dict(args), "items": rendered}
    configurations, release = published_map(client, args)
    rendered = {key: render_value(value, args.show_values) for key, value in sorted(configurations.items())}
    return {
        "status": "ok",
        "view": "published",
        "target": target_dict(args),
        "configurations": rendered,
        "release": release_meta(release),
    }


def command_diff(client, args):
    draft = draft_map(client, args)
    published, release = published_map(client, args)
    return {
        "status": "ok",
        "target": target_dict(args),
        "baseRelease": release_meta(release),
        "diff": diff_output(draft, published, args.show_values),
    }


def command_set(client, args):
    require_operator(args)
    value = read_value(args)
    current = get_item(client, args, args.key)
    current_value = None if current is None else current.get("value", "")
    current_comment = "" if current is None else current.get("comment", "")
    comment = current_comment if args.comment is None else args.comment
    if args.expect_sha256 and digest(current_value) != args.expect_sha256:
        raise ApolloError("current value does not match --expect-sha256; refusing stale write")
    plan = {
        "operation": "set",
        "target": target_dict(args),
        "key": args.key,
        "create": current is None,
        "before": short_digest(current_value),
        "after": short_digest(value),
        "commentChanged": comment != current_comment,
    }
    if current_value == value and comment == current_comment:
        return {"status": "no-op", "plan": plan}
    if not args.apply:
        return {"status": "planned", "applyRequired": True, "plan": plan}
    body = {
        "key": args.key,
        "value": value,
        "comment": comment,
        "dataChangeLastModifiedBy": args.operator,
    }
    if current is None:
        body["dataChangeCreatedBy"] = args.operator
    client.request(
        "PUT",
        f"{target_path(args)}/items/{path_segment(args.key)}",
        {"createIfNotExists": "true"},
        body,
    )
    verified = get_item(client, args, args.key)
    if verified is None or verified.get("value", "") != value:
        raise ApolloError("write returned success but draft read-back did not match")
    return {"status": "applied", "plan": plan, "verified": True}


def command_publish(client, args):
    require_operator(args)
    draft = draft_map(client, args)
    published, release = published_map(client, args)
    changes = diff_output(draft, published, False)
    lock = client.request("GET", f"{target_path(args)}/lock", allow_not_found=True)
    plan = {
        "operation": "publish",
        "target": target_dict(args),
        "title": args.title,
        "baseRelease": release_meta(release),
        "lock": lock,
        "diff": changes,
    }
    changed_count = sum(changes["counts"][name] for name in ("added", "changed", "removed"))
    if changed_count == 0:
        return {"status": "no-op", "plan": plan}
    if isinstance(lock, dict) and lock.get("isLocked") and lock.get("lockedBy") == args.operator:
        raise ApolloError("namespace is locked by the publishing operator; Apollo may require a different publisher")
    if not args.apply:
        return {"status": "planned", "applyRequired": True, "plan": plan}
    created = client.request(
        "POST",
        f"{target_path(args)}/releases",
        body={"releaseTitle": args.title, "releaseComment": args.comment or "", "releasedBy": args.operator},
    )
    latest = latest_release(client, args)
    if latest is None:
        raise ApolloError("release returned success but releases/latest was not found")
    if created and created.get("id") and latest.get("id") and created["id"] != latest["id"]:
        raise ApolloError("latest release changed during verification; inspect Apollo before retrying")
    return {
        "status": "published",
        "plan": plan,
        "createdRelease": release_meta(created),
        "verifiedRelease": release_meta(latest),
    }


def target_dict(args):
    return {
        "portal": args.portal_url,
        "env": args.env,
        "appId": args.app,
        "cluster": args.cluster,
        "namespace": args.namespace,
    }


def cluster_target_dict(args):
    return {
        "portal": args.portal_url,
        "env": args.env,
        "appId": args.app,
        "cluster": args.cluster,
    }


def release_meta(release):
    if not release:
        return None
    return {
        key: release.get(key)
        for key in ("id", "name", "comment", "dataChangeCreatedBy", "dataChangeCreatedTime")
        if key in release
    }


def build_parser():
    parser = argparse.ArgumentParser(description="Safely manage Apollo configuration through Portal Open API")
    parser.add_argument("--portal-url", default=env_default("APOLLO_PORTAL_URL"))
    parser.add_argument("--token-env", default="APOLLO_OPENAPI_TOKEN")
    parser.add_argument("--app", default=env_default("APOLLO_APP_ID"))
    parser.add_argument("--env", default=env_default("APOLLO_ENV"))
    parser.add_argument("--cluster", default=env_default("APOLLO_CLUSTER", "default"))
    parser.add_argument("--namespace", default=env_default("APOLLO_NAMESPACE", "application"))
    parser.add_argument("--operator", default=env_default("APOLLO_OPERATOR"))
    parser.add_argument("--ca-file", default=env_default("APOLLO_CA_FILE"))
    parser.add_argument("--timeout", type=float, default=10.0)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="read-only connectivity and permission check")
    subparsers.add_parser("namespaces", help="list namespaces in the target cluster")

    get_parser = subparsers.add_parser("get", help="get one configuration key")
    get_parser.add_argument("key")
    get_parser.add_argument("--view", choices=("draft", "published"), default="draft")
    get_parser.add_argument("--show-values", action="store_true")

    list_parser = subparsers.add_parser("list", help="list namespace configuration")
    list_parser.add_argument("--view", choices=("draft", "published"), default="draft")
    list_parser.add_argument("--show-values", action="store_true")

    diff_parser = subparsers.add_parser("diff", help="compare draft with latest release")
    diff_parser.add_argument("--show-values", action="store_true")

    set_parser = subparsers.add_parser("set", help="create or update a draft item")
    set_parser.add_argument("key")
    set_parser.add_argument("--value", help="literal value; visible in command arguments")
    set_parser.add_argument("--value-stdin", action="store_true")
    set_parser.add_argument("--value-env")
    set_parser.add_argument("--value-file")
    set_parser.add_argument("--comment")
    set_parser.add_argument("--expect-sha256", help="full SHA-256 of current value, or 'missing'")
    set_parser.add_argument("--apply", action="store_true")

    publish_parser = subparsers.add_parser("publish", help="publish current namespace draft")
    publish_parser.add_argument("--title", required=True)
    publish_parser.add_argument("--comment")
    publish_parser.add_argument("--apply", action="store_true")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        require_target(args)
        token = os.environ.get(args.token_env, "")
        client = ApolloClient(
            args.portal_url,
            token,
            timeout=args.timeout,
            ca_file=args.ca_file,
        )
        handlers = {
            "doctor": command_doctor,
            "namespaces": command_namespaces,
            "get": command_get,
            "list": command_list,
            "diff": command_diff,
            "set": command_set,
            "publish": command_publish,
        }
        result = handlers[args.command](client, args)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    except ApolloError as exc:
        error = {"status": "error", "message": str(exc)}
        if exc.status is not None:
            error["httpStatus"] = exc.status
        print(json.dumps(error, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
