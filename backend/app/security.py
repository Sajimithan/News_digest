"""Security helpers for protecting external-facing API routes."""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from app.config import settings


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def _is_valid_api_key(candidate: str, allowed: tuple[str, ...]) -> bool:
    return any(hmac.compare_digest(candidate, key) for key in allowed)


async def require_external_api_key(
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
    authorization: str | None = Header(default=None),
) -> None:
    """
    Protect external endpoints with API key auth.

    Auth can be provided via either:
    - x-api-key: <key>
    - Authorization: Bearer <key>

    If EXTERNAL_API_KEYS is empty, auth is disabled for local/dev usage.
    """
    allowed = settings.EXTERNAL_API_KEYS
    if not allowed:
        return

    candidate = (x_api_key or "").strip() or (_extract_bearer_token(authorization) or "")
    if not candidate or not _is_valid_api_key(candidate, allowed):
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing API key.")
