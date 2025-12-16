"""
Meta API 認証モジュール
"""
import logging
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.user import User

import config

logger = logging.getLogger(__name__)


class MetaAuth:
    """Meta API認証を管理するクラス"""

    def __init__(
        self,
        app_id: str = None,
        app_secret: str = None,
        access_token: str = None,
    ):
        self.app_id = app_id or config.META_APP_ID
        self.app_secret = app_secret or config.META_APP_SECRET
        self.access_token = access_token or config.META_ACCESS_TOKEN
        self.api = None
        self._initialized = False

    def initialize(self) -> bool:
        """
        Facebook Ads APIを初期化

        Returns:
            bool: 初期化成功したかどうか
        """
        if not self.access_token:
            logger.error("アクセストークンが設定されていません")
            return False

        try:
            self.api = FacebookAdsApi.init(
                app_id=self.app_id,
                app_secret=self.app_secret,
                access_token=self.access_token,
                api_version=config.META_API_VERSION,
            )
            self._initialized = True
            logger.info("Meta API を初期化しました")
            return True
        except Exception as e:
            logger.error(f"Meta API の初期化に失敗しました: {e}")
            return False

    def verify_token(self) -> dict | None:
        """
        アクセストークンを検証し、ユーザー情報を取得

        Returns:
            dict | None: ユーザー情報、または失敗時はNone
        """
        if not self._initialized:
            if not self.initialize():
                return None

        try:
            me = User(fbid="me")
            user_info = me.api_get(fields=["id", "name"])
            logger.info(f"認証成功: {user_info.get('name')} (ID: {user_info.get('id')})")
            return {
                "id": user_info.get("id"),
                "name": user_info.get("name"),
            }
        except Exception as e:
            logger.error(f"トークン検証に失敗しました: {e}")
            return None

    def get_ad_accounts(self) -> list[dict]:
        """
        アクセス可能な広告アカウント一覧を取得

        Returns:
            list[dict]: 広告アカウント情報のリスト
        """
        if not self._initialized:
            if not self.initialize():
                return []

        try:
            me = User(fbid="me")
            accounts = me.get_ad_accounts(fields=[
                "id",
                "name",
                "account_id",
                "account_status",
                "currency",
                "timezone_name",
                "amount_spent",
            ])

            result = []
            for account in accounts:
                result.append({
                    "id": account.get("id"),
                    "account_id": account.get("account_id"),
                    "name": account.get("name"),
                    "status": self._get_account_status_text(account.get("account_status")),
                    "currency": account.get("currency"),
                    "timezone": account.get("timezone_name"),
                    "total_spent": account.get("amount_spent"),
                })

            logger.info(f"{len(result)} 件の広告アカウントを取得しました")
            return result

        except Exception as e:
            logger.error(f"広告アカウントの取得に失敗しました: {e}")
            return []

    def get_ad_account(self, account_id: str) -> AdAccount | None:
        """
        指定した広告アカウントのオブジェクトを取得

        Args:
            account_id: 広告アカウントID（act_XXX形式）

        Returns:
            AdAccount | None: 広告アカウントオブジェクト
        """
        if not self._initialized:
            if not self.initialize():
                return None

        # act_ プレフィックスを追加
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"

        try:
            account = AdAccount(account_id)
            # アカウント情報を取得して存在確認
            account.api_get(fields=["id", "name"])
            return account
        except Exception as e:
            logger.error(f"広告アカウント {account_id} の取得に失敗しました: {e}")
            return None

    @staticmethod
    def _get_account_status_text(status: int) -> str:
        """アカウントステータスをテキストに変換"""
        status_map = {
            1: "ACTIVE",
            2: "DISABLED",
            3: "UNSETTLED",
            7: "PENDING_RISK_REVIEW",
            8: "PENDING_SETTLEMENT",
            9: "IN_GRACE_PERIOD",
            100: "PENDING_CLOSURE",
            101: "CLOSED",
            201: "ANY_ACTIVE",
            202: "ANY_CLOSED",
        }
        return status_map.get(status, f"UNKNOWN({status})")

    @property
    def is_initialized(self) -> bool:
        """初期化済みかどうか"""
        return self._initialized


