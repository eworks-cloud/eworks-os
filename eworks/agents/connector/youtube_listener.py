"""
YouTube video comment listener.
"""
from __future__ import annotations
import os
import logging
from pathlib import Path


class YouTubeListener:
    def __init__(self):
        self.token_path = Path('config/youtube_token.json')
        self.logger = logging.getLogger(self.__class__.__name__)
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service
        if not self.token_path.exists():
            return None
        try:
            import json
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            token_data = json.loads(self.token_path.read_text())
            creds = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get(
                    'scopes', ['https://www.googleapis.com/auth/youtube.force-ssl']
                ),
            )
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            self._service = build('youtube', 'v3', credentials=creds)
            return self._service
        except Exception as e:
            self.logger.error('YouTube auth failed: %s', e)
            return None

    def get_recent_videos(self, max_results: int = 10) -> list[dict]:
        """Get recent uploaded videos."""
        svc = self._get_service()
        if not svc:
            return []
        try:
            ch = svc.channels().list(part='contentDetails', mine=True).execute()
            uploads_id = ch['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            pl = svc.playlistItems().list(
                part='snippet', playlistId=uploads_id, maxResults=max_results
            ).execute()
            return [
                {
                    'id': item['snippet']['resourceId']['videoId'],
                    'title': item['snippet']['title'],
                }
                for item in pl.get('items', [])
            ]
        except Exception as e:
            self.logger.error('YouTube videos fetch failed: %s', e)
            return []

    def get_comments(self, video_id: str, max_results: int = 50) -> list[dict]:
        """Get top-level comments on a video."""
        svc = self._get_service()
        if not svc:
            return []
        try:
            resp = svc.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=max_results,
                order='time',
            ).execute()
            comments = []
            for item in resp.get('items', []):
                top = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'id': item['id'],
                    'author_name': top.get('authorDisplayName', ''),
                    'author_id': top.get('authorChannelId', {}).get('value', ''),
                    'text': top.get('textDisplay', ''),
                    'published_at': top.get('publishedAt', ''),
                })
            return comments
        except Exception as e:
            self.logger.error('YouTube comments fetch failed: %s', e)
            return []

    def reply_to_comment(self, parent_id: str, text: str) -> dict:
        """Reply to a YouTube comment thread."""
        svc = self._get_service()
        if not svc:
            return {'status': 'needs_auth'}
        try:
            resp = svc.comments().insert(
                part='snippet',
                body={'snippet': {'parentId': parent_id, 'textOriginal': text[:10000]}}
            ).execute()
            return {'reply_id': resp.get('id', ''), 'status': 'replied'}
        except Exception as e:
            self.logger.error('YouTube reply failed: %s', e)
            return {'status': 'error', 'error': str(e)}

    def scan(self) -> list[dict]:
        """Full scan: get comments on recent videos."""
        videos = self.get_recent_videos(max_results=5)
        interactions = []
        for video in videos:
            video_id = video['id']
            comments = self.get_comments(video_id, max_results=20)
            for c in comments:
                interactions.append({
                    'platform': 'youtube',
                    'interaction_type': 'comment',
                    'external_id': c['id'],
                    'parent_id': video_id,
                    'author_id': c.get('author_id', ''),
                    'author_username': c.get('author_name', ''),
                    'author_name': c.get('author_name', ''),
                    'content': c.get('text', ''),
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                })
        return interactions
