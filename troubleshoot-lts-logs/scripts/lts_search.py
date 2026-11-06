#!/usr/bin/env python3
"""Standalone, read-only CMCC LTS log search CLI.

Self-contained port of the lts-troubleshooter MCP server query path
(HMAC signing, config loading, log normalization, query validation).
Uses only the Python standard library; no MCP server required.

Credentials are resolved in this order:
  1. Environment variables (CMCC_AK, CMCC_SK, CMCC_PROJECT_ID, ...)
  2. File pointed to by --config / LTS_TROUBLESHOOTER_CONFIG
  3. ~/.config/lts-troubleshooter/credentials.env (or %APPDATA% on Windows)

Usage:
  lts_search.py groups
  lts_search.py search --group G --node N --start T1 --end T2 --keywords 'KWS' [--limit 100]
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import quote, unquote, urlsplit
from zoneinfo import ZoneInfo

ALGORITHM = "SDK-HMAC-SHA256"
SHANGHAI = ZoneInfo("Asia/Shanghai")
MAX_RANGE_MS = 2 * 60 * 60 * 1000

_HIGHLIGHT = re.compile(r"</?HighLightTag>")
_SECRET = re.compile(r"(?i)\b(authorization|cookie|password|secret|access[_-]?token)\b\s*[:=]\s*([^\s,;]+)")


class CliError(RuntimeError):
    pass


# ---------------------------------------------------------------- signing

def _encode(value: str) -> str:
    return quote(value, safe="~")


def sign_request(method: str, url: str, headers: dict[str, str], body: bytes, ak: str, sk: str) -> tuple[str, dict[str, str]]:
    """Return signed URL and headers using the same canonical form as apig_sdk."""
    parsed = urlsplit(url)
    signed = dict(headers)
    signed.setdefault("X-Sdk-Date", datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    signed.setdefault("host", parsed.netloc)
    canonical_path = "/".join(_encode(part) for part in unquote(parsed.path or "/").split("/"))
    if not canonical_path.endswith("/"):
        canonical_path += "/"
    query_parts: list[tuple[str, str]] = []
    if parsed.query:
        for part in parsed.query.split("&"):
            key, _, value = part.partition("=")
            query_parts.append((unquote(key), unquote(value)))
    canonical_query = "&".join(
        f"{_encode(k)}={_encode(v)}" for k, v in sorted(query_parts)
    )
    normalized = {key.lower(): str(value).strip() for key, value in signed.items()}
    signed_names = sorted(normalized)
    canonical_headers = "".join(f"{key}:{normalized[key]}\n" for key in signed_names)
    payload_hash = normalized.get("x-sdk-content-sha256") or hashlib.sha256(body).hexdigest()
    canonical_request = "\n".join((method.upper(), canonical_path, canonical_query, canonical_headers, ";".join(signed_names), payload_hash))
    request_hash = hashlib.sha256(canonical_request.encode()).hexdigest()
    string_to_sign = f"{ALGORITHM}\n{signed['X-Sdk-Date']}\n{request_hash}"
    signature = hmac.new(sk.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()
    signed["Authorization"] = f"{ALGORITHM} Access={ak}, SignedHeaders={';'.join(signed_names)}, Signature={signature}"
    signed["content-length"] = str(len(body))
    return url, signed


# ---------------------------------------------------------------- config

def default_config_path() -> Path:
    override = os.getenv("LTS_TROUBLESHOOTER_CONFIG", "").strip()
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = Path(os.getenv("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / "lts-troubleshooter" / "credentials.env"


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            raise CliError(f"invalid config line {number} in {path}")
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _json_map(raw: str, key: str) -> dict[str, str]:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise CliError(f"{key} must be a JSON object") from exc
    if not isinstance(value, dict):
        raise CliError(f"{key} must be a JSON object")
    return {str(k): str(v) for k, v in value.items()}


@dataclass(frozen=True)
class Settings:
    ak: str
    sk: str
    project_id: str
    group_map: dict[str, str]
    node_map: dict[str, str]
    base_url: str = "https://lts.cidc-rp-12.joint.cmecloud.cn"
    language: str = "zh-cn"
    timeout_seconds: float = 15.0

    @classmethod
    def load(cls, config_path: Path | None = None) -> "Settings":
        path = config_path or default_config_path()
        values = _read_env_file(path)
        for key in (
            "CMCC_AK", "CMCC_SK", "CMCC_PROJECT_ID", "CMCC_LTS_BASE_URL",
            "CMCC_X_LANGUAGE", "CMCC_HTTP_TIMEOUT_SEC", "CMCC_GROUP_LOG_GROUP_MAP",
            "CMCC_NODE_LOG_STREAM_MAP",
        ):
            if key in os.environ:
                values[key] = os.environ[key]
        required = ("CMCC_AK", "CMCC_SK", "CMCC_PROJECT_ID")
        missing = [key for key in required if not values.get(key, "").strip()]
        if missing:
            raise CliError(
                f"missing {', '.join(missing)}; set environment variables or configure {path}"
            )
        try:
            timeout = float(values.get("CMCC_HTTP_TIMEOUT_SEC", "15"))
        except ValueError as exc:
            raise CliError("CMCC_HTTP_TIMEOUT_SEC must be numeric") from exc
        return cls(
            ak=values["CMCC_AK"].strip(), sk=values["CMCC_SK"].strip(),
            project_id=values["CMCC_PROJECT_ID"].strip(),
            group_map=_json_map(values.get("CMCC_GROUP_LOG_GROUP_MAP", "{}"), "CMCC_GROUP_LOG_GROUP_MAP"),
            node_map=_json_map(values.get("CMCC_NODE_LOG_STREAM_MAP", "{}"), "CMCC_NODE_LOG_STREAM_MAP"),
            base_url=values.get("CMCC_LTS_BASE_URL", cls.base_url).rstrip("/"),
            language=values.get("CMCC_X_LANGUAGE", "zh-cn"), timeout_seconds=timeout,
        )


# ---------------------------------------------------------------- query

def parse_time(value: str) -> int:
    text = str(value).strip()
    if text.isdigit():
        number = int(text)
        if len(text) == 10:
            number *= 1000
        if number <= 0:
            raise CliError("time must be positive")
        return number
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CliError(f"invalid time {value!r}; use ISO-8601 or epoch milliseconds") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=SHANGHAI)
    return int(parsed.timestamp() * 1000)


def _normalize(item: dict[str, Any]) -> dict[str, Any]:
    labels = item.get("labels") if isinstance(item.get("labels"), dict) else {}
    content: dict[str, Any] = {}
    try:
        if isinstance(item.get("content"), str):
            parsed = json.loads(item["content"])
            content = parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    def value(key: str, default: Any = None) -> Any:
        return labels.get(key) or content.get(key) or default

    message = _HIGHLIGHT.sub("", str(value("message", "")))
    message = _SECRET.sub(lambda m: f"{m.group(1)}=<redacted>", message)
    message_truncated = len(message) > 8000
    if message_truncated:
        message = message[:8000] + "\n...[message truncated]"
    return {
        "time": _HIGHLIGHT.sub("", str(value("time", ""))) or None,
        "level": _HIGHLIGHT.sub("", str(value("level", ""))) or None,
        "TID": value("TID"), "lineNum": item.get("line_num"),
        "containerName": value("containerName"), "podName": value("podName"),
        "pathFile": value("pathFile"), "message": message,
        "messageTruncated": message_truncated,
    }


def query_logs(settings: Settings, *, group: str, node: str, start_ms: int, end_ms: int, keywords: str, limit: int) -> dict[str, Any]:
    group_id = settings.group_map.get(group)
    stream_id = settings.node_map.get(node)
    if not group_id:
        raise CliError(f"unknown group {group!r}; available: {sorted(settings.group_map)}")
    if not stream_id:
        raise CliError(f"unknown node {node!r}; available: {sorted(settings.node_map)}")
    url = (
        f"{settings.base_url}/v2/{settings.project_id}/groups/{group_id}"
        f"/streams/{stream_id}/content/query"
    )
    body = json.dumps({
        "start_time": str(start_ms), "end_time": str(end_ms), "keywords": keywords,
        "limit": limit, "highlight": False,
    }, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "X-Project-Id": settings.project_id,
        "X-Language": settings.language,
        "X-Sdk-Content-Sha256": "UNSIGNED-PAYLOAD",
    }
    signed_url, signed_headers = sign_request("POST", url, headers, body, settings.ak, settings.sk)
    request = urlrequest.Request(signed_url, data=body, headers=signed_headers, method="POST")
    try:
        with urlrequest.urlopen(request, timeout=settings.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        request_id = exc.headers.get("X-Request-Id", "unknown") if exc.headers else "unknown"
        raise CliError(f"LTS returned HTTP {exc.code} (requestId={request_id})") from exc
    except (urlerror.URLError, OSError, ValueError) as exc:
        raise CliError(f"LTS request failed: {type(exc).__name__}") from exc
    logs = [_normalize(item) for item in payload.get("logs", [])]
    return {
        "isQueryComplete": bool(payload.get("isQueryComplete", True)),
        "count": payload.get("count"),
        "logs": logs,
    }


def search(settings: Settings, *, group: str, node: str, start_time: str, end_time: str, keywords: str, limit: int) -> dict[str, Any]:
    group, node, keywords = group.strip(), node.strip(), keywords.strip()
    if not group or not node or not keywords:
        raise CliError("group, node and keywords are required")
    if not 1 <= limit <= 100:
        raise CliError("limit must be between 1 and 100")
    start_ms, end_ms = parse_time(start_time), parse_time(end_time)
    if end_ms <= start_ms:
        raise CliError("end_time must be later than start_time")
    if end_ms - start_ms > MAX_RANGE_MS:
        raise CliError("query range must not exceed 2 hours; narrow the time window")
    result = query_logs(settings, group=group, node=node, start_ms=start_ms, end_ms=end_ms, keywords=keywords, limit=limit)
    logs = result["logs"]
    truncated = len(logs) >= limit or not result["isQueryComplete"]
    return {
        "query": {"group": group, "node": node, "startTimeMs": str(start_ms), "endTimeMs": str(end_ms), "keywords": keywords, "limit": limit},
        "isQueryComplete": result["isQueryComplete"], "count": result.get("count"),
        "returned": len(logs), "truncated": truncated, "logs": logs,
        "nextAction": "Narrow the time range or keywords before querying again." if truncated else None,
    }


# ---------------------------------------------------------------- cli

def cmd_groups(settings: Settings | None, config_path: Path) -> dict[str, Any]:
    settings = settings or Settings.load(config_path)
    return {
        "configPath": str(default_config_path() if config_path is None else config_path),
        "credentialsOk": bool(settings.ak and settings.sk and settings.project_id),
        "groups": sorted(settings.group_map),
        "nodes": sorted(settings.node_map),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lts_search.py",
        description="Read-only CMCC LTS log search (standalone, no MCP server).",
    )
    parser.add_argument("--config", help="credentials.env path (default: $LTS_TROUBLESHOOTER_CONFIG or ~/.config/lts-troubleshooter/credentials.env)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("groups", help="list configured group/node names and check credentials")

    search_parser = subparsers.add_parser("search", help="query LTS logs")
    search_parser.add_argument("--group", required=True, help="log group name, e.g. robot-business")
    search_parser.add_argument("--node", required=True, help="log stream (node) name, e.g. robot-business-device")
    search_parser.add_argument("--start", required=True, help="ISO-8601 or epoch seconds/milliseconds; naive ISO is Asia/Shanghai")
    search_parser.add_argument("--end", required=True, help="same format as --start; window must be at most 2 hours")
    search_parser.add_argument("--keywords", required=True, help="LTS keyword expression; a bare TID also works")
    search_parser.add_argument("--limit", type=int, default=100, help="1-100, default 100")

    args = parser.parse_args(argv)
    config_path = Path(args.config).expanduser() if args.config else None
    try:
        if args.command == "groups":
            result = cmd_groups(None, config_path)  # type: ignore[arg-type]
            ok = result["credentialsOk"]
        else:
            result = search(Settings.load(config_path), group=args.group, node=args.node,
                            start_time=args.start, end_time=args.end,
                            keywords=args.keywords, limit=args.limit)
            ok = True
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
