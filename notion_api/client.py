"""
Notion API クライアント
"""
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionClient:
    """Notion APIクライアント"""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict = None,
    ) -> dict | None:
        """APIリクエストを送信"""
        url = f"{NOTION_API_BASE}/{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Notion API エラー: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"レスポンス: {e.response.text}")
            return None

    def get_page(self, page_id: str) -> dict | None:
        """ページを取得"""
        return self._request("GET", f"pages/{page_id}")

    def get_database(self, database_id: str) -> dict | None:
        """データベースを取得"""
        return self._request("GET", f"databases/{database_id}")

    def query_database(
        self,
        database_id: str,
        filter: dict = None,
        sorts: list = None,
    ) -> list[dict]:
        """データベースをクエリ"""
        data = {}
        if filter:
            data["filter"] = filter
        if sorts:
            data["sorts"] = sorts

        result = self._request("POST", f"databases/{database_id}/query", data)
        if result:
            return result.get("results", [])
        return []

    def create_database(
        self,
        parent_page_id: str,
        title: str,
        properties: dict,
    ) -> dict | None:
        """データベースを作成"""
        data = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties,
        }
        return self._request("POST", "databases", data)

    def update_database(
        self,
        database_id: str,
        properties: dict = None,
        title: str = None,
    ) -> dict | None:
        """データベースを更新"""
        data = {}
        if properties:
            data["properties"] = properties
        if title:
            data["title"] = [{"type": "text", "text": {"content": title}}]
        
        return self._request("PATCH", f"databases/{database_id}", data)

    def create_page(
        self,
        database_id: str,
        properties: dict,
        content: list = None,
    ) -> dict | None:
        """ページ（レコード）を作成"""
        data = {
            "parent": {"type": "database_id", "database_id": database_id},
            "properties": properties,
        }
        if content:
            data["children"] = content
        
        return self._request("POST", "pages", data)

    def update_page(
        self,
        page_id: str,
        properties: dict,
    ) -> dict | None:
        """ページを更新"""
        return self._request("PATCH", f"pages/{page_id}", {"properties": properties})

    def verify_connection(self) -> bool:
        """接続を確認"""
        result = self._request("GET", "users/me")
        if result:
            logger.info(f"Notion接続成功: {result.get('name', 'Unknown')}")
            return True
        return False


