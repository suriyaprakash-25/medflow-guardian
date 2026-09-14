"""Request-scoped identifiers used by authorization and audit persistence."""

from contextvars import ContextVar, Token


_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def bind_request_context(request_id: str, correlation_id: str) -> tuple[Token, Token]:
    return _request_id.set(request_id), _correlation_id.set(correlation_id)


def reset_request_context(tokens: tuple[Token, Token]) -> None:
    request_token, correlation_token = tokens
    _request_id.reset(request_token)
    _correlation_id.reset(correlation_token)


def get_request_id() -> str | None:
    return _request_id.get()


def get_correlation_id() -> str | None:
    return _correlation_id.get()
