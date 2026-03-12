"""Authentication API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from api.database import get_db
from ..repositories.auth_repository import AuthRepository
from ..schemas.auth import AuthResponse, LoginRequest, SignupRequest, UserOut
from ..services.auth_service import AuthService

router = APIRouter()


def get_auth_repo(conn=Depends(get_db)):
    """Dependency to get auth repository."""
    return AuthRepository(conn)


def get_auth_service(repo=Depends(get_auth_repo)):
    """Dependency to get auth service."""
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
def signup(payload: SignupRequest, service=Depends(get_auth_service)):
    """Create a new user account and return a bearer token."""
    return service.signup(
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, service=Depends(get_auth_service)):
    """Authenticate a user and return a bearer token."""
    return service.login(
        email=payload.email,
        password=payload.password,
    )


@router.get("/me", response_model=UserOut)
def me(current_user=Depends(get_current_user)):
    """Return the currently authenticated user."""
    return current_user