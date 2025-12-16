"""
Notion データベース管理
"""
import logging
from typing import Any
from datetime import datetime

from .client import NotionClient

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Notionデータベースの管理を行うクラス"""

    def __init__(self, client: NotionClient):
        self.client = client

    # =========================================================================
    # 案件管理DB
    # =========================================================================
    
    def get_projects(self, status: str = None) -> list[dict]:
        """案件一覧を取得"""
        filter_obj = None
        if status:
            filter_obj = {
                "property": "ステータス",
                "select": {"equals": status}
            }
        
        results = self.client.query_database(
            database_id=self.projects_db_id,
            filter=filter_obj,
        )
        
        return [self._parse_project(r) for r in results]

    def get_project_by_account_id(self, account_id: str) -> dict | None:
        """広告アカウントIDで案件を取得"""
        results = self.client.query_database(
            database_id=self.projects_db_id,
            filter={
                "property": "広告アカウントID",
                "rich_text": {"equals": account_id}
            },
        )
        
        if results:
            return self._parse_project(results[0])
        return None

    def create_project(
        self,
        name: str,
        account_id: str,
        target_cpa: float = None,
        target_roas: float = None,
        **kwargs,
    ) -> dict | None:
        """案件を作成"""
        properties = {
            "案件名": {"title": [{"text": {"content": name}}]},
            "広告アカウントID": {"rich_text": [{"text": {"content": account_id}}]},
        }
        
        if target_cpa:
            properties["目標CPA"] = {"number": target_cpa}
        if target_roas:
            properties["目標ROAS"] = {"number": target_roas}
        if kwargs.get("article_url"):
            properties["記事URL"] = {"url": kwargs["article_url"]}
        if kwargs.get("lp_url"):
            properties["LP_URL"] = {"url": kwargs["lp_url"]}
        if kwargs.get("offer"):
            properties["オファー内容"] = {"rich_text": [{"text": {"content": kwargs["offer"]}}]}
        if kwargs.get("status"):
            properties["ステータス"] = {"select": {"name": kwargs["status"]}}
        if kwargs.get("memo"):
            properties["メモ"] = {"rich_text": [{"text": {"content": kwargs["memo"]}}]}

        return self.client.create_page(self.projects_db_id, properties)

    def _parse_project(self, page: dict) -> dict:
        """案件データをパース"""
        props = page.get("properties", {})
        return {
            "id": page.get("id"),
            "name": self._get_title(props.get("案件名")),
            "account_id": self._get_rich_text(props.get("広告アカウントID")),
            "target_cpa": self._get_number(props.get("目標CPA")),
            "target_roas": self._get_number(props.get("目標ROAS")),
            "article_url": self._get_url(props.get("記事URL")),
            "lp_url": self._get_url(props.get("LP_URL")),
            "offer": self._get_rich_text(props.get("オファー内容")),
            "status": self._get_select(props.get("ステータス")),
            "memo": self._get_rich_text(props.get("メモ")),
        }

    # =========================================================================
    # 運用ナレッジDB
    # =========================================================================
    
    def get_knowledge(self, category: str = None, importance: str = None) -> list[dict]:
        """運用ナレッジを取得"""
        filters = []
        if category:
            filters.append({
                "property": "カテゴリ",
                "select": {"equals": category}
            })
        if importance:
            filters.append({
                "property": "重要度",
                "select": {"equals": importance}
            })

        filter_obj = None
        if len(filters) == 1:
            filter_obj = filters[0]
        elif len(filters) > 1:
            filter_obj = {"and": filters}

        results = self.client.query_database(
            database_id=self.knowledge_db_id,
            filter=filter_obj,
        )
        
        return [self._parse_knowledge(r) for r in results]

    def create_knowledge(
        self,
        title: str,
        content: str,
        category: str = None,
        source: str = None,
        importance: str = None,
        url: str = None,
    ) -> dict | None:
        """運用ナレッジを作成"""
        properties = {
            "タイトル": {"title": [{"text": {"content": title}}]},
        }
        
        if category:
            properties["カテゴリ"] = {"select": {"name": category}}
        if source:
            properties["ソース"] = {"select": {"name": source}}
        if importance:
            properties["重要度"] = {"select": {"name": importance}}
        if url:
            properties["参照URL"] = {"url": url}

        # 本文をページコンテンツとして追加
        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                }
            }
        ]

        return self.client.create_page(self.knowledge_db_id, properties, children)

    def _parse_knowledge(self, page: dict) -> dict:
        """ナレッジデータをパース"""
        props = page.get("properties", {})
        return {
            "id": page.get("id"),
            "title": self._get_title(props.get("タイトル")),
            "category": self._get_select(props.get("カテゴリ")),
            "source": self._get_select(props.get("ソース")),
            "importance": self._get_select(props.get("重要度")),
            "url": self._get_url(props.get("参照URL")),
        }

    # =========================================================================
    # 運用ログDB
    # =========================================================================
    
    def get_operation_logs(self, days: int = 7) -> list[dict]:
        """運用ログを取得"""
        from datetime import timedelta
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        results = self.client.query_database(
            database_id=self.logs_db_id,
            filter={
                "property": "日付",
                "date": {"on_or_after": since}
            },
            sorts=[{"property": "日付", "direction": "descending"}],
        )
        
        return [self._parse_log(r) for r in results]

    def create_operation_log(
        self,
        title: str,
        action: str,
        reason: str,
        date: str = None,
    ) -> dict | None:
        """運用ログを作成"""
        properties = {
            "タイトル": {"title": [{"text": {"content": title}}]},
            "日付": {"date": {"start": date or datetime.now().strftime("%Y-%m-%d")}},
            "アクション": {"select": {"name": action}},
            "理由": {"rich_text": [{"text": {"content": reason}}]},
        }

        return self.client.create_page(self.logs_db_id, properties)

    def _parse_log(self, page: dict) -> dict:
        """ログデータをパース"""
        props = page.get("properties", {})
        return {
            "id": page.get("id"),
            "title": self._get_title(props.get("タイトル")),
            "date": self._get_date(props.get("日付")),
            "action": self._get_select(props.get("アクション")),
            "reason": self._get_rich_text(props.get("理由")),
            "result": self._get_rich_text(props.get("結果")),
        }

    # =========================================================================
    # ヘルパーメソッド
    # =========================================================================
    
    @staticmethod
    def _get_title(prop: dict) -> str:
        if not prop or not prop.get("title"):
            return ""
        titles = prop["title"]
        return "".join(t.get("plain_text", "") for t in titles)

    @staticmethod
    def _get_rich_text(prop: dict) -> str:
        if not prop or not prop.get("rich_text"):
            return ""
        texts = prop["rich_text"]
        return "".join(t.get("plain_text", "") for t in texts)

    @staticmethod
    def _get_number(prop: dict) -> float | None:
        if not prop:
            return None
        return prop.get("number")

    @staticmethod
    def _get_select(prop: dict) -> str | None:
        if not prop or not prop.get("select"):
            return None
        return prop["select"].get("name")

    @staticmethod
    def _get_url(prop: dict) -> str | None:
        if not prop:
            return None
        return prop.get("url")

    @staticmethod
    def _get_date(prop: dict) -> str | None:
        if not prop or not prop.get("date"):
            return None
        return prop["date"].get("start")


