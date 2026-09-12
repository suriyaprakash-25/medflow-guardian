import os
from slowapi import Limiter
from slowapi.util import get_remote_address

# In a real production deployment, if deployed behind a proxy,
# get_remote_address should ideally extract the X-Forwarded-For header correctly.
# SlowAPI defaults to Starlette's request.client.host, but can be configured.

def get_real_ip(request):
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    return get_remote_address(request)

is_testing = os.getenv("TESTING", "False") == "True"

limiter = Limiter(
    key_func=get_real_ip,
    default_limits=["1000/minute"],
    enabled=not is_testing
)
