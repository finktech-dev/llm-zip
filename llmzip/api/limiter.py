import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

_rpm = 60
_rpd = 10000


def set_limits(rpm: int, rpd: int) -> None:
    global _rpm, _rpd
    _rpm = rpm
    _rpd = rpd


def get_rpm_limit() -> str:
    return f"{_rpm}/minute"


def get_rpd_limit() -> str:
    return f"{_rpd}/day"


def _get_real_ip(request: Request) -> str:
    """Return the real client IP even behind nginx, traefik, or Docker's internal proxy.

    Without this, slowapi reads request.client.host which is the gateway IP
    (172.x.x.x or 127.0.0.1) in proxied deployments — every client appears
    identical and the rate limit exhausts for all of them simultaneously.

    X-Forwarded-For is only trusted when TRUST_PROXY_HEADERS=true is set in
    the environment. Do NOT enable this unless llm-zip sits behind a proxy that
    you control and that sets the header correctly — otherwise clients can
    spoof their IP and bypass rate limits entirely.
    """
    if os.environ.get("TRUST_PROXY_HEADERS", "").lower() == "true":
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can be a comma-separated list; the leftmost is the client.
            return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_get_real_ip, enabled=False)
