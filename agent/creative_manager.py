"""
クリエイティブ自動管理モジュール
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from meta_api import AdManager, InsightsManager
from .analyzer import PerformanceAnalyzer
import config

logger = logging.getLogger(__name__)


class CreativeManager:
    """クリエイティブの自動管理を行うクラス"""

    def __init__(
        self,
        ad_manager: AdManager,
        insights_manager: InsightsManager,
        analyzer: PerformanceAnalyzer = None,
    ):
        self.ad_manager = ad_manager
        self.insights_manager = insights_manager
        self.analyzer = analyzer or PerformanceAnalyzer()
        self.config = config.CREATIVE_AUTO_OFF

    def check_low_performers(
        self,
        days: int = None,
    ) -> list[dict[str, Any]]:
        """
        低パフォーマンスのクリエイティブをチェック

        Args:
            days: チェック期間（日数）

        Returns:
            list[dict]: 低パフォーマンスクリエイティブのリスト
        """
        days = days or self.config["consecutive_days"]

        # 広告レベルのパフォーマンスデータを取得
        insights = self.insights_manager.get_ad_insights(
            date_preset=f"last_{days}d",
            time_increment=1,  # 日別
        )

        if not insights:
            logger.info("パフォーマンスデータがありません")
            return []

        # 広告ごとに集計
        ad_performance = self._aggregate_by_ad(insights, days)

        # 低パフォーマンス判定
        low_performers = []
        for ad_id, data in ad_performance.items():
            result = self._evaluate_performance(ad_id, data)
            if result.get("is_low_performer"):
                low_performers.append(result)

        logger.info(f"{len(low_performers)} 件の低パフォーマンスクリエイティブを検出")
        return low_performers

    def auto_pause_low_performers(
        self,
        days: int = None,
        dry_run: bool = True,
        notify: bool = True,
    ) -> dict[str, Any]:
        """
        低パフォーマンスクリエイティブを自動で一時停止

        Args:
            days: チェック期間（日数）
            dry_run: True=実際には停止しない
            notify: Slack通知を送るかどうか

        Returns:
            dict: 実行結果
        """
        low_performers = self.check_low_performers(days)

        if not low_performers:
            return {
                "success": True,
                "message": "低パフォーマンスのクリエイティブはありません",
                "paused_count": 0,
            }

        paused = []
        failed = []

        for ad in low_performers:
            ad_id = ad["ad_id"]
            
            if dry_run:
                paused.append({
                    **ad,
                    "action": "would_pause",
                    "dry_run": True,
                })
            else:
                success = self.ad_manager.pause_ad(ad_id)
                if success:
                    paused.append({
                        **ad,
                        "action": "paused",
                        "timestamp": datetime.now().isoformat(),
                    })
                    # 操作ログを保存
                    self._log_operation({
                        "type": "auto_pause",
                        "ad_id": ad_id,
                        "ad_name": ad.get("ad_name"),
                        "reason": ad.get("reason"),
                        "performance": ad.get("performance"),
                    })
                else:
                    failed.append({
                        **ad,
                        "action": "failed",
                    })

        result = {
            "success": True,
            "dry_run": dry_run,
            "paused_count": len(paused),
            "failed_count": len(failed),
            "paused_ads": paused,
            "failed_ads": failed,
            "timestamp": datetime.now().isoformat(),
        }

        # Slack通知
        if notify and paused and not dry_run:
            self._send_notification(result)

        return result

    def get_creative_ranking(
        self,
        days: int = 7,
        metric: str = "ctr",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        クリエイティブのランキングを取得

        Args:
            days: 集計期間（日数）
            metric: ランキング指標 (ctr, cvr, cpa, roas)
            limit: 取得件数

        Returns:
            list[dict]: ランキング
        """
        insights = self.insights_manager.get_ad_insights(
            date_preset=f"last_{days}d",
            time_increment=0,  # 合計
        )

        if not insights:
            return []

        # 最小インプレッション数でフィルタ
        min_imp = self.config["min_impressions"]
        filtered = [i for i in insights if i.get("impressions", 0) >= min_imp]

        # 指標でソート
        reverse = metric not in ["cpa"]  # CPAは小さい方が良い
        sorted_data = sorted(
            filtered,
            key=lambda x: x.get(metric) or 0,
            reverse=reverse,
        )

        return sorted_data[:limit]

    def analyze_with_ai(
        self,
        days: int = 7,
    ) -> dict[str, Any]:
        """
        AIを使ってクリエイティブを分析

        Args:
            days: 分析期間（日数）

        Returns:
            dict: AI分析結果
        """
        insights = self.insights_manager.get_ad_insights(
            date_preset=f"last_{days}d",
            time_increment=0,
        )

        if not insights:
            return {"error": "データがありません"}

        # 最小インプレッション数でフィルタ
        min_imp = self.config["min_impressions"]
        filtered = [i for i in insights if i.get("impressions", 0) >= min_imp]

        if not filtered:
            return {"error": "十分なデータがありません"}

        return self.analyzer.analyze_creative_performance(filtered)

    def _aggregate_by_ad(
        self,
        insights: list[dict],
        days: int,
    ) -> dict[str, dict]:
        """
        広告ごとにパフォーマンスを集計

        Args:
            insights: Insightsデータ
            days: 集計日数

        Returns:
            dict: 広告IDをキーとした集計データ
        """
        aggregated = {}

        for insight in insights:
            ad_id = insight.get("ad_id")
            if not ad_id:
                continue

            if ad_id not in aggregated:
                aggregated[ad_id] = {
                    "ad_id": ad_id,
                    "ad_name": insight.get("ad_name"),
                    "daily_data": [],
                    "total_impressions": 0,
                    "total_clicks": 0,
                    "total_conversions": 0,
                    "total_spend": 0,
                    "low_ctr_days": 0,
                    "low_cvr_days": 0,
                }

            aggregated[ad_id]["daily_data"].append(insight)
            aggregated[ad_id]["total_impressions"] += insight.get("impressions", 0)
            aggregated[ad_id]["total_clicks"] += insight.get("clicks", 0)
            aggregated[ad_id]["total_conversions"] += insight.get("conversions", 0)
            aggregated[ad_id]["total_spend"] += insight.get("spend", 0)

            # 日別の低パフォーマンスをカウント
            daily_imp = insight.get("impressions", 0)
            daily_clicks = insight.get("clicks", 0)
            daily_conv = insight.get("conversions", 0)

            if daily_imp >= 100:  # 最小インプレッション
                daily_ctr = daily_clicks / daily_imp * 100
                if daily_ctr < self.config["ctr_threshold"]:
                    aggregated[ad_id]["low_ctr_days"] += 1

            if daily_clicks >= 10:  # 最小クリック
                daily_cvr = daily_conv / daily_clicks * 100
                if daily_cvr < self.config["cvr_threshold"]:
                    aggregated[ad_id]["low_cvr_days"] += 1

        return aggregated

    def _evaluate_performance(
        self,
        ad_id: str,
        data: dict,
    ) -> dict[str, Any]:
        """
        広告のパフォーマンスを評価

        Args:
            ad_id: 広告ID
            data: 集計データ

        Returns:
            dict: 評価結果
        """
        result = {
            "ad_id": ad_id,
            "ad_name": data.get("ad_name"),
            "is_low_performer": False,
            "reason": None,
            "performance": {
                "impressions": data["total_impressions"],
                "clicks": data["total_clicks"],
                "conversions": data["total_conversions"],
                "spend": data["total_spend"],
            },
        }

        # 最小インプレッションを満たさない場合はスキップ
        if data["total_impressions"] < self.config["min_impressions"]:
            result["skip_reason"] = "insufficient_impressions"
            return result

        # CTRチェック
        total_ctr = (
            data["total_clicks"] / data["total_impressions"] * 100
            if data["total_impressions"] > 0 else 0
        )
        result["performance"]["ctr"] = round(total_ctr, 2)

        # CVRチェック
        total_cvr = None
        if data["total_clicks"] >= self.config["min_clicks"]:
            total_cvr = (
                data["total_conversions"] / data["total_clicks"] * 100
                if data["total_clicks"] > 0 else 0
            )
            result["performance"]["cvr"] = round(total_cvr, 2)

        # 連続低パフォーマンス判定
        consecutive_days = self.config["consecutive_days"]

        if data["low_ctr_days"] >= consecutive_days:
            result["is_low_performer"] = True
            result["reason"] = f"CTRが{consecutive_days}日連続で閾値以下（CTR: {total_ctr:.2f}%）"

        if data["low_cvr_days"] >= consecutive_days:
            result["is_low_performer"] = True
            result["reason"] = f"CVRが{consecutive_days}日連続で閾値以下（CVR: {total_cvr:.2f}%）"

        return result

    def _log_operation(self, operation: dict[str, Any]) -> None:
        """操作ログを保存"""
        log_file = config.OPERATION_LOG_FILE
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logs = []
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except (json.JSONDecodeError, IOError):
                logs = []

        logs.append({
            "timestamp": datetime.now().isoformat(),
            **operation,
        })

        logs = logs[-1000:]

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    def _send_notification(self, result: dict[str, Any]) -> None:
        """Slack通知を送信"""
        if not config.SLACK_WEBHOOK_URL:
            return

        try:
            import requests

            paused_ads = result.get("paused_ads", [])
            message = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🔴 クリエイティブ自動停止通知",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{len(paused_ads)}件* の低パフォーマンスクリエイティブを自動停止しました。",
                        },
                    },
                    {"type": "divider"},
                ],
            }

            for ad in paused_ads[:5]:  # 最大5件
                message["blocks"].append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{ad.get('ad_name', ad.get('ad_id'))}*\n理由: {ad.get('reason')}",
                    },
                })

            if len(paused_ads) > 5:
                message["blocks"].append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"_...他 {len(paused_ads) - 5} 件_",
                        }
                    ],
                })

            requests.post(
                config.SLACK_WEBHOOK_URL,
                json=message,
                timeout=30,
            )
        except Exception as e:
            logger.error(f"Slack通知に失敗しました: {e}")


