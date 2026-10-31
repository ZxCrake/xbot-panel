"""Per-account proxy resolution and rotating-gateway session pinning.

Proxy inventory comes from the user's config: `proxies` (newline separated,
one proxy per line) plus the legacy shared `proxy` fallback. Account *i*
uses line *i* when present, otherwise the fallback.

Two modes (`proxy_mode`):
- "static"   — each line is used verbatim (datacenter or dedicated
               residential proxy). One line per account is expected; accounts
               without a line fall back to `proxy` (or a direct connection).
- "rotating" — a backconnect residential gateway whose exit IP rotates per
               request. Long-lived X sessions cannot survive that: every
               HTTP request would appear from a new address. Lines are reused
               round-robin across accounts and each account slot gets its own
               provider-supported *sticky session*, so one gateway line can
               serve any number of accounts (one IP per account) until the
               user rotates sessions (POST /api/proxy/rotate-sessions bumps
               the epoch → every slot gets a fresh session id → fresh IPs).

Sticky-session syntax (`proxy_session_format`):
- "auto" (default) — DataImpulse gateways detected by host, else generic.
- "generic"        — `username-session-<id>:password@host`
                     (Smartproxy/IPRoyal/SOAX-style).
- "dataimpulse"    — `username;sessid.<id>:password@host` (DataImpulse docs).

The session id goes in the proxy *username*, never the password. Lines that
already contain a session marker (`-session-`, `;sessid.`, `__sessid.`) are
used unchanged, letting operators encode provider-specific durations
(e.g. `-session-foo-sessionduration-30`) manually.
"""
from __future__ import annotations

import hashlib

MAX_PROXIES = 1000
MAX_PROXY_LINE = 512
SESSION_MARKER = "-session-"
SESSION_MARKERS = ("-session-", ";sessid.", "__sessid.")
SESSION_FORMATS = ("auto", "generic", "dataimpulse")
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


def _pin_session(proxy: str, epoch: int, slot: int,
                 session_format: str = "auto") -> str:
    """Pin a sticky session on the proxy *username* (never the password).

    - generic:     `user-session-<id>:pass@host` (Smartproxy/IPRoyal/SOAX)
    - dataimpulse: `user;sessid.<id>:pass@host`  (DataImpulse docs)
    """
    scheme, creds, host = _split_line(proxy)
    if not creds:
        return proxy  # no credentials to annotate (IP-allowlisted gateway)
    if any(marker in creds for marker in SESSION_MARKERS):
        return proxy  # operator pinned their own session (maybe w/ duration)
    if session_format not in SESSION_FORMATS:
        session_format = "auto"
    if session_format == "auto":
        session_format = "dataimpulse" if "dataimpulse.com" in host.lower() else "generic"
    user, sep, password = creds.partition(":")
    sid = _session_id(epoch, slot)
    if session_format == "dataimpulse":
        user = f"{user};sessid.{sid}"
    else:
        user = f"{user}-session-{sid}"
    creds = f"{user}:{password}" if sep else user
    return f"{scheme}{creds}@{host}"


def _normalize(proxy: str) -> str:
    """curl_cffi's proxies dict wants scheme:// explicitly; default to http."""
    if "://" not in proxy:
        return "http://" + proxy
    return proxy


def resolve_for_account(cfg: dict, index: int) -> str:
    """Final proxy string for account slot `index` ('' = direct connection).

    Static mode keeps the historical one-line-per-account mapping. Rotating
    mode reuses the lines round-robin, because a backconnect gateway line is
    a slot pool, not a dedicated IP: the per-account session pin creates the
    distinct exit IP.
    """
    try:
        proxies = parse_proxy_list(str(cfg.get("proxies", "") or ""))
    except ValueError:
        proxies = []
    mode = str(cfg.get("proxy_mode", "static"))
    fallback = str(cfg.get("proxy", "") or "").strip()
    if not proxies:
        proxy = fallback
    elif mode == "rotating":
        proxy = proxies[index % len(proxies)]
    elif index < len(proxies):
        proxy = proxies[index]
    else:
        proxy = fallback
    if not proxy:
        return ""
    try:
        validate_proxy_line(proxy)
    except ValueError:
        return ""
    # Preserve mapping stability: rotate epoch rotates every slot.
    if mode == "rotating":
        try:
            epoch = int(cfg.get("proxy_session_epoch", 0))
        except (TypeError, ValueError):
            epoch = 0
        fmt = str(cfg.get("proxy_session_format", "auto") or "auto")
        proxy = _pin_session(proxy, epoch, index, fmt)
    return _normalize(proxy)


def coverage_error(cfg: dict, account_count: int) -> str:
    """Return an error when static proxy coverage is incomplete.

    Silent direct connections are dangerous: several accounts would share the
    server's public IP, which is exactly what gets them flagged. Rotating mode
    is exempt because lines are reused with one sticky session per account.
    """
    if str(cfg.get("proxy_mode", "static")) != "static":
        return ""
    try:
        proxies = parse_proxy_list(str(cfg.get("proxies", "") or ""))
    except ValueError:
        return "proxies: invalid proxy line"
    if not proxies or str(cfg.get("proxy", "") or "").strip():
        return ""
    if len(proxies) < account_count:
        return (f"{len(proxies)} proxy line(s) for {account_count} account(s) in "
                "static mode; add one line per account, set a fallback proxy, "
                "or switch to rotating mode")
    return ""


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
