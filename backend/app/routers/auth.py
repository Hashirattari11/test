"""Auth routes: GitHub OAuth code exchange -> our session JWT."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..crypto import get_cipher
from ..db import db, fetch_one
from ..deps import get_current_user_id, issue_session_token, require_internal_secret
from ..github_client import GitHubError, exchange_code_for_token, get_authenticated_user
from ..schemas import AuthOut, GitHubCallbackIn, UserOut
from .consent import _user_out

router = APIRouter(prefix="/auth", tags=["auth"])

# Internal-only test identity. The public "demo account" has been removed —
# real users sign in with GitHub. This endpoint now requires the internal
# secret and is used solely for automated tests.
DEMO_EMAIL = "demo@autofix.app"


@router.get("/demo", response_model=AuthOut)
def demo_session(_: None = Depends(require_internal_secret)) -> AuthOut:
    """INTERNAL ONLY session (public demo removed).

    Requires `X-Internal-Secret`. Kept so automated tests can obtain a scoped
    session without GitHub; it is not reachable by the public frontend.
    """
    row = {
        "email": DEMO_EMAIL,
        "github_login": "demo",
    }
    res = db().table("users").upsert(row, on_conflict="email").execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create demo session")
    user = res.data[0]
    return AuthOut(token=issue_session_token(user["id"]), user=_user_out(user))


@router.post("/github/callback", response_model=AuthOut)
def github_callback(body: GitHubCallbackIn) -> AuthOut:
    """Exchange the OAuth code for a token, upsert the user, return a session JWT.

    The GitHub token is encrypted (Fernet) before it ever touches the database.
    """
    try:
        gh_token = exchange_code_for_token(body.code, body.redirect_uri)
        gh_user = get_authenticated_user(gh_token)
    except GitHubError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"{exc}; redirect_uri={body.redirect_uri!r}",
        )

    if not gh_user.get("email"):
        raise HTTPException(
            status_code=400,
            detail="No verified email available from GitHub. Verify your email and retry.",
        )

    encrypted = get_cipher().encrypt(gh_token)
    row = {
        "email": gh_user["email"],
        "github_id": gh_user["github_id"],
        "github_login": gh_user.get("github_login"),
        "github_access_token": encrypted,
    }
    res = db().table("users").upsert(row, on_conflict="github_id").execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to persist user")
    user = res.data[0]

    return AuthOut(
        token=issue_session_token(user["id"]),
        user=_user_out(user),
    )


@router.get("/me", response_model=UserOut)
def me(user_id: str = Depends(get_current_user_id)) -> UserOut:
    user = fetch_one("users", {"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_out(user)
