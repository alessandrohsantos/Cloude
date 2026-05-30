"""
Google OAuth2 flow for Gmail access.
"""
import json
import os
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

# In-memory session storage (use Redis/DB for production)
_sessions: dict[str, dict] = {}


def create_flow() -> Flow:
    return Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback"),
    )


def get_authorization_url() -> tuple[str, str]:
    """Returns (auth_url, state)."""
    flow = create_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url, state


def exchange_code(code: str, state: str) -> Credentials:
    """Exchange authorization code for credentials."""
    flow = create_flow()
    flow.fetch_token(code=code)
    return flow.credentials


def credentials_to_dict(creds: Credentials) -> dict:
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }


def credentials_from_dict(data: dict) -> Credentials:
    return Credentials(
        token=data["token"],
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id", os.getenv("GOOGLE_CLIENT_ID", "")),
        client_secret=data.get("client_secret", os.getenv("GOOGLE_CLIENT_SECRET", "")),
        scopes=data.get("scopes", SCOPES),
    )


def refresh_credentials(creds: Credentials) -> Credentials:
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def store_session(session_id: str, data: dict):
    _sessions[session_id] = data


def get_session(session_id: str) -> Optional[dict]:
    return _sessions.get(session_id)


def clear_session(session_id: str):
    _sessions.pop(session_id, None)
