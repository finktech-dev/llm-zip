from slowapi import Limiter
from slowapi.util import get_remote_address

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

limiter = Limiter(key_func=get_remote_address, enabled=False)
