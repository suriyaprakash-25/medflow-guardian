import ipaddress
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def _trusted_proxy_networks():
    """Compile configured trusted proxy CIDRs, ignoring invalid entries fail-safe."""
    networks = []
    for raw_cidr in settings.TRUSTED_PROXY_CIDRS:
        try:
            networks.append(ipaddress.ip_network(raw_cidr, strict=False))
        except ValueError:
            # A malformed trusted-proxy entry must never broaden trust.
            continue
    return networks


def _is_trusted_proxy(address, networks) -> bool:
    return any(address in network for network in networks)


def get_real_ip(request):
    """Return a rate-limit identity without trusting spoofable forwarded headers.

    ``X-Forwarded-For`` is honored only when the immediate TCP peer is in an
    explicitly configured trusted proxy network. The chain is then evaluated
    from right to left and stops at the nearest untrusted hop. Anything to the
    left of that hop is untrusted input and cannot override the rate-limit key.
    """
    peer_raw = get_remote_address(request)
    if not peer_raw:
        return "unknown"

    try:
        peer_ip = ipaddress.ip_address(peer_raw)
    except ValueError:
        return peer_raw

    trusted_networks = _trusted_proxy_networks()
    if not trusted_networks or not _is_trusted_proxy(peer_ip, trusted_networks):
        return str(peer_ip)

    forwarded_for = request.headers.get("x-forwarded-for")
    if not forwarded_for:
        return str(peer_ip)

    chain = []
    for raw_part in forwarded_for.split(","):
        part = raw_part.strip()
        if not part:
            return str(peer_ip)
        try:
            chain.append(ipaddress.ip_address(part))
        except ValueError:
            return str(peer_ip)

    for candidate in reversed(chain):
        if _is_trusted_proxy(candidate, trusted_networks):
            continue
        return str(candidate)

    # Every supplied hop is trusted. The leftmost trusted hop is the most
    # specific identity available; do not invent or trust another address.
    return str(chain[0]) if chain else str(peer_ip)


is_testing = os.getenv("TESTING", "False") == "True"

limiter = Limiter(
    key_func=get_real_ip,
    default_limits=["1000/minute"],
    enabled=not is_testing
)
