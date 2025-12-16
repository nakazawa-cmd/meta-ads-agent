"""
入札最適化モジュール
"""
import json
import logging
from datetime import datetime
from typing import Any

from meta_api import AdSetManager, InsightsManager
from .analyzer import PerformanceAnalyzer
import config

logger = logging.getLogger(__name__)


class BidOptimizer:
    """入札の自動最適化を行うクラス"""

    def __init__(
        self,
        adset_manager: AdSetManager,
        insights_manager: InsightsManager,
        analyzer: PerformanceAnalyzer = None,
    ):
        self.adset_manager = adset_manager
        self.insights_manager = insights_manager
        self.analyzer = analyzer or PerformanceAnalyzer()
        self.config = config.BID_OPTIMIZATION

    def optimize_adset_bid(
        self,
        adset_id: str,
        target_cpa: float = None,
        target_roas: float = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """
        広告セットの入札を最適化

        Args:
            adset_id: 広告セットID
            target_cpa: 目標CPA
            target_roas: 目標ROAS
            dry_run: True=実際には変更しない

        Returns:
            dict: 最適化結果
        """
        target_cpa = target_cpa or self.config["default_target_cpa"]
        target_roas = target_roas or self.config["default_target_roas"]

        # 広告セット情報を取得
        adset = self.adset_manager.get_adset(adset_id)
        if not adset:
            return {"success": False, "error": "広告セットが見つかりません"}

        # パフォーマンスデータを取得
        insights = self.insights_manager.get_adset_insights(
            date_preset=f"last_{self.config['min_data_days']}d",
            time_increment=0,  # 合計値
            adset_ids=[adset_id],
        )

        if not insights:
            return {
                "success": False,
                "error": "パフォーマンスデータが取得できません",
            }

        insight = insights[0]

        # 最小コンバージョン数チェック
        if insight.get("conversions", 0) < self.config["min_conversions"]:
            return {
                "success": False,
                "error": f"コンバージョン数が不足しています（{insight.get('conversions', 0)}/{self.config['min_conversions']}）",
                "skip_reason": "insufficient_data",
            }

        # 分析データを準備
        analysis_data = {
            **adset,
            "performance": insight,
        }

        # Claudeに入札調整を提案させる
        suggestion = self.analyzer.suggest_bid_adjustment(
            adset_data=analysis_data,
            target_cpa=target_cpa,
            target_roas=target_roas,
        )

        if suggestion.get("error"):
            return {"success": False, "error": suggestion["error"]}

        result = {
            "adset_id": adset_id,
            "adset_name": adset.get("name"),
            "current_performance": insight,
            "suggestion": suggestion,
            "dry_run": dry_run,
        }

        # 実際に入札を変更
        if suggestion.get("should_adjust") and not dry_run:
            new_bid = suggestion.get("recommended_bid")
            if new_bid:
                success = self.adset_manager.update_adset_bid(adset_id, int(new_bid))
                result["execution"] = {
                    "success": success,
                    "new_bid": new_bid,
                    "timestamp": datetime.now().isoformat(),
                }

                # 操作ログを保存
                self._log_operation(result)

        return result

    def optimize_all_adsets(
        self,
        status_filter: list[str] = None,
        target_cpa: float = None,
        target_roas: float = None,
        dry_run: bool = True,
    ) -> list[dict[str, Any]]:
        """
        すべてのアクティブな広告セットの入札を最適化

        Args:
            status_filter: ステータスフィルタ
            target_cpa: 目標CPA
            target_roas: 目標ROAS
            dry_run: True=実際には変更しない

        Returns:
            list[dict]: 各広告セットの最適化結果
        """
        status_filter = status_filter or ["ACTIVE"]
        
        # 広告セット一覧を取得
        adsets = self.adset_manager.get_adsets(status_filter=status_filter)
        
        results = []
        for adset in adsets:
            logger.info(f"広告セット '{adset['name']}' を最適化中...")
            
            result = self.optimize_adset_bid(
                adset_id=adset["id"],
                target_cpa=target_cpa,
                target_roas=target_roas,
                dry_run=dry_run,
            )
            results.append(result)

        # サマリー
        optimized_count = sum(
            1 for r in results
            if r.get("suggestion", {}).get("should_adjust")
        )
        logger.info(f"最適化完了: {optimized_count}/{len(results)} 件の広告セットで入札調整を提案")

        return results

    def calculate_optimal_bid(
        self,
        current_cpa: float,
        target_cpa: float,
        current_bid: float,
    ) -> dict[str, Any]:
        """
        最適な入札額を計算（ルールベース）

        Args:
            current_cpa: 現在のCPA
            target_cpa: 目標CPA
            current_bid: 現在の入札額

        Returns:
            dict: 計算結果
        """
        if current_cpa <= 0 or target_cpa <= 0 or current_bid <= 0:
            return {
                "recommended_bid": current_bid,
                "change_percent": 0,
                "reason": "データ不足",
            }

        # CPA比率に基づいて入札を調整
        cpa_ratio = current_cpa / target_cpa
        max_change = self.config["max_bid_change_percent"] / 100

        if cpa_ratio > 1.2:
            # CPAが目標を20%以上超過 → 入札を下げる
            change = min((cpa_ratio - 1) * 0.5, max_change)
            new_bid = current_bid * (1 - change)
            reason = f"CPA高騰（{current_cpa:.0f}円 > 目標{target_cpa:.0f}円）"
        elif cpa_ratio < 0.8:
            # CPAが目標の80%未満 → 入札を上げてボリューム増
            change = min((1 - cpa_ratio) * 0.5, max_change)
            new_bid = current_bid * (1 + change)
            reason = f"CPA好調（{current_cpa:.0f}円 < 目標{target_cpa:.0f}円）、ボリューム増を推奨"
        else:
            # 目標付近 → 維持
            new_bid = current_bid
            change = 0
            reason = "CPA目標達成中、現状維持"

        change_percent = (new_bid - current_bid) / current_bid * 100

        return {
            "recommended_bid": round(new_bid, 0),
            "change_percent": round(change_percent, 1),
            "reason": reason,
        }

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
            "type": "bid_optimization",
            "data": operation,
        })

        # 最新1000件のみ保持
        logs = logs[-1000:]

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)


