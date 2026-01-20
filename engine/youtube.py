import json
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def upload_short(video, title, description):
    creds = Credentials.from_authorized_user_info(
        json.loads(os.environ["YOUTUBE_TOKEN_JSON"]),
        SCOPES
    )

    yt = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:95],
            "description": description,
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(video, mimetype="video/mp4", resumable=True)
    yt.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    ).execute()
