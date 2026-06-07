from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def create_token_file(*, client_secret_file: Path, token_file: Path) -> Path:
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), SCOPES)
    credentials = flow.run_local_server(port=0)
    token_file.write_text(credentials.to_json(), encoding="utf-8")
    return token_file


def upload_video(
    video_path: Path,
    *,
    title: str,
    description: str,
    category_id: str,
    privacy_status: str,
) -> str:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    token_file = _token_file_from_env()
    credentials = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials.valid:
        raise RuntimeError("YouTube OAuth credentials are invalid. Refresh the token and try again.")

    youtube = build("youtube", "v3", credentials=credentials)
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": category_id,
        },
        "status": {"privacyStatus": privacy_status},
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = response["id"]
    return f"https://www.youtube.com/watch?v={video_id}"


def _token_file_from_env() -> Path:
    token_file = os.getenv("YOUTUBE_TOKEN_FILE")
    if token_file:
        return Path(token_file)

    token_json = os.getenv("YOUTUBE_TOKEN_JSON")
    if not token_json:
        raise RuntimeError("Set YOUTUBE_TOKEN_FILE or YOUTUBE_TOKEN_JSON before uploading.")

    parsed = json.loads(token_json)
    handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    with handle:
        json.dump(parsed, handle)
    return Path(handle.name)
