"""
広告（クリエイティブ）管理モジュール
"""
import logging
from typing import Any

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.ad import Ad

logger = logging.getLogger(__name__)


class AdManager:
    """広告（クリエイティブ）の取得・操作を行うクラス"""

    def __init__(self, ad_account: AdAccount):
        self.ad_account = ad_account

    def get_ads(
        self,
        adset_id: str = None,
        campaign_id: str = None,
        status_filter: list[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        広告一覧を取得

        Args:
            adset_id: 広告セットIDでフィルタ（オプション）
            campaign_id: キャンペーンIDでフィルタ（オプション）
            status_filter: ステータスでフィルタ (例: ["ACTIVE", "PAUSED"])
            limit: 取得件数上限

        Returns:
            list[dict]: 広告情報のリスト
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

            if adset_id:
                filtering.append({
                    "field": "adset_id",
                    "operator": "EQUAL",
                    "value": adset_id,
                })

            if campaign_id:
                filtering.append({
                    "field": "campaign_id",
                    "operator": "EQUAL",
                    "value": campaign_id,
                })

            if filtering:
                params["filtering"] = filtering

            ads = self.ad_account.get_ads(
                fields=[
                    "id",
                    "name",
                    "adset_id",
                    "campaign_id",
                    "status",
                    "effective_status",
                    "creative",
                    "created_time",
                    "updated_time",
                ],
                params=params,
            )

            result = []
            for ad in ads:
                result.append({
                    "id": ad.get("id"),
                    "name": ad.get("name"),
                    "adset_id": ad.get("adset_id"),
                    "campaign_id": ad.get("campaign_id"),
                    "status": ad.get("status"),
                    "effective_status": ad.get("effective_status"),
                    "creative_id": ad.get("creative", {}).get("id") if ad.get("creative") else None,
                    "created_time": ad.get("created_time"),
                    "updated_time": ad.get("updated_time"),
                })

            logger.info(f"{len(result)} 件の広告を取得しました")
            return result

        except Exception as e:
            logger.error(f"広告の取得に失敗しました: {e}")
            return []

    def get_ad(self, ad_id: str) -> dict[str, Any] | None:
        """
        特定の広告を取得

        Args:
            ad_id: 広告ID

        Returns:
            dict | None: 広告情報
        """
        try:
            ad = Ad(ad_id)
            data = ad.api_get(fields=[
                "id",
                "name",
                "adset_id",
                "campaign_id",
                "status",
                "effective_status",
                "creative",
                "created_time",
                "updated_time",
            ])

            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "adset_id": data.get("adset_id"),
                "campaign_id": data.get("campaign_id"),
                "status": data.get("status"),
                "effective_status": data.get("effective_status"),
                "creative_id": data.get("creative", {}).get("id") if data.get("creative") else None,
                "created_time": data.get("created_time"),
                "updated_time": data.get("updated_time"),
            }

        except Exception as e:
            logger.error(f"広告 {ad_id} の取得に失敗しました: {e}")
            return None

    def update_ad_status(self, ad_id: str, status: str) -> bool:
        """
        広告のステータスを更新

        Args:
            ad_id: 広告ID
            status: 新しいステータス ("ACTIVE", "PAUSED")

        Returns:
            bool: 更新成功したかどうか
        """
        if status not in ["ACTIVE", "PAUSED"]:
            logger.error(f"無効なステータス: {status}")
            return False

        try:
            ad = Ad(ad_id)
            ad.api_update(params={"status": status})
            logger.info(f"広告 {ad_id} のステータスを {status} に更新しました")
            return True

        except Exception as e:
            logger.error(f"広告 {ad_id} のステータス更新に失敗しました: {e}")
            return False

    def pause_ad(self, ad_id: str) -> bool:
        """
        広告を一時停止

        Args:
            ad_id: 広告ID

        Returns:
            bool: 更新成功したかどうか
        """
        return self.update_ad_status(ad_id, "PAUSED")

    def activate_ad(self, ad_id: str) -> bool:
        """
        広告を有効化

        Args:
            ad_id: 広告ID

        Returns:
            bool: 更新成功したかどうか
        """
        return self.update_ad_status(ad_id, "ACTIVE")

    # =========================================================================
    # 広告の作成
    # =========================================================================

    def create_ad(
        self,
        adset_id: str,
        creative_id: str,
        name: str,
        status: str = "PAUSED",
    ) -> dict | None:
        """
        広告を作成
        
        Args:
            adset_id: 広告セットID
            creative_id: クリエイティブID
            name: 広告名
            status: 初期ステータス（PAUSED推奨）
        
        Returns:
            dict: 作成した広告の情報
        """
        try:
            params = {
                "name": name,
                "adset_id": adset_id,
                "creative": {"creative_id": creative_id},
                "status": status,
            }
            
            ad = self.ad_account.create_ad(params=params)
            
            result = {
                "id": ad.get("id"),
                "name": name,
                "adset_id": adset_id,
                "creative_id": creative_id,
            }
            
            logger.info(f"広告を作成しました: {name}")
            return result
            
        except Exception as e:
            logger.error(f"広告作成エラー: {e}")
            return None

    def duplicate_ad(
        self,
        ad_id: str,
        new_name: str = None,
        adset_id: str = None,
    ) -> dict | None:
        """
        既存の広告を複製
        
        Args:
            ad_id: 複製元の広告ID
            new_name: 新しい名前（省略時は元の名前 + " (Copy)"）
            adset_id: 別の広告セットに複製する場合の広告セットID
        
        Returns:
            dict: 複製した広告の情報
        """
        try:
            # 元の広告を取得
            original = self.get_ad(ad_id)
            if not original:
                return None
            
            # 複製パラメータを準備
            params = {
                "name": new_name or f"{original.get('name', 'Ad')} (Copy)",
                "adset_id": adset_id or original.get("adset_id"),
                "creative": {"creative_id": original.get("creative_id")},
                "status": "PAUSED",  # 複製は一旦停止状態で作成
            }
            
            # 作成
            new_ad = self.ad_account.create_ad(params=params)
            
            result = {
                "id": new_ad.get("id"),
                "name": params["name"],
                "original_id": ad_id,
            }
            
            logger.info(f"広告を複製しました: {params['name']}")
            return result
            
        except Exception as e:
            logger.error(f"広告複製エラー: {e}")
            return None

    def create_ad_with_creative(
        self,
        adset_id: str,
        name: str,
        page_id: str,
        image_hash: str = None,
        video_id: str = None,
        message: str = None,
        link_url: str = None,
        headline: str = None,
        description: str = None,
        call_to_action: str = "LEARN_MORE",
        status: str = "PAUSED",
    ) -> dict | None:
        """
        クリエイティブと広告を一度に作成（簡易版）
        
        Args:
            adset_id: 広告セットID
            name: 広告名
            page_id: FacebookページID
            image_hash: 画像ハッシュ（画像広告の場合）
            video_id: 動画ID（動画広告の場合）
            message: 投稿テキスト
            link_url: リンク先URL
            headline: 見出し
            description: 説明文
            call_to_action: CTAボタン
            status: 初期ステータス
        
        Returns:
            dict: 作成した広告の情報
        """
        try:
            # クリエイティブパラメータを構築
            if image_hash:
                object_story_spec = {
                    "page_id": page_id,
                    "link_data": {
                        "image_hash": image_hash,
                        "link": link_url or "https://example.com",
                        "message": message or "",
                        "name": headline or "",
                        "description": description or "",
                        "call_to_action": {"type": call_to_action},
                    },
                }
            elif video_id:
                object_story_spec = {
                    "page_id": page_id,
                    "video_data": {
                        "video_id": video_id,
                        "message": message or "",
                        "name": headline or "",
                        "description": description or "",
                        "call_to_action": {
                            "type": call_to_action,
                            "value": {"link": link_url or "https://example.com"},
                        },
                    },
                }
            else:
                logger.error("image_hash または video_id が必要です")
                return None
            
            # 広告作成パラメータ
            params = {
                "name": name,
                "adset_id": adset_id,
                "creative": {
                    "name": f"{name}_creative",
                    "object_story_spec": object_story_spec,
                },
                "status": status,
            }
            
            ad = self.ad_account.create_ad(params=params)
            
            result = {
                "id": ad.get("id"),
                "name": name,
                "adset_id": adset_id,
            }
            
            logger.info(f"広告（クリエイティブ込み）を作成しました: {name}")
            return result
            
        except Exception as e:
            logger.error(f"広告作成（クリエイティブ込み）エラー: {e}")
            return None

    def get_ads_with_low_performance(
        self,
        insights_data: list[dict],
        ctr_threshold: float = 0.5,
        cvr_threshold: float = 1.0,
        min_impressions: int = 1000,
        min_clicks: int = 50,
    ) -> list[dict[str, Any]]:
        """
        パフォーマンスが低い広告を抽出

        Args:
            insights_data: Insights APIから取得したデータ
            ctr_threshold: CTR閾値（%）
            cvr_threshold: CVR閾値（%）
            min_impressions: 最小インプレッション数
            min_clicks: 最小クリック数

        Returns:
            list[dict]: 低パフォーマンス広告のリスト
        """
        low_performers = []

        for insight in insights_data:
            impressions = insight.get("impressions", 0)
            clicks = insight.get("clicks", 0)
            conversions = insight.get("conversions", 0)

            # 最小インプレッションを満たさない場合はスキップ
            if impressions < min_impressions:
                continue

            # CTR計算
            ctr = (clicks / impressions * 100) if impressions > 0 else 0

            # CVR計算（クリック数が閾値を満たす場合のみ）
            cvr = None
            if clicks >= min_clicks:
                cvr = (conversions / clicks * 100) if clicks > 0 else 0

            # 低パフォーマンス判定
            is_low_ctr = ctr < ctr_threshold
            is_low_cvr = cvr is not None and cvr < cvr_threshold

            if is_low_ctr or is_low_cvr:
                low_performers.append({
                    "ad_id": insight.get("ad_id"),
                    "ad_name": insight.get("ad_name"),
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                    "ctr": round(ctr, 2),
                    "cvr": round(cvr, 2) if cvr is not None else None,
                    "reason": "LOW_CTR" if is_low_ctr else "LOW_CVR",
                })

        logger.info(f"{len(low_performers)} 件の低パフォーマンス広告を検出しました")
        return low_performers


