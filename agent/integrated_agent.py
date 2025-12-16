"""
統合エージェント
Meta APIからリアルデータを取得し、インテリジェントエージェントで分析
"""
import logging
from datetime import datetime, timedelta
from typing import Any

import config
from meta_api import MetaAuth, CampaignManager, AdSetManager, AdManager, InsightsManager
from knowledge_engine import IntelligentAgent, PatternLearner

logger = logging.getLogger(__name__)


class IntegratedAgent:
    """
    Meta API + インテリジェントエージェント統合クラス
    
    機能:
    - 実データの取得
    - AI分析の実行
    - 結果の保存
    - アクションの実行
    """

    def __init__(self):
        # Meta API初期化
        self.meta_initialized = False
        self.meta_auth = None
        try:
            if config.META_ACCESS_TOKEN:
                self.meta_auth = MetaAuth()
                if self.meta_auth.initialize():
                    self.meta_initialized = True
                    logger.info("✅ Meta API 初期化完了")
                else:
                    logger.warning("⚠️ Meta API初期化に失敗しました")
            else:
                logger.warning("⚠️ Meta APIトークンが設定されていません")
        except Exception as e:
            logger.warning(f"⚠️ Meta API初期化スキップ: {e}")
        
        # インテリジェントエージェント初期化
        self.agent = IntelligentAgent()
        self.pattern_learner = PatternLearner()
        
        # マネージャー（広告アカウントごとに初期化）
        self._managers = {}  # account_id -> managers dict
        
        logger.info("🤖 IntegratedAgent 初期化完了")

    def _get_managers(self, account_id: str = None):
        """広告アカウント用のマネージャーを取得（遅延初期化）"""
        if not self.meta_initialized:
            return None
        
        if not account_id:
            if config.META_AD_ACCOUNT_IDS:
                account_id = config.META_AD_ACCOUNT_IDS[0]
            else:
                return None
        
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"
        
        if account_id not in self._managers:
            ad_account = self.meta_auth.get_ad_account(account_id)
            if ad_account:
                self._managers[account_id] = {
                    "campaign": CampaignManager(ad_account),
                    "adset": AdSetManager(ad_account),
                    "ad": AdManager(ad_account),
                    "insights": InsightsManager(ad_account),
                }
            else:
                return None
        
        return self._managers[account_id]

    def get_account_overview(self, account_id: str = None) -> dict[str, Any]:
        """
        アカウント概要を取得
        
        Args:
            account_id: 広告アカウントID（省略時は設定ファイルの最初のアカウント）
        
        Returns:
            dict: アカウント概要
        """
        if not self.meta_initialized:
            return {"error": "Meta APIが初期化されていません", "demo_mode": True}
        
        if not account_id:
            if config.META_AD_ACCOUNT_IDS:
                account_id = config.META_AD_ACCOUNT_IDS[0]
            else:
                return {"error": "広告アカウントIDが設定されていません"}
        
        # アカウントIDの形式を確認
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"
        
        try:
            managers = self._get_managers(account_id)
            if not managers:
                return {"error": "マネージャーの初期化に失敗しました"}
            
            # キャンペーン一覧
            campaigns = managers["campaign"].get_campaigns(status_filter=["ACTIVE"])
            
            # 広告セット一覧
            adsets = managers["adset"].get_adsets(status_filter=["ACTIVE"])
            
            # 直近7日のパフォーマンス
            insights = managers["insights"].get_account_insights(date_preset="last_7d")
            
            return {
                "account_id": account_id,
                "campaigns": {
                    "active_count": len(campaigns),
                    "list": campaigns[:10],  # 最初の10件
                },
                "adsets": {
                    "active_count": len(adsets),
                    "list": adsets[:10],
                },
                "performance_7d": insights,
                "fetched_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"アカウント概要取得エラー: {e}")
            return {"error": str(e)}

    def analyze_campaign(
        self,
        campaign_id: str,
        project_info: dict = None,
    ) -> dict[str, Any]:
        """
        キャンペーンをAI分析
        
        Args:
            campaign_id: キャンペーンID
            project_info: 案件情報（target_cpa, industry等）
        
        Returns:
            dict: AI分析結果
        """
        if not self.meta_initialized:
            return self._demo_campaign_analysis(project_info)
        
        try:
            managers = self._get_managers()
            if not managers:
                return {"error": "マネージャーの初期化に失敗しました"}
            
            # パフォーマンスデータ取得
            insights = managers["insights"].get_campaign_insights(
                date_preset="last_7d",
                campaign_ids=[campaign_id],
            )
            
            if not insights:
                return {"error": "パフォーマンスデータがありません"}
            
            # パフォーマンスデータを整形
            performance = self._format_performance(insights[0] if insights else {})
            
            # 案件情報がない場合はデフォルト値
            project = project_info or {
                "name": f"Campaign {campaign_id}",
                "industry": "健康食品",
                "target_cpa": config.BID_OPTIMIZATION["default_target_cpa"],
                "target_roas": config.BID_OPTIMIZATION["default_target_roas"],
            }
            
            # AI分析実行
            result = self.agent.analyze_and_decide(
                project=project,
                performance=performance,
            )
            
            return result
            
        except Exception as e:
            logger.error(f"キャンペーン分析エラー: {e}")
            return {"error": str(e)}

    def analyze_all_campaigns(
        self,
        account_id: str = None,
        project_mapping: dict[str, dict] = None,
    ) -> list[dict]:
        """
        全アクティブキャンペーンを分析
        
        Args:
            account_id: 広告アカウントID
            project_mapping: キャンペーンIDと案件情報のマッピング
        
        Returns:
            list[dict]: 各キャンペーンの分析結果
        """
        if not self.meta_initialized:
            return self._demo_all_campaigns_analysis()
        
        if not account_id:
            if config.META_AD_ACCOUNT_IDS:
                account_id = config.META_AD_ACCOUNT_IDS[0]
            else:
                return [{"error": "広告アカウントIDが設定されていません"}]
        
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"
        
        results = []
        project_mapping = project_mapping or {}
        
        try:
            managers = self._get_managers(account_id)
            if not managers:
                return [{"error": "マネージャーの初期化に失敗しました"}]
            
            campaigns = managers["campaign"].get_campaigns(status_filter=["ACTIVE"])
            
            for campaign in campaigns:
                campaign_id = campaign.get("id")
                project_info = project_mapping.get(campaign_id)
                
                analysis = self.analyze_campaign(campaign_id, project_info)
                analysis["campaign_id"] = campaign_id
                analysis["campaign_name"] = campaign.get("name")
                
                results.append(analysis)
            
            return results
            
        except Exception as e:
            logger.error(f"全キャンペーン分析エラー: {e}")
            return [{"error": str(e)}]

    def get_daily_report(
        self,
        account_id: str = None,
        date_preset: str = "last_7d",
    ) -> dict[str, Any]:
        """
        レポートを生成
        
        Args:
            account_id: 広告アカウントID
            date_preset: 期間プリセット (today, yesterday, last_3d, last_7d, last_14d, last_30d)
        
        Returns:
            dict: レポート
        """
        if not self.meta_initialized:
            return self._demo_daily_report(date_preset)
        
        if not account_id:
            if config.META_AD_ACCOUNT_IDS:
                account_id = config.META_AD_ACCOUNT_IDS[0]
            else:
                return {"error": "広告アカウントIDが設定されていません"}
        
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"
        
        try:
            managers = self._get_managers(account_id)
            if not managers:
                return {"error": "マネージャーの初期化に失敗しました"}
            
            # 選択期間のサマリー（日別データを取得して合計）
            current_insights_raw = managers["insights"].get_account_insights(
                date_preset=date_preset,
                time_increment=1,  # 日別
            )
            
            # 合計値を計算
            current_insights = [self._aggregate_insights(current_insights_raw)] if current_insights_raw else []
            
            # 前期間は「昨日」で簡易比較
            previous_insights_raw = managers["insights"].get_account_insights(
                date_preset="yesterday",
                time_increment=1,
            )
            previous_insights = previous_insights_raw
            
            # キャンペーン別パフォーマンス
            campaign_insights = managers["insights"].get_campaign_insights(
                date_preset=date_preset,
                time_increment=1,
            )
            
            # AIによるブリーフィング生成
            projects = []
            for ci in campaign_insights:
                perf = self._format_performance(ci)
                projects.append({
                    "name": ci.get("campaign_name", "Unknown"),
                    "target_cpa": config.BID_OPTIMIZATION["default_target_cpa"],
                    "target_roas": config.BID_OPTIMIZATION["default_target_roas"],
                    "performance": perf,
                })
            
            briefing = self.agent.get_daily_briefing(projects)
            
            return {
                "date_preset": date_preset,
                "account_id": account_id,
                "current": self._format_performance(current_insights[0] if current_insights else {}),
                "previous": self._format_performance(previous_insights[0] if previous_insights else {}),
                "campaigns": campaign_insights,
                "ai_briefing": briefing,
                "generated_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"日次レポート生成エラー: {e}")
            return {"error": str(e)}

    def simulate_budget_change(
        self,
        campaign_id: str,
        new_budget: float,
        project_info: dict = None,
    ) -> dict[str, Any]:
        """
        予算変更のシミュレーション
        
        Args:
            campaign_id: キャンペーンID
            new_budget: 新しい日予算
            project_info: 案件情報
        
        Returns:
            dict: シミュレーション結果
        """
        if not self.meta_initialized:
            return self._demo_budget_simulation(new_budget, project_info)
        
        # デモモードでシミュレーション実行
        return self._demo_budget_simulation(new_budget, project_info)

    def record_performance(self, account_id: str = None) -> int:
        """
        パフォーマンスを履歴に記録（パターン学習用）
        
        Args:
            account_id: 広告アカウントID
        
        Returns:
            int: 記録件数
        """
        if not self.meta_initialized:
            return 0
        
        if not account_id:
            if config.META_AD_ACCOUNT_IDS:
                account_id = config.META_AD_ACCOUNT_IDS[0]
            else:
                return 0
        
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"
        
        count = 0
        today = datetime.now().strftime("%Y-%m-%d")
        
        try:
            managers = self._get_managers(account_id)
            if not managers:
                return 0
            
            campaign_insights = managers["insights"].get_campaign_insights(
                date_preset="today",
            )
            
            for ci in campaign_insights:
                performance = self._format_performance(ci)
                
                self.pattern_learner.record_performance(
                    project_id=ci.get("campaign_id", "unknown"),
                    project_name=ci.get("campaign_name", "Unknown"),
                    date=today,
                    metrics=performance,
                    context={
                        "account_id": account_id,
                        "target_cpa": config.BID_OPTIMIZATION["default_target_cpa"],
                    },
                )
                count += 1
            
            logger.info(f"📊 {count}件のパフォーマンスを記録")
            return count
            
        except Exception as e:
            logger.error(f"パフォーマンス記録エラー: {e}")
            return 0

    def _aggregate_insights(self, insights_list: list) -> dict:
        """複数のInsightsデータを合計"""
        if not insights_list:
            return {}
        
        total = {
            "spend": sum(float(i.get("spend", 0)) for i in insights_list),
            "impressions": sum(int(i.get("impressions", 0)) for i in insights_list),
            "clicks": sum(int(i.get("clicks", 0)) for i in insights_list),
            "conversions": sum(int(i.get("conversions", 0)) for i in insights_list),
            "conversion_value": sum(float(i.get("conversion_value", 0)) for i in insights_list),
            "reach": sum(int(i.get("reach", 0)) for i in insights_list),
            # フォロー関連（トラフィック/エンゲージメント向け）
            "follows": sum(int(i.get("follows", 0)) for i in insights_list),
            "page_engagements": sum(int(i.get("page_engagements", 0)) for i in insights_list),
            "link_clicks": sum(int(i.get("link_clicks", 0)) for i in insights_list),
        }
        
        # 派生指標
        if total["impressions"] > 0:
            total["ctr"] = round(total["clicks"] / total["impressions"] * 100, 2)
            total["cpm"] = round(total["spend"] / total["impressions"] * 1000, 0)
        else:
            total["ctr"] = 0
            total["cpm"] = 0
        
        if total["clicks"] > 0:
            total["cpc"] = round(total["spend"] / total["clicks"], 0)
            total["cvr"] = round(total["conversions"] / total["clicks"] * 100, 2)
        else:
            total["cpc"] = 0
            total["cvr"] = 0
        
        if total["conversions"] > 0:
            total["cpa"] = round(total["spend"] / total["conversions"], 0)
        else:
            total["cpa"] = 0
        
        if total["spend"] > 0 and total["conversion_value"] > 0:
            total["roas"] = round(total["conversion_value"] / total["spend"], 2)
        else:
            total["roas"] = 0
        
        # CPF（Cost Per Follow）
        if total["follows"] > 0:
            total["cpf"] = round(total["spend"] / total["follows"], 2)
        else:
            total["cpf"] = 0
        
        return total

    def _format_performance(self, raw_data: dict) -> dict:
        """生データをパフォーマンス形式に整形"""
        spend = float(raw_data.get("spend", 0))
        impressions = int(raw_data.get("impressions", 0))
        clicks = int(raw_data.get("clicks", 0))
        
        # コンバージョンの取得（複数の可能性があるフィールドをチェック）
        conversions = 0
        if "conversions" in raw_data:
            conversions = int(raw_data["conversions"])
        elif "actions" in raw_data:
            for action in raw_data.get("actions", []):
                if action.get("action_type") in ["purchase", "lead", "complete_registration"]:
                    conversions += int(action.get("value", 0))
        
        # 派生指標の計算
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        cpc = (spend / clicks) if clicks > 0 else 0
        cvr = (conversions / clicks * 100) if clicks > 0 else 0
        cpa = (spend / conversions) if conversions > 0 else 0
        
        # ROASの計算
        conversion_value = float(raw_data.get("conversion_value", 0))
        if not conversion_value and "action_values" in raw_data:
            for av in raw_data.get("action_values", []):
                if av.get("action_type") in ["purchase", "omni_purchase"]:
                    conversion_value += float(av.get("value", 0))
        
        roas = (conversion_value / spend) if spend > 0 else 0
        
        return {
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "ctr": round(ctr, 2),
            "cpc": round(cpc, 0),
            "cvr": round(cvr, 2),
            "cpa": round(cpa, 0),
            "roas": round(roas, 2),
            "conversion_value": conversion_value,
        }

    # =========================================================================
    # デモモード（Meta API未接続時）
    # =========================================================================

    def _demo_campaign_analysis(self, project_info: dict = None) -> dict:
        """デモ用キャンペーン分析"""
        project = project_info or {
            "name": "デモ案件",
            "industry": "健康食品",
            "target_cpa": 5000,
            "target_roas": 3.5,
            "has_article_lp": True,
            "offer": "初回980円",
        }
        
        performance = {
            "spend": 85000,
            "impressions": 320000,
            "clicks": 5760,
            "conversions": 18,
            "ctr": 1.8,
            "cpc": 15,
            "cvr": 0.31,
            "cpa": 4722,
            "roas": 3.8,
        }
        
        return self.agent.analyze_and_decide(
            project=project,
            performance=performance,
        )

    def _demo_all_campaigns_analysis(self) -> list[dict]:
        """デモ用全キャンペーン分析"""
        demo_campaigns = [
            {
                "name": "美容サプリA",
                "industry": "美容・コスメ",
                "target_cpa": 5000,
                "performance": {"spend": 95000, "impressions": 380000, "clicks": 6840, "conversions": 16, "ctr": 1.8, "cvr": 0.23, "cpa": 5938, "roas": 2.8},
            },
            {
                "name": "健康食品B",
                "industry": "健康食品",
                "target_cpa": 6000,
                "performance": {"spend": 120000, "impressions": 500000, "clicks": 7500, "conversions": 25, "ctr": 1.5, "cvr": 0.33, "cpa": 4800, "roas": 4.2},
            },
            {
                "name": "オンライン講座C",
                "industry": "教育",
                "target_cpa": 10000,
                "performance": {"spend": 80000, "impressions": 200000, "clicks": 4000, "conversions": 10, "ctr": 2.0, "cvr": 0.25, "cpa": 8000, "roas": 6.5},
            },
        ]
        
        results = []
        for campaign in demo_campaigns:
            analysis = self.agent.analyze_and_decide(
                project={
                    "name": campaign["name"],
                    "industry": campaign["industry"],
                    "target_cpa": campaign["target_cpa"],
                },
                performance=campaign["performance"],
            )
            analysis["campaign_name"] = campaign["name"]
            analysis["demo_mode"] = True
            results.append(analysis)
        
        return results

    def _demo_daily_report(self, date_preset: str = "last_7d") -> dict:
        """デモ用レポート"""
        projects = [
            {"name": "美容サプリA", "target_cpa": 5000, "target_roas": 3.0, "performance": {"spend": 95000, "conversions": 16, "cpa": 5938, "roas": 2.8}},
            {"name": "健康食品B", "target_cpa": 6000, "target_roas": 4.0, "performance": {"spend": 120000, "conversions": 25, "cpa": 4800, "roas": 4.2}},
            {"name": "オンライン講座C", "target_cpa": 10000, "target_roas": 5.0, "performance": {"spend": 80000, "conversions": 10, "cpa": 8000, "roas": 6.5}},
        ]
        
        briefing = self.agent.get_daily_briefing(projects)
        
        return {
            "date_preset": date_preset,
            "demo_mode": True,
            "current": {
                "spend": 295000,
                "impressions": 1200000,
                "clicks": 18000,
                "conversions": 51,
                "ctr": 1.5,
                "cvr": 0.28,
                "cpa": 5784,
                "roas": 4.1,
            },
            "previous": {
                "spend": 280000,
                "impressions": 1150000,
                "clicks": 17000,
                "conversions": 48,
                "ctr": 1.48,
                "cvr": 0.28,
                "cpa": 5833,
                "roas": 3.9,
            },
            "ai_briefing": briefing,
            "generated_at": datetime.now().isoformat(),
        }

    def _demo_budget_simulation(self, new_budget: float, project_info: dict = None) -> dict:
        """デモ用予算シミュレーション"""
        from knowledge_engine import Predictor
        predictor = Predictor()
        
        current_performance = {
            "spend": 100000,
            "impressions": 400000,
            "clicks": 6000,
            "conversions": 20,
            "ctr": 1.5,
            "cvr": 0.33,
            "cpc": 17,
            "cpa": 5000,
            "roas": 4.0,
        }
        
        return predictor.simulate_budget_change(
            current_performance=current_performance,
            current_budget=100000,
            new_budget=new_budget,
            context=project_info or {"target_cpa": 6000},
        )


