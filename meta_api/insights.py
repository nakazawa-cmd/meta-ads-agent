"""
パフォーマンスデータ（Insights）取得モジュール
"""
import logging
from datetime import datetime, timedelta
from typing import Any

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adsinsights import AdsInsights

logger = logging.getLogger(__name__)


class InsightsManager:
    """パフォーマンスデータの取得を行うクラス"""

    def __init__(self, ad_account: AdAccount):
        self.ad_account = ad_account

    def get_account_insights(
        self,
        date_preset: str = "last_7d",
        time_increment: int = 1,
    ) -> list[dict[str, Any]]:
        """
        アカウントレベルのパフォーマンスデータを取得

        Args:
            date_preset: 期間プリセット (last_7d, last_14d, last_30d, etc.)
            time_increment: 日ごとに分割するか (1=日別, 0=合計)

        Returns:
            list[dict]: パフォーマンスデータ
        """
        return self._get_insights(
            level="account",
            date_preset=date_preset,
            time_increment=time_increment,
        )

    def get_campaign_insights(
        self,
        date_preset: str = "last_7d",
        time_increment: int = 1,
        campaign_ids: list[str] = None,
    ) -> list[dict[str, Any]]:
        """
        キャンペーンレベルのパフォーマンスデータを取得

        Args:
            date_preset: 期間プリセット
            time_increment: 日ごとに分割するか
            campaign_ids: 特定のキャンペーンIDのみ取得（オプション）

        Returns:
            list[dict]: パフォーマンスデータ
        """
        filtering = None
        if campaign_ids:
            filtering = [{"field": "campaign.id", "operator": "IN", "value": campaign_ids}]

        return self._get_insights(
            level="campaign",
            date_preset=date_preset,
            time_increment=time_increment,
            filtering=filtering,
        )

    def get_adset_insights(
        self,
        date_preset: str = "last_7d",
        time_increment: int = 1,
        adset_ids: list[str] = None,
    ) -> list[dict[str, Any]]:
        """
        広告セットレベルのパフォーマンスデータを取得

        Args:
            date_preset: 期間プリセット
            time_increment: 日ごとに分割するか
            adset_ids: 特定の広告セットIDのみ取得（オプション）

        Returns:
            list[dict]: パフォーマンスデータ
        """
        filtering = None
        if adset_ids:
            filtering = [{"field": "adset.id", "operator": "IN", "value": adset_ids}]

        return self._get_insights(
            level="adset",
            date_preset=date_preset,
            time_increment=time_increment,
            filtering=filtering,
        )

    def get_ad_insights(
        self,
        date_preset: str = "last_7d",
        time_increment: int = 1,
        ad_ids: list[str] = None,
    ) -> list[dict[str, Any]]:
        """
        広告レベルのパフォーマンスデータを取得

        Args:
            date_preset: 期間プリセット
            time_increment: 日ごとに分割するか
            ad_ids: 特定の広告IDのみ取得（オプション）

        Returns:
            list[dict]: パフォーマンスデータ
        """
        filtering = None
        if ad_ids:
            filtering = [{"field": "ad.id", "operator": "IN", "value": ad_ids}]

        return self._get_insights(
            level="ad",
            date_preset=date_preset,
            time_increment=time_increment,
            filtering=filtering,
        )

    def get_insights_by_date_range(
        self,
        level: str,
        start_date: str,
        end_date: str,
        time_increment: int = 1,
    ) -> list[dict[str, Any]]:
        """
        日付範囲を指定してパフォーマンスデータを取得

        Args:
            level: 集計レベル (account, campaign, adset, ad)
            start_date: 開始日 (YYYY-MM-DD)
            end_date: 終了日 (YYYY-MM-DD)
            time_increment: 日ごとに分割するか

        Returns:
            list[dict]: パフォーマンスデータ
        """
        return self._get_insights(
            level=level,
            start_date=start_date,
            end_date=end_date,
            time_increment=time_increment,
        )

    def _get_insights(
        self,
        level: str,
        date_preset: str = None,
        start_date: str = None,
        end_date: str = None,
        time_increment: int = 1,
        filtering: list = None,
    ) -> list[dict[str, Any]]:
        """
        Insights APIを呼び出してデータを取得

        Args:
            level: 集計レベル (account, campaign, adset, ad)
            date_preset: 期間プリセット
            start_date: 開始日
            end_date: 終了日
            time_increment: 日ごとに分割するか
            filtering: フィルタ条件

        Returns:
            list[dict]: パフォーマンスデータ
        """
        try:
            # 取得するフィールド
            fields = [
                "date_start",
                "date_stop",
                "impressions",
                "clicks",
                "spend",
                "reach",
                "frequency",
                "cpm",
                "cpc",
                "ctr",
                "actions",
                "action_values",
                "conversions",
                "cost_per_action_type",
                "cost_per_conversion",
            ]

            # レベルに応じたフィールドを追加
            if level == "campaign":
                fields.extend(["campaign_id", "campaign_name"])
            elif level == "adset":
                fields.extend(["campaign_id", "campaign_name", "adset_id", "adset_name"])
            elif level == "ad":
                fields.extend([
                    "campaign_id", "campaign_name",
                    "adset_id", "adset_name",
                    "ad_id", "ad_name",
                ])

            # パラメータ設定
            params = {
                "level": level,
                "time_increment": time_increment,
            }

            if date_preset:
                params["date_preset"] = date_preset
            elif start_date and end_date:
                params["time_range"] = {
                    "since": start_date,
                    "until": end_date,
                }
            else:
                # デフォルトは過去7日
                params["date_preset"] = "last_7d"

            if filtering:
                params["filtering"] = filtering

            # API呼び出し
            insights = self.ad_account.get_insights(
                fields=fields,
                params=params,
            )

            # 結果を整形
            result = []
            for insight in insights:
                data = self._parse_insight(insight)
                result.append(data)

            logger.info(f"{level}レベルで {len(result)} 件のデータを取得しました")
            return result

        except Exception as e:
            logger.error(f"Insightsの取得に失敗しました: {e}")
            return []

    def _parse_insight(self, insight: AdsInsights) -> dict[str, Any]:
        """
        Insightデータを整形

        Args:
            insight: AdsInsightsオブジェクト

        Returns:
            dict: 整形されたデータ
        """
        data = {
            "date_start": insight.get("date_start"),
            "date_stop": insight.get("date_stop"),
            "impressions": int(insight.get("impressions", 0)),
            "clicks": int(insight.get("clicks", 0)),
            "spend": float(insight.get("spend", 0)),
            "reach": int(insight.get("reach", 0)),
            "frequency": float(insight.get("frequency", 0)),
            "cpm": float(insight.get("cpm", 0)),
            "cpc": float(insight.get("cpc", 0)) if insight.get("cpc") else None,
            "ctr": float(insight.get("ctr", 0)),
        }

        # ID/名前フィールド
        for field in ["campaign_id", "campaign_name", "adset_id", "adset_name", "ad_id", "ad_name"]:
            if insight.get(field):
                data[field] = insight.get(field)

        # アクション（コンバージョン）データの解析
        actions = insight.get("actions", [])
        action_values = insight.get("action_values", [])
        cost_per_action = insight.get("cost_per_action_type", [])

        # コンバージョン関連指標を抽出
        conversions = 0
        conversion_value = 0
        cpa = None
        
        # フォロー関連指標（トラフィック/エンゲージメント向け）
        follows = 0
        cpf = None  # Cost Per Follow
        
        # その他のエンゲージメント指標
        page_engagements = 0
        link_clicks = 0
        post_engagements = 0

        for action in actions:
            action_type = action.get("action_type", "")
            value = int(action.get("value", 0))
            
            # コンバージョン系
            if action_type in ["purchase", "complete_registration", "lead", "omni_purchase"]:
                conversions += value
            
            # フォロー（重要！トラフィックキャンペーン向け）
            if action_type in ["follow", "like"]:
                follows += value
            
            # その他エンゲージメント
            if action_type == "page_engagement":
                page_engagements += value
            if action_type == "link_click":
                link_clicks += value
            if action_type == "post_engagement":
                post_engagements += value

        for av in action_values:
            action_type = av.get("action_type", "")
            if action_type in ["purchase", "omni_purchase"]:
                conversion_value += float(av.get("value", 0))

        for cpa_item in cost_per_action:
            action_type = cpa_item.get("action_type", "")
            if action_type in ["purchase", "complete_registration", "lead", "omni_purchase"]:
                cpa = float(cpa_item.get("value", 0))
            # フォロー単価
            if action_type in ["follow", "like"]:
                cpf = float(cpa_item.get("value", 0))

        data["conversions"] = conversions
        data["conversion_value"] = conversion_value
        data["cpa"] = cpa
        
        # フォロー関連
        data["follows"] = follows
        data["cpf"] = cpf
        
        # その他エンゲージメント
        data["page_engagements"] = page_engagements
        data["link_clicks"] = link_clicks
        data["post_engagements"] = post_engagements
        
        # CPFが取得できなかった場合は計算
        if cpf is None and follows > 0 and data["spend"] > 0:
            data["cpf"] = round(data["spend"] / follows, 2)

        # ROAS計算
        if data["spend"] > 0 and conversion_value > 0:
            data["roas"] = round(conversion_value / data["spend"], 2)
        else:
            data["roas"] = None

        # CVR計算
        if data["clicks"] > 0:
            data["cvr"] = round(conversions / data["clicks"] * 100, 2)
        else:
            data["cvr"] = None

        return data

    def get_daily_performance_summary(
        self,
        days: int = 7,
    ) -> dict[str, Any]:
        """
        日別パフォーマンスサマリーを取得

        Args:
            days: 過去何日分を取得するか

        Returns:
            dict: サマリーデータ
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        insights = self.get_insights_by_date_range(
            level="account",
            start_date=start_date,
            end_date=end_date,
            time_increment=1,
        )

        # サマリー計算
        total_spend = sum(i.get("spend", 0) for i in insights)
        total_impressions = sum(i.get("impressions", 0) for i in insights)
        total_clicks = sum(i.get("clicks", 0) for i in insights)
        total_conversions = sum(i.get("conversions", 0) for i in insights)
        total_conversion_value = sum(i.get("conversion_value", 0) for i in insights)

        return {
            "period": f"{start_date} ~ {end_date}",
            "days": days,
            "total_spend": round(total_spend, 0),
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "total_conversion_value": round(total_conversion_value, 0),
            "avg_ctr": round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0,
            "avg_cpc": round(total_spend / total_clicks, 0) if total_clicks > 0 else None,
            "avg_cpa": round(total_spend / total_conversions, 0) if total_conversions > 0 else None,
            "roas": round(total_conversion_value / total_spend, 2) if total_spend > 0 else None,
            "daily_data": insights,
        }


