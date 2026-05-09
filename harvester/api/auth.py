"""Authentication dependency for Harvester API."""

from fastapi import Depends, Header, HTTPException, status

from harvester.api.settings import APISettings, get_api_settings


async def require_api_token(
    authorization: str = Header(default=""),
    settings: APISettings = Depends(get_api_settings),
) -> str:
    """Validate the API token from Authorization header.

    Returns the token value on success. Raises 401 on failure.
    """
    if not settings.api_token:
        return ""

    token = ""
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    if not token or token != settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
        )

    return token
