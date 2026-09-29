"""Per-account proxy resolution and rotating-gateway session pinning.

Proxy inventory comes from the user's config: `proxies` (newline separated,
one proxy per line) plus the legacy shared `proxy` fallback. Account *i*
uses line *i* when present, otherwise the fallback.

Two modes (`proxy_mode`):
- "static"   — each line is used verbatim (datacenter or dedicated
               residential proxy).
- "rotating" — a backconnect residential gateway whose exit IP rotates per
               request. Long-lived X sessions cannot survive that: every
               HTTP request would appear from a new address. For these lines
               the bot pins a provider-supported *sticky session* per account
               slot, so all requests of one account exit via one IP until the
               user rotates sessions (POST /api/proxy/rotate-sessions bumps
               the epoch → every slot gets a fresh session id → fresh IPs).

Sticky-session syntax: `-session-<id>` appended to the proxy *username*
(Smartproxy/IPRoyal/SOAX-style). Lines already containing a session marker
are used unchanged, letting operators encode provider-specific durations
(e.g. `-session-foo-sessionduration-30`) manually.
"""
from __future__ import annotations

import hashlib

MAX_PROXIES = 1000
MAX_PROXY_LINE = 512
SESSION_MARKER = "-session-"
_SCHEMES = ("http://", "https://", "socks5://", "socks5h://")


def _split_line(line: str) -> tuple:
    """(scheme, creds, host) for `[scheme://][creds@]host`. creds may be ""."""
    line = line.strip()
    for s in _SCHEMES:
        if line.startswith(s):
            rest = line[len(s):]
            break
    else:
        rest = line
    if "@" in rest:
        creds, host = rest.rsplit("@", 1)
    else:
        creds, host = "", rest
    return line[: len(line) - len(rest)], creds, host


def validate_proxy_line(line: str) -> None:
    """Reject malformed proxy lines early (raises ValueError)."""
    if not line or len(line) > MAX_PROXY_LINE:
        raise ValueError("proxy lines must be 1..512 characters")
    if any(c in line for c in " \t\r\n"):
        raise ValueError("proxy lines must not contain whitespace")
    scheme, _, host = _split_line(line)
    if scheme and scheme not in _SCHEMES:
        raise ValueError(f"unsupported proxy scheme: {scheme}")
    host = host.rstrip("/")
    # host should be `host[:port]` or `[v6]:port`; reject obvious junk
    if not host:
        raise ValueError("proxy host is empty")
    if host.count(":") > 1 and not host.startswith("["):
        raise ValueError("proxy host looks malformed")
    # username must be non-empty to pin sessions on rotating gateways;
    # empty creds are still valid for IP-authenticated static proxies.


def parse_proxy_list(text: str) -> list:
    """Non-empty validated lines from a proxies config blob."""
    out = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        validate_proxy_line(line)
        out.append(line)
    if len(out) > MAX_PROXIES:
        raise ValueError(f"too many proxies (max {MAX_PROXIES})")
    return out


def _session_id(epoch: int, slot: int) -> str:
    return hashlib.sha256(f"proxy-session:{epoch}:{slot}".encode()).hexdigest()[:16]


def _pin_session(proxy: str, epoch: int, slot: int) -> str:
    """Append a sticky-session suffix to the username, unless one exists."""
    scheme_and_rest = proxy
    for s in _SCHEMES:
        if proxy.startswith(s):
            scheme, scheme_and_rest = s, proxy[len(s):]
            break
    else:
        scheme = ""
    if "@" not in scheme_and_rest:
        return proxy  # no credentials to annotate (IP-allowlisted gateway)
    creds, host = scheme_and_rest.rsplit("@", 1)
    if SESSION_MARKER in creds:
        return proxy  # operator pinned their own session (maybe w/ duration)
    sid = _session_id(epoch, slot)
    return f"{scheme}{creds}{SESSION_MARKER}{sid}@{host}"


def _normalize(proxy: str) -> str:
    """curl_cffi's proxies dict wants scheme:// explicitly; default to http."""
    if "://" not in proxy:
        return "http://" + proxy
    return proxy


def resolve_for_account(cfg: dict, index: int) -> str:
    """Final proxy string for account slot `index` ('' = direct connection)."""
    try:
        proxies = parse_proxy_list(str(cfg.get("proxies", "") or ""))
    except ValueError:
        proxies = []
    if index < len(proxies):
        proxy = proxies[index]
    else:
        proxy = str(cfg.get("proxy", "") or "").strip()
        if not proxy:
            return ""
        try:
            validate_proxy_line(proxy)
        except ValueError:
            return ""
    mode = str(cfg.get("proxy_mode", "static"))
    # Preserve mapping stability: rotate epoch rotates every slot.
    if mode == "rotating":
        try:
            epoch = int(cfg.get("proxy_session_epoch", 0))
        except (TypeError, ValueError):
            epoch = 0
        proxy = _pin_session(proxy, epoch, index)
    return _normalize(proxy)


def resolve_for_fetch(cfg: dict) -> str:
    """Proxy for anonymous fetch paths (syndication / stock images).

    Rotating gateways are used *raw* here on purpose: a fresh exit IP per
    request is exactly what those rate-limited public endpoints call for.
    """
    try:
        proxies = parse_proxy_list(str(cfg.get("proxies", "") or ""))
    except ValueError:
        proxies = []
    proxy = proxies[0] if proxies else str(cfg.get("proxy", "") or "").strip()
    if not proxy:
        return ""
    try:
        validate_proxy_line(proxy)
    except ValueError:
        return ""
    return _normalize(proxy)
