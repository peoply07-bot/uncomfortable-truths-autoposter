import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials


def get_youtube_service():
    token_json = os.getenv("YOUTUBE_TOKEN_JSON", "")
    if not token_json:
        raise RuntimeError("Missing YOUTUBE_TOKEN_JSON secret")

    creds = Credentials.from_authorized_user_info(eval(token_json), scopes=[
        "https://www.googleapis.com/auth/youtube.upload"
    ])
    return build("youtube", "v3", credentials=creds)


def upload_short(video_path: str, title: str, description: str = "", tags=None):
    youtube = get_youtube_service()

    privacy = os.getenv("YT_PRIVACY", "private").strip().lower()
    if privacy not in ("private", "unlisted", "public"):
        privacy = "private"

    tags = tags or []

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(video_path, mimetype="video/*", resumable=True)

    req = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    res = req.execute()
    return res
