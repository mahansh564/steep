from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_credentials(repo_root: Path) -> Credentials:
    cred_path = repo_root / "token.json"
    secret_path = repo_root / "credentials.json"
    creds: Credentials | None = None
    if cred_path.exists():
        creds = Credentials.from_authorized_user_file(str(cred_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not secret_path.exists():
                raise FileNotFoundError(
                    f"Missing {secret_path}. Download OAuth client JSON as credentials.json."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)
            creds = flow.run_local_server(port=0)
        cred_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def gmail_service(repo_root: Path):
    creds = get_credentials(repo_root)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)
