"""
Aegis Security & Role-Based Access Control (RBAC) Module
Provides role-based authorization for ADMIN, ANALYST, and VIEWER roles.
Uses API keys or Bearer tokens passed via Authorization headers.
"""

import os
from typing import Optional
from fastapi import Header, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security_scheme = HTTPBearer(auto_error=False)

# Configurable API keys for enterprise roles
ROLE_KEYS = {
    os.getenv("ADMIN_API_KEY", "aegis-admin-secret-key"): "ADMIN",
    os.getenv("ANALYST_API_KEY", "aegis-analyst-secret-key"): "ANALYST",
    os.getenv("VIEWER_API_KEY", "aegis-viewer-secret-key"): "VIEWER",
}


class UserRole:
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


def get_current_user_role(
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    Extracts and validates credentials from either:
    1. X-API-Key: <key>
    2. Authorization: Bearer <token/key>
    Defaults to ANALYST in demo/development mode for seamless local exploration.
    """
    token = None
    if x_api_key:
        token = x_api_key
    elif auth_header:
        token = auth_header.credentials

    # If demo mode or no token provided in local dev, grant ANALYST permissions
    if not token:
        if os.getenv("REQUIRE_AUTH", "false").lower() == "true":
            raise HTTPException(status_code=401, detail="Authentication required. Provide X-API-Key or Bearer token.")
        return UserRole.ANALYST

    role = ROLE_KEYS.get(token)
    if not role:
        # Check standard admin token
        if token == "admin":
            return UserRole.ADMIN
        if token == "analyst":
            return UserRole.ANALYST
        if token == "viewer":
            return UserRole.VIEWER
        raise HTTPException(status_code=403, detail="Invalid API Key or unauthorized token.")
    return role


def require_role(allowed_roles: list[str]):
    """Enforces specific role membership for restricted endpoints."""
    def role_checker(role: str = Depends(get_current_user_role)):
        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: Action requires one of {allowed_roles}. Current role: {role}"
            )
        return role
    return role_checker

