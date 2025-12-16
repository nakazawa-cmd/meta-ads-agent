"""
広告セット管理モジュール
"""
import logging
from typing import Any

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet

logger = logging.getLogger(__name__)


class AdSetManager:
    """広告セットの取得・操作を行うクラス"""

    def __init__(self, ad_account: AdAccount):
        self.ad_account = ad_account

    def get_adsets(
        self,
        campaign_id: str = None,
        status_filter: list[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        広告セット一覧を取得

        Args:
            campaign_id: キャンペーンIDでフィルタ（オプション）
            status_filter: ステータスでフィルタ (例: ["ACTIVE", "PAUSED"])
            limit: 取得件数上限

        Returns:
            list[dict]: 広告セット情報のリスト
        """
        try:
            params = {"limit": limit}
            filtering = []

            if status_filter:
                filtering.append({
                    "field": "effective_status",
                    "operator": "IN",
                    "value": status_filter,
                })

            if campaign_id:
                filtering.append({
                    "field": "campaign_id",
                    "operator": "EQUAL",
                    "value": campaign_id,
                })

            if filtering:
                params["filtering"] = filtering

            adsets = self.ad_account.get_ad_sets(
                fields=[
                    "id",
                    "name",
                    "campaign_id",
                    "status",
                    "effective_status",
                    "daily_budget",
                    "lifetime_budget",
                    "bid_amount",
                    "bid_strategy",
                    "billing_event",
                    "optimization_goal",
                    "targeting",
                    "created_time",
                    "updated_time",
                    "start_time",
                    "end_time",
                ],
                params=params,
            )

            result = []
            for adset in adsets:
                result.append({
                    "id": adset.get("id"),
                    "name": adset.get("name"),
                    "campaign_id": adset.get("campaign_id"),
                    "status": adset.get("status"),
                    "effective_status": adset.get("effective_status"),
                    "daily_budget": self._format_budget(adset.get("daily_budget")),
                    "lifetime_budget": self._format_budget(adset.get("lifetime_budget")),
                    "bid_amount": self._format_budget(adset.get("bid_amount")),
                    "bid_strategy": adset.get("bid_strategy"),
                    "billing_event": adset.get("billing_event"),
                    "optimization_goal": adset.get("optimization_goal"),
                    "targeting": adset.get("targeting"),
                    "created_time": adset.get("created_time"),
                    "updated_time": adset.get("updated_time"),
                    "start_time": adset.get("start_time"),
                    "end_time": adset.get("end_time"),
                })

            logger.info(f"{len(result)} 件の広告セットを取得しました")
            return result

        except Exception as e:
            logger.error(f"広告セットの取得に失敗しました: {e}")
            return []

    def get_adset(self, adset_id: str) -> dict[str, Any] | None:
        """
        特定の広告セットを取得

        Args:
            adset_id: 広告セットID

        Returns:
            dict | None: 広告セット情報
        """
        try:
            adset = AdSet(adset_id)
            data = adset.api_get(fields=[
                "id",
                "name",
                "campaign_id",
                "status",
                "effective_status",
                "daily_budget",
                "lifetime_budget",
                "bid_amount",
                "bid_strategy",
                "billing_event",
                "optimization_goal",
                "created_time",
                "updated_time",
            ])

            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "campaign_id": data.get("campaign_id"),
                "status": data.get("status"),
                "effective_status": data.get("effective_status"),
                "daily_budget": self._format_budget(data.get("daily_budget")),
                "lifetime_budget": self._format_budget(data.get("lifetime_budget")),
                "bid_amount": self._format_budget(data.get("bid_amount")),
                "bid_strategy": data.get("bid_strategy"),
                "billing_event": data.get("billing_event"),
                "optimization_goal": data.get("optimization_goal"),
                "created_time": data.get("created_time"),
                "updated_time": data.get("updated_time"),
            }

        except Exception as e:
            logger.error(f"広告セット {adset_id} の取得に失敗しました: {e}")
            return None

    def update_adset_status(self, adset_id: str, status: str) -> bool:
        """
        広告セットのステータスを更新

        Args:
            adset_id: 広告セットID
            status: 新しいステータス ("ACTIVE", "PAUSED")

        Returns:
            bool: 更新成功したかどうか
        """
        if status not in ["ACTIVE", "PAUSED"]:
            logger.error(f"無効なステータス: {status}")
            return False

        try:
            adset = AdSet(adset_id)
            adset.api_update(params={"status": status})
            logger.info(f"広告セット {adset_id} のステータスを {status} に更新しました")
            return True

        except Exception as e:
            logger.error(f"広告セット {adset_id} のステータス更新に失敗しました: {e}")
            return False

    def update_adset_bid(self, adset_id: str, bid_amount: int) -> bool:
        """
        広告セットの入札額を更新

        Args:
            adset_id: 広告セットID
            bid_amount: 入札額（円）

        Returns:
            bool: 更新成功したかどうか
        """
        try:
            adset = AdSet(adset_id)
            # Meta APIは最小通貨単位で指定
            adset.api_update(params={"bid_amount": bid_amount * 100})
            logger.info(f"広告セット {adset_id} の入札額を {bid_amount}円 に更新しました")
            return True

        except Exception as e:
            logger.error(f"広告セット {adset_id} の入札額更新に失敗しました: {e}")
            return False

    def update_adset_budget(
        self,
        adset_id: str,
        daily_budget: int = None,
        lifetime_budget: int = None,
    ) -> bool:
        """
        広告セットの予算を更新

        Args:
            adset_id: 広告セットID
            daily_budget: 日予算（円）
            lifetime_budget: 通算予算（円）

        Returns:
            bool: 更新成功したかどうか
        """
        try:
            adset = AdSet(adset_id)
            params = {}

            if daily_budget is not None:
                params["daily_budget"] = daily_budget * 100

            if lifetime_budget is not None:
                params["lifetime_budget"] = lifetime_budget * 100

            if not params:
                logger.warning("更新するパラメータがありません")
                return False

            adset.api_update(params=params)
            logger.info(f"広告セット {adset_id} の予算を更新しました: {params}")
            return True

        except Exception as e:
            logger.error(f"広告セット {adset_id} の予算更新に失敗しました: {e}")
            return False

    # =========================================================================
    # 広告セットの作成
    # =========================================================================

    def create_adset(
        self,
        campaign_id: str,
        name: str,
        daily_budget: int = None,
        lifetime_budget: int = None,
        optimization_goal: str = "LINK_CLICKS",
        billing_event: str = "IMPRESSIONS",
        bid_strategy: str = "LOWEST_COST_WITHOUT_CAP",
        targeting: dict = None,
        status: str = "PAUSED",
        start_time: str = None,
        end_time: str = None,
    ) -> dict | None:
        """
        広告セットを作成
        
        Args:
            campaign_id: 紐づけるキャンペーンID
            name: 広告セット名
            daily_budget: 日予算（円）
            lifetime_budget: 通算予算（円）
            optimization_goal: 最適化目標
                - LINK_CLICKS: リンククリック
                - IMPRESSIONS: インプレッション
                - REACH: リーチ
                - CONVERSIONS: コンバージョン
                - LANDING_PAGE_VIEWS: LP閲覧
            billing_event: 課金イベント（通常はIMPRESSIONS）
            bid_strategy: 入札戦略
                - LOWEST_COST_WITHOUT_CAP: 最小コスト（上限なし）
                - LOWEST_COST_WITH_BID_CAP: 最小コスト（入札上限あり）
                - COST_CAP: コスト上限
            targeting: ターゲティング設定
            status: 初期ステータス（PAUSED推奨）
            start_time: 開始日時（ISO8601形式）
            end_time: 終了日時（ISO8601形式）
        
        Returns:
            dict: 作成した広告セットの情報
        """
        try:
            params = {
                "campaign_id": campaign_id,
                "name": name,
                "optimization_goal": optimization_goal,
                "billing_event": billing_event,
                "bid_strategy": bid_strategy,
                "status": status,
            }
            
            # 予算設定
            if daily_budget:
                params["daily_budget"] = daily_budget * 100  # 円→セント変換
            elif lifetime_budget:
                params["lifetime_budget"] = lifetime_budget * 100
            else:
                # デフォルトで日予算1000円
                params["daily_budget"] = 100000
            
            # ターゲティング設定
            if targeting:
                params["targeting"] = targeting
            else:
                # デフォルトターゲティング（日本、18-65歳）
                params["targeting"] = {
                    "geo_locations": {
                        "countries": ["JP"],
                    },
                    "age_min": 18,
                    "age_max": 65,
                }
            
            # 日時設定
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time
            
            adset = self.ad_account.create_ad_set(params=params)
            
            result = {
                "id": adset.get("id"),
                "name": name,
                "campaign_id": campaign_id,
            }
            
            logger.info(f"広告セットを作成しました: {name}")
            return result
            
        except Exception as e:
            logger.error(f"広告セット作成エラー: {e}")
            return None

    def duplicate_adset(
        self,
        adset_id: str,
        new_name: str = None,
        campaign_id: str = None,
    ) -> dict | None:
        """
        既存の広告セットを複製
        
        Args:
            adset_id: 複製元の広告セットID
            new_name: 新しい名前（省略時は元の名前 + " (Copy)"）
            campaign_id: 別のキャンペーンに複製する場合のキャンペーンID
        
        Returns:
            dict: 複製した広告セットの情報
        """
        try:
            # 元の広告セットを取得
            original = self.get_adset(adset_id)
            if not original:
                return None
            
            # 複製パラメータを準備
            params = {
                "campaign_id": campaign_id or original.get("campaign_id"),
                "name": new_name or f"{original.get('name', 'AdSet')} (Copy)",
                "status": "PAUSED",  # 複製は一旦停止状態で作成
            }
            
            # 予算をコピー
            if original.get("daily_budget"):
                params["daily_budget"] = int(original["daily_budget"] * 100)
            elif original.get("lifetime_budget"):
                params["lifetime_budget"] = int(original["lifetime_budget"] * 100)
            
            # その他の設定をコピー
            if original.get("optimization_goal"):
                params["optimization_goal"] = original["optimization_goal"]
            if original.get("billing_event"):
                params["billing_event"] = original["billing_event"]
            if original.get("bid_strategy"):
                params["bid_strategy"] = original["bid_strategy"]
            
            # ターゲティングをコピー（別途取得が必要）
            adset_full = AdSet(adset_id)
            adset_data = adset_full.api_get(fields=["targeting"])
            if adset_data.get("targeting"):
                params["targeting"] = adset_data["targeting"]
            
            # 作成
            new_adset = self.ad_account.create_ad_set(params=params)
            
            result = {
                "id": new_adset.get("id"),
                "name": params["name"],
                "original_id": adset_id,
            }
            
            logger.info(f"広告セットを複製しました: {params['name']}")
            return result
            
        except Exception as e:
            logger.error(f"広告セット複製エラー: {e}")
            return None

    @staticmethod
    def _format_budget(budget_value: str | None) -> float | None:
        """予算値をフォーマット（100で割って実際の金額に）"""
        if budget_value is None:
            return None
        try:
            return float(budget_value) / 100
        except (ValueError, TypeError):
            return None


