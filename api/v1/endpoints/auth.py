"""Authentication API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from api.database import get_db
from ..repositories.audit_repository import AuditRepository
from ..repositories.auth_repository import AuthRepository
from ..schemas.auth import AuthResponse, LoginRequest, SignupRequest, UserOut
from ..services.auth_service import AuthService

router = APIRouter()


def get_audit_repo(conn=Depends(get_db)) -> AuditRepository:
    return AuditRepository(conn)


def get_auth_repo(conn=Depends(get_db)):
    return AuthRepository(conn)


def get_auth_service(repo=Depends(get_auth_repo)):
    return AuthService(repo)


def get_current_user(
    authorization: str | None = Header(default=None),
    service: AuthService = Depends(get_auth_service),
):
    """Extract and validate bearer token from Authorization header."""
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header.",
        )

    return service.get_current_user_from_token(token)


@router.post("/signup", response_model=AuthResponse)
def signup(
    payload: SignupRequest,
    service: AuthService = Depends(get_auth_service),
    audit_repo: AuditRepository = Depends(get_audit_repo),
):
    """Create a new user account and return a bearer token."""
    result = service.signup(
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
    )
    audit_repo.log(
        action="SIGNUP",
        resource_type="UserAccount",
        user_id=result["user"]["user_id"],
        resource_id=str(result["user"]["user_id"]),
        details={"email": result["user"]["email"], "full_name": result["user"]["full_name"]},
    )
    return result


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
    audit_repo: AuditRepository = Depends(get_audit_repo),
):
    """Authenticate a user and return a bearer token."""
    result = service.login(
        email=payload.email,
        password=payload.password,
    )
    audit_repo.log(
        action="LOGIN",
        resource_type="UserAccount",
        user_id=result["user"]["user_id"],
        resource_id=str(result["user"]["user_id"]),
    )
    return result


@router.get("/me", response_model=UserOut)
def me(current_user=Depends(get_current_user)):
    """Return the currently authenticated user."""
    return current_user
