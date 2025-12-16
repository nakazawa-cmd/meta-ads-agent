"""
キャンペーン管理モジュール
"""
import logging
from typing import Any

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign

logger = logging.getLogger(__name__)


class CampaignManager:
    """キャンペーンの取得・操作を行うクラス"""

    def __init__(self, ad_account: AdAccount):
        self.ad_account = ad_account

    def get_campaigns(
        self,
        status_filter: list[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        キャンペーン一覧を取得

        Args:
            status_filter: ステータスでフィルタ (例: ["ACTIVE", "PAUSED"])
            limit: 取得件数上限

        Returns:
            list[dict]: キャンペーン情報のリスト
        """
        try:
            params = {"limit": limit}
            
            if status_filter:
                params["filtering"] = [
                    {"field": "effective_status", "operator": "IN", "value": status_filter}
                ]

            campaigns = self.ad_account.get_campaigns(
                fields=[
                    "id",
                    "name",
                    "status",
                    "effective_status",
                    "objective",
                    "daily_budget",
                    "lifetime_budget",
                    "budget_remaining",
                    "created_time",
                    "updated_time",
                    "start_time",
                    "stop_time",
                    "smart_promotion_type",  # ASC判定用
                    "special_ad_categories",
                ],
                params=params,
            )

            result = []
            for campaign in campaigns:
                result.append({
                    "id": campaign.get("id"),
                    "name": campaign.get("name"),
                    "status": campaign.get("status"),
                    "effective_status": campaign.get("effective_status"),
                    "objective": campaign.get("objective"),
                    "daily_budget": self._format_budget(campaign.get("daily_budget")),
                    "lifetime_budget": self._format_budget(campaign.get("lifetime_budget")),
                    "budget_remaining": self._format_budget(campaign.get("budget_remaining")),
                    "created_time": campaign.get("created_time"),
                    "updated_time": campaign.get("updated_time"),
                    "start_time": campaign.get("start_time"),
                    "stop_time": campaign.get("stop_time"),
                    "smart_promotion_type": campaign.get("smart_promotion_type"),  # ASC判定
                    "is_asc": campaign.get("smart_promotion_type") == "ADVANTAGE_PLUS_SHOPPING",
                })

            logger.info(f"{len(result)} 件のキャンペーンを取得しました")
            return result

        except Exception as e:
            logger.error(f"キャンペーンの取得に失敗しました: {e}")
            return []

    def get_campaign(self, campaign_id: str) -> dict[str, Any] | None:
        """
        特定のキャンペーンを取得

        Args:
            campaign_id: キャンペーンID

        Returns:
            dict | None: キャンペーン情報
        """
        try:
            campaign = Campaign(campaign_id)
            data = campaign.api_get(fields=[
                "id",
                "name",
                "status",
                "effective_status",
                "objective",
                "daily_budget",
                "lifetime_budget",
                "budget_remaining",
                "created_time",
                "updated_time",
            ])

            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "status": data.get("status"),
                "effective_status": data.get("effective_status"),
                "objective": data.get("objective"),
                "daily_budget": self._format_budget(data.get("daily_budget")),
                "lifetime_budget": self._format_budget(data.get("lifetime_budget")),
                "budget_remaining": self._format_budget(data.get("budget_remaining")),
                "created_time": data.get("created_time"),
                "updated_time": data.get("updated_time"),
            }

        except Exception as e:
            logger.error(f"キャンペーン {campaign_id} の取得に失敗しました: {e}")
            return None

    def update_campaign_status(self, campaign_id: str, status: str) -> bool:
        """
        キャンペーンのステータスを更新

        Args:
            campaign_id: キャンペーンID
            status: 新しいステータス ("ACTIVE", "PAUSED")

        Returns:
            bool: 更新成功したかどうか
        """
        if status not in ["ACTIVE", "PAUSED"]:
            logger.error(f"無効なステータス: {status}")
            return False

        try:
            campaign = Campaign(campaign_id)
            campaign.api_update(params={"status": status})
            logger.info(f"キャンペーン {campaign_id} のステータスを {status} に更新しました")
            return True

        except Exception as e:
            logger.error(f"キャンペーン {campaign_id} のステータス更新に失敗しました: {e}")
            return False

    def update_campaign_budget(
        self,
        campaign_id: str,
        daily_budget: int = None,
        lifetime_budget: int = None,
    ) -> bool:
        """
        キャンペーンの予算を更新

        Args:
            campaign_id: キャンペーンID
            daily_budget: 日予算（円、100倍して設定）
            lifetime_budget: 通算予算（円、100倍して設定）

        Returns:
            bool: 更新成功したかどうか
        """
        try:
            campaign = Campaign(campaign_id)
            params = {}

            if daily_budget is not None:
                # Meta APIは最小通貨単位（円の場合は1円）で指定
                # ただし、内部的には100倍されることがあるので注意
                params["daily_budget"] = daily_budget * 100

            if lifetime_budget is not None:
                params["lifetime_budget"] = lifetime_budget * 100

            if not params:
                logger.warning("更新するパラメータがありません")
                return False

            campaign.api_update(params=params)
            logger.info(f"キャンペーン {campaign_id} の予算を更新しました: {params}")
            return True

        except Exception as e:
            logger.error(f"キャンペーン {campaign_id} の予算更新に失敗しました: {e}")
            return False

    # =========================================================================
    # キャンペーンの作成・複製
    # =========================================================================

    def create_campaign(
        self,
        name: str,
        objective: str = "OUTCOME_TRAFFIC",
        status: str = "PAUSED",
        daily_budget: int = None,
        lifetime_budget: int = None,
        special_ad_categories: list = None,
    ) -> dict | None:
        """
        キャンペーンを作成
        
        Args:
            name: キャンペーン名
            objective: キャンペーン目的
                - OUTCOME_TRAFFIC: トラフィック
                - OUTCOME_ENGAGEMENT: エンゲージメント
                - OUTCOME_LEADS: リード
                - OUTCOME_SALES: 売上
                - OUTCOME_APP_PROMOTION: アプリ
                - OUTCOME_AWARENESS: 認知
            status: 初期ステータス（PAUSED推奨）
            daily_budget: 日予算（円）- CBO使用時
            lifetime_budget: 通算予算（円）- CBO使用時
            special_ad_categories: 特別広告カテゴリ（HOUSING, EMPLOYMENT, CREDIT等）
        
        Returns:
            dict: 作成したキャンペーンの情報
        """
        try:
            params = {
                "name": name,
                "objective": objective,
                "status": status,
            }
            
            # 特別広告カテゴリ
            if special_ad_categories:
                params["special_ad_categories"] = special_ad_categories
            else:
                params["special_ad_categories"] = []  # 必須フィールド
            
            # CBO（キャンペーン予算最適化）を使用する場合
            if daily_budget or lifetime_budget:
                params["campaign_budget_optimization"] = True
                if daily_budget:
                    params["daily_budget"] = daily_budget * 100
                elif lifetime_budget:
                    params["lifetime_budget"] = lifetime_budget * 100
            
            campaign = self.ad_account.create_campaign(params=params)
            
            result = {
                "id": campaign.get("id"),
                "name": name,
                "objective": objective,
            }
            
            logger.info(f"キャンペーンを作成しました: {name}")
            return result
            
        except Exception as e:
            logger.error(f"キャンペーン作成エラー: {e}")
            return None

    def duplicate_campaign(
        self,
        campaign_id: str,
        new_name: str = None,
        copy_adsets: bool = True,
        copy_ads: bool = True,
    ) -> dict | None:
        """
        既存のキャンペーンを複製
        
        Args:
            campaign_id: 複製元のキャンペーンID
            new_name: 新しい名前（省略時は元の名前 + " (Copy)"）
            copy_adsets: 広告セットも複製するか
            copy_ads: 広告も複製するか
        
        Returns:
            dict: 複製したキャンペーンの情報
        """
        try:
            # 元のキャンペーンを取得
            original = self.get_campaign(campaign_id)
            if not original:
                return None
            
            # 新しいキャンペーンを作成
            new_campaign = self.create_campaign(
                name=new_name or f"{original.get('name', 'Campaign')} (Copy)",
                objective=original.get("objective", "OUTCOME_TRAFFIC"),
                status="PAUSED",
                daily_budget=original.get("daily_budget"),
                lifetime_budget=original.get("lifetime_budget"),
            )
            
            if not new_campaign:
                return None
            
            result = {
                "id": new_campaign["id"],
                "name": new_campaign["name"],
                "original_id": campaign_id,
                "copied_adsets": [],
                "copied_ads": [],
            }
            
            # 広告セットと広告の複製
            if copy_adsets:
                from meta_api.adsets import AdSetManager
                from meta_api.ads import AdManager
                
                adset_manager = AdSetManager(self.ad_account)
                ad_manager = AdManager(self.ad_account)
                
                # 元のキャンペーンの広告セットを取得
                original_adsets = adset_manager.get_adsets(campaign_id=campaign_id)
                
                for orig_adset in original_adsets:
                    # 広告セットを複製
                    new_adset = adset_manager.duplicate_adset(
                        adset_id=orig_adset["id"],
                        campaign_id=new_campaign["id"],
                    )
                    
                    if new_adset:
                        result["copied_adsets"].append(new_adset)
                        
                        # 広告も複製
                        if copy_ads:
                            original_ads = ad_manager.get_ads(adset_id=orig_adset["id"])
                            
                            for orig_ad in original_ads:
                                new_ad = ad_manager.duplicate_ad(
                                    ad_id=orig_ad["id"],
                                    adset_id=new_adset["id"],
                                )
                                if new_ad:
                                    result["copied_ads"].append(new_ad)
            
            logger.info(f"キャンペーンを複製しました: {result['name']} "
                       f"(広告セット: {len(result['copied_adsets'])}件, "
                       f"広告: {len(result['copied_ads'])}件)")
            return result
            
        except Exception as e:
            logger.error(f"キャンペーン複製エラー: {e}")
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


