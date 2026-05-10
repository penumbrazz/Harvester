"""Authentication dependency for Harvester API."""

from fastapi import Depends, Header, HTTPException, status

from harvester.api.settings import APISettings, get_api_settings

_Settings = Depends(get_api_settings)
_AuthHeader = Header(default="")


async def require_api_token(
    authorization: str = _AuthHeader,
    settings: APISettings = _Settings,
) -> str:
    """Validate the API token from Authorization header.

    Returns the token value on success. Raises 401 on failure.
    """
    if not settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="HARVESTER_API_TOKEN is not configured — mutating endpoints are disabled",
        )

    token = ""
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    if not token or token != settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
        )

    return token
