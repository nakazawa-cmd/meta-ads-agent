"""
パフォーマンス監視エンジン v2
キャンペーン目的別・複合期間比較・統合判定
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)

# 日本時間（JST）
JST = timezone(timedelta(hours=9))


# =============================================================================
# キャンペーン目的別の設定
# =============================================================================

CAMPAIGN_TYPE_CONFIG = {
    # トラフィック / フォロワー獲得
    # ★重要: CTRは高くて当然。CPF（フォロー単価）が重要指標
    # ★重要: トラフィックからCVは生まれにくいのでCV関連は無視
    "LINK_CLICKS": {
        "display_name": "トラフィック/フォロー獲得",
        "primary_kpi": "cpf",  # Cost Per Follow が最重要
        "secondary_kpis": ["follows", "cpc"],
        "is_traffic_campaign": True,  # トラフィック系フラグ
        "ignore_conversions": True,   # CV関連の提案をしない
        "thresholds": {
            "cpf_good": 50,       # CPF 50円以下で良好
            "cpf_warning": 100,   # CPF 100円以上で注意
            "cpf_critical": 200,  # CPF 200円以上で危険
            # CTRは参考程度（トラフィックでは高くて当然）
        },
    },
    "POST_ENGAGEMENT": {
        "display_name": "エンゲージメント/フォロワー獲得",
        "primary_kpi": "cpf",  # Cost Per Follower
        "secondary_kpis": ["follows", "engagement_rate"],
        "is_traffic_campaign": True,
        "ignore_conversions": True,
        "thresholds": {
            "cpf_good": 50,       # CPF 50円以下で良好
            "cpf_warning": 100,   # CPF 100円以上で注意
            "cpf_critical": 200,  # CPF 200円以上で危険
        },
    },
    "OUTCOME_TRAFFIC": {
        "display_name": "トラフィック/フォロー獲得",
        "primary_kpi": "cpf",
        "secondary_kpis": ["follows", "cpc"],
        "is_traffic_campaign": True,
        "ignore_conversions": True,
        "thresholds": {
            "cpf_good": 50,
            "cpf_warning": 100,
            "cpf_critical": 200,
        },
    },
    "OUTCOME_ENGAGEMENT": {
        "display_name": "エンゲージメント/フォロー獲得",
        "primary_kpi": "cpf",
        "secondary_kpis": ["follows", "engagement_rate"],
        "is_traffic_campaign": True,
        "ignore_conversions": True,
        "thresholds": {
            "cpf_good": 50,
            "cpf_warning": 100,
            "cpf_critical": 200,
        },
    },
    # 売上 / コンバージョン
    "CONVERSIONS": {
        "display_name": "コンバージョン",
        "primary_kpi": "cpa",
        "secondary_kpis": ["roas", "cvr", "ctr"],
        "thresholds": {
            "cpa_good_ratio": 0.7,     # 目標CPAの70%以下で良好
            "cpa_warning_ratio": 1.0,  # 目標CPA以上で注意
            "cpa_critical_ratio": 1.3, # 目標CPAの130%以上で危険
            "cvr_warning": 0.5,        # CVR 0.5%以下で注意
        },
    },
    "PRODUCT_CATALOG_SALES": {
        "display_name": "カタログ販売",
        "primary_kpi": "roas",
        "secondary_kpis": ["cpa", "cvr"],
        "thresholds": {
            "roas_good": 3.0,      # ROAS 3.0以上で良好
            "roas_warning": 2.0,   # ROAS 2.0以下で注意
            "roas_critical": 1.0,  # ROAS 1.0以下で危険（赤字）
        },
    },
    # ============================================
    # ASC（Advantage+ Shopping Campaign）専用設定
    # ============================================
    # ASCは機械学習で最適化されるため、人間の介入は最小限に
    # 主に予算とクリエイティブの管理が重要
    "ASC": {
        "display_name": "Advantage+ ショッピング（ASC）",
        "primary_kpi": "roas",
        "secondary_kpis": ["cpa", "purchase_value", "cvr"],
        "is_asc_campaign": True,  # ASCフラグ
        "thresholds": {
            "roas_good": 3.0,
            "roas_warning": 2.0,
            "roas_critical": 1.0,
            "cpa_warning_ratio": 1.2,  # 目標CPAの120%以上で注意
            "learning_phase_min_conversions": 50,  # 学習フェーズ: 50CV必要
        },
        "special_notes": [
            "機械学習で最適化されているため、頻繁な変更は避ける",
            "クリエイティブの追加は効果的",
            "予算変更は20%以内に抑える",
            "学習フェーズ中は7日間は様子を見る",
        ],
    },
    # OUTCOME_SALES（新しいAPI形式）
    "OUTCOME_SALES": {
        "display_name": "売上",
        "primary_kpi": "roas",
        "secondary_kpis": ["cpa", "cvr", "purchase_value"],
        "thresholds": {
            "roas_good": 3.0,
            "roas_warning": 2.0,
            "roas_critical": 1.0,
        },
    },
    # 認知 / リーチ
    "REACH": {
        "display_name": "リーチ",
        "primary_kpi": "cpm",
        "secondary_kpis": ["reach", "frequency"],
        "thresholds": {
            "cpm_good": 300,       # CPM 300円以下で良好
            "cpm_warning": 500,    # CPM 500円以上で注意
            "frequency_warning": 3.0,  # フリークエンシー3以上で注意
        },
    },
    "BRAND_AWARENESS": {
        "display_name": "ブランド認知",
        "primary_kpi": "cpm",
        "secondary_kpis": ["reach", "frequency"],
        "thresholds": {
            "cpm_good": 400,
            "cpm_warning": 600,
            "frequency_warning": 2.5,
        },
    },
    # デフォルト（不明な場合）
    "DEFAULT": {
        "display_name": "不明",
        "primary_kpi": "spend",
        "secondary_kpis": ["ctr", "cpc"],
        "thresholds": {},
    },
}


class PerformanceMonitor:
    """
    パフォーマンス監視エンジン v2
    
    改善点:
    1. キャンペーン目的別のKPI・閾値
    2. 複合的な期間比較（昨日 / 7日平均 / 30日平均）
    3. 統合判定（アラートとチャンスの矛盾解消）
    4. 具体的なアクション生成
    5. CPF（Cost Per Follower）対応
    """

    def __init__(self, integrated_agent=None, anthropic_api_key: str = None):
        self.agent = integrated_agent
        
        if anthropic_api_key:
            self.claude = Anthropic(api_key=anthropic_api_key)
        else:
            import config
            self.claude = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        
        # 目標値マネージャーを初期化
        try:
            from automation.targets import get_target_manager
            self.target_manager = get_target_manager()
            logger.info("目標値マネージャーを初期化しました")
        except Exception as e:
            logger.warning(f"目標値マネージャー初期化エラー: {e}")
            self.target_manager = None
        
        # 学習モジュールを初期化
        try:
            from automation.learning import ActionLearner
            self.learner = ActionLearner(integrated_agent=integrated_agent)
            logger.info(f"学習モジュール初期化: {self.learner.get_learning_summary()['total_learnings']}件の学習データ")
        except Exception as e:
            logger.warning(f"学習モジュール初期化エラー: {e}")
            self.learner = None
        
        # 知識ベースを初期化
        try:
            from knowledge_engine.knowledge_base import KnowledgeBase
            self.knowledge_base = KnowledgeBase()
            logger.info("知識ベース初期化完了")
        except Exception as e:
            logger.warning(f"知識ベース初期化エラー: {e}")
            self.knowledge_base = None
        
        logger.info("PerformanceMonitor v2 初期化完了")

    def set_project_target(self, campaign_id: str, targets: dict):
        """プロジェクト固有の目標値を設定"""
        self.project_targets[campaign_id] = targets

    def check_all_accounts(self, account_ids: list[str]) -> dict[str, Any]:
        """全アカウントをチェック"""
        results = {
            "checked_at": datetime.now().isoformat(),
            "accounts": {},
            "alerts": [],
            "opportunities": [],
            "summary": None,
        }
        
        for account_id in account_ids:
            try:
                account_result = self.check_account(account_id)
                results["accounts"][account_id] = account_result
                results["alerts"].extend(account_result.get("alerts", []))
                results["opportunities"].extend(account_result.get("opportunities", []))
            except Exception as e:
                logger.error(f"アカウント {account_id} のチェックエラー: {e}")
                results["accounts"][account_id] = {"error": str(e)}
        
        results["summary"] = self._generate_summary(results)
        return results

    def check_account(self, account_id: str) -> dict[str, Any]:
        """単一アカウントをチェック"""
        if not self.agent or not self.agent.meta_initialized:
            return {"error": "Meta API未接続"}
        
        result = {
            "account_id": account_id,
            "checked_at": datetime.now().isoformat(),
            "campaigns": [],
            "alerts": [],
            "opportunities": [],
            "recommendations": [],
        }
        
        try:
            managers = self.agent._get_managers(account_id)
            if not managers:
                return {"error": "マネージャーの初期化に失敗しました"}
            
            # アクティブキャンペーンを取得
            campaigns = managers["campaign"].get_campaigns(status_filter=["ACTIVE"])
            
            for campaign in campaigns:
                campaign_result = self._analyze_campaign(campaign, managers)
                
                # 消化不足でスキップされたキャンペーンは含めない
                judgment = campaign_result.get("judgment", {})
                if judgment.get("status") == "insufficient_data":
                    continue
                
                result["campaigns"].append(campaign_result)
                
                # ★ 統合判定結果からアラート/チャンスを振り分け
                # ★ ノイズ削減: criticalのみアラート、warningはアラートしない
                status = judgment.get("status")
                
                if status == "critical":
                    # 本当にヤバいものだけアラート
                    result["alerts"].append(self._format_alert(campaign_result))
                elif status == "opportunity":
                    # 好調なものは機会として通知
                    result["opportunities"].append(self._format_opportunity(campaign_result))
                # warningとnormalはアラートにも機会にも含めない（ダッシュボードで確認可能）
            
            # AIによる推奨アクション生成
            if result["alerts"] or result["opportunities"]:
                result["recommendations"] = self._generate_recommendations(result)
            
        except Exception as e:
            logger.error(f"アカウントチェックエラー: {e}")
            result["error"] = str(e)
        
        return result

    def _analyze_campaign(self, campaign: dict, managers: dict) -> dict:
        """
        キャンペーンを詳細分析
        複数期間のデータを取得し、総合判定を行う
        """
        campaign_id = campaign.get("id")
        campaign_name = campaign.get("name", "Unknown")
        objective = campaign.get("objective", "DEFAULT")
        daily_budget = campaign.get("daily_budget", 0) or 0
        
        # ASC（Advantage+ Shopping Campaign）かどうか判定
        is_asc = campaign.get("is_asc", False)
        smart_promotion_type = campaign.get("smart_promotion_type")
        
        # キャンペーン目的の設定を取得（ASCは専用設定）
        if is_asc or smart_promotion_type == "ADVANTAGE_PLUS_SHOPPING":
            type_config = CAMPAIGN_TYPE_CONFIG.get("ASC", CAMPAIGN_TYPE_CONFIG["PRODUCT_CATALOG_SALES"])
            objective = "ASC"  # 表示用にASCとして扱う
        else:
            type_config = CAMPAIGN_TYPE_CONFIG.get(objective, CAMPAIGN_TYPE_CONFIG["DEFAULT"])
        
        # 複数期間のパフォーマンスを取得
        periods = self._get_multi_period_performance(campaign_id, managers)
        
        # 予算消化状況を計算
        budget_status = self._calculate_budget_status(periods.get("today", {}), daily_budget)
        
        # 目標値を取得（目標値マネージャーから）
        targets = {}
        if self.target_manager:
            # キャンペーンタイプを判定
            is_traffic = type_config.get("is_traffic_campaign", False)
            campaign_type = "traffic" if is_traffic else "sales"
            targets = self.target_manager.get_campaign_targets(campaign_id, campaign_type)
        
        # 統合判定
        judgment = self._make_integrated_judgment(
            campaign_name=campaign_name,
            objective=objective,
            type_config=type_config,
            periods=periods,
            budget_status=budget_status,
            targets=targets,
        )
        
        result = {
            "id": campaign_id,
            "name": campaign_name,
            "objective": objective,
            "objective_display": type_config["display_name"],
            "daily_budget": daily_budget,
            "periods": periods,
            "budget_status": budget_status,
            "judgment": judgment,
            "is_asc": is_asc or smart_promotion_type == "ADVANTAGE_PLUS_SHOPPING",
        }
        
        # ASCの場合は特別な注意点を追加
        if result["is_asc"]:
            result["asc_notes"] = type_config.get("special_notes", [])
        
        return result

    def _get_multi_period_performance(self, campaign_id: str, managers: dict) -> dict:
        """複数期間のパフォーマンスを取得"""
        periods = {}
        
        period_configs = [
            ("today", "today"),
            ("yesterday", "yesterday"),
            ("last_7d", "last_7d"),
            ("last_30d", "last_30d"),
        ]
        
        for period_name, date_preset in period_configs:
            try:
                insights = managers["insights"].get_campaign_insights(
                    date_preset=date_preset,
                    campaign_ids=[campaign_id],
                )
                if insights:
                    perf = self.agent._aggregate_insights(insights)
                    
                    # 日数で割って日平均を計算（7日/30日の場合）
                    if period_name == "last_7d":
                        perf = self._calculate_daily_average(perf, 7)
                    elif period_name == "last_30d":
                        perf = self._calculate_daily_average(perf, 30)
                    
                    periods[period_name] = perf
                else:
                    periods[period_name] = {}
            except Exception as e:
                logger.warning(f"期間 {period_name} のデータ取得失敗: {e}")
                periods[period_name] = {}
        
        return periods

    def _calculate_daily_average(self, perf: dict, days: int) -> dict:
        """日平均を計算"""
        if not perf or days <= 0:
            return perf
        
        averaged = perf.copy()
        # 累計値は日数で割る
        for key in ["spend", "impressions", "clicks", "conversions", "reach", "follows", "page_engagements", "link_clicks"]:
            if key in averaged and averaged[key]:
                averaged[key] = averaged[key] / days
                averaged[f"{key}_total"] = perf[key]  # 合計も保持
        
        # CPFを再計算（日平均ベース）
        if averaged.get("follows", 0) > 0 and averaged.get("spend", 0) > 0:
            averaged["cpf"] = round(averaged["spend"] / averaged["follows"], 2)
        
        # 率系は変更しない（既に平均値）
        return averaged

    def _calculate_budget_status(self, today_perf: dict, daily_budget: float) -> dict:
        """予算消化状況を計算（日本時間ベース）"""
        if not daily_budget or daily_budget <= 0:
            return {"status": "unknown", "message": "日予算未設定"}
        
        today_spend = today_perf.get("spend", 0) or 0
        spend_rate = (today_spend / daily_budget) * 100 if daily_budget > 0 else 0
        
        # 日本時間（JST）で現在時刻を取得
        now_jst = datetime.now(JST)
        hours_passed = now_jst.hour + now_jst.minute / 60
        expected_rate = (hours_passed / 24) * 100
        
        # 消化ペースを判定（時間帯を考慮）
        # 深夜〜早朝（0-6時）は消化が少なくて当然
        # 日中（6-24時）で比較
        
        if hours_passed < 6:
            # 早朝は判定しない
            status = "early_morning"
            message = f"早朝のため判定保留（現在: {now_jst.strftime('%H:%M')} JST, 消化: {spend_rate:.0f}%）"
        elif spend_rate < expected_rate * 0.3:
            status = "under_pacing"
            message = f"消化ペース遅れ: {spend_rate:.0f}%消化 (現在{now_jst.strftime('%H:%M')}で期待{expected_rate:.0f}%)"
        elif spend_rate > expected_rate * 1.5:
            status = "over_pacing"
            message = f"消化ペース早い: {spend_rate:.0f}%消化 (期待{expected_rate:.0f}%)"
        else:
            status = "on_track"
            message = f"消化ペース正常: {spend_rate:.0f}%消化（{now_jst.strftime('%H:%M')} JST時点）"
        
        return {
            "status": status,
            "message": message,
            "daily_budget": daily_budget,
            "today_spend": today_spend,
            "spend_rate": spend_rate,
            "expected_rate": expected_rate,
            "current_time_jst": now_jst.strftime("%Y-%m-%d %H:%M JST"),
        }

    def _make_integrated_judgment(
        self,
        campaign_name: str,
        objective: str,
        type_config: dict,
        periods: dict,
        budget_status: dict,
        targets: dict,
    ) -> dict:
        """
        統合判定を行う
        短期的な悪化と長期的なトレンドを組み合わせて判断
        
        ★ノイズ削減のルール:
        1. 最低消化額: 1日1,000円以下はアラート対象外
        2. 厳格な閾値: 50%以上の変化でのみアラート
        3. 消化変動は無視: 消化の急変は問題ではなくノイズ
        4. 継続性重視: 1日だけの悪化ではアラートしない
        """
        today = periods.get("today", {})
        yesterday = periods.get("yesterday", {})
        avg_7d = periods.get("last_7d", {})
        avg_30d = periods.get("last_30d", {})
        
        # ★★★ 最低消化額フィルター ★★★
        # 1日1,000円以下は分析対象外（ノイズになるだけ）
        MIN_DAILY_SPEND = 1000
        spend_today = today.get("spend", 0)
        
        if spend_today < MIN_DAILY_SPEND:
            return {
                "status": "insufficient_data",
                "severity": "none",
                "issues": [],
                "positives": [],
                "comparisons": [],
                "summary": f"消化が少ないため分析スキップ（¥{spend_today:,.0f} < ¥{MIN_DAILY_SPEND:,}）",
            }
        
        issues = []      # 問題点
        positives = []   # 良い点
        comparisons = [] # 比較情報
        
        primary_kpi = type_config["primary_kpi"]
        thresholds = type_config["thresholds"]
        
        # =================================================================
        # 目的別のKPI判定
        # =================================================================
        
        # トラフィック/フォロー獲得キャンペーンかどうか
        is_traffic = type_config.get("is_traffic_campaign", False)
        ignore_conversions = type_config.get("ignore_conversions", False)
        
        if primary_kpi == "cpf":
            # フォロワー獲得キャンペーン
            # CPF（Cost Per Follow）を直接取得、または計算
            cpf_today = today.get("cpf", 0)
            cpf_7d = avg_7d.get("cpf", 0)
            follows_today = today.get("follows", 0)
            follows_7d = avg_7d.get("follows", 0)
            
            target_cpf = targets.get("target_cpf", thresholds.get("cpf_good", 50))
            
            # フォロー数を表示
            if follows_today > 0:
                positives.append(f"本日のフォロー: {follows_today}件")
            
            if cpf_today and cpf_today > 0:
                if cpf_today <= target_cpf:
                    positives.append(f"CPF良好: ¥{cpf_today:.0f} (目標: ¥{target_cpf})")
                elif cpf_today > thresholds.get("cpf_critical", 200):
                    issues.append({
                        "severity": "critical",
                        "message": f"CPF高騰: ¥{cpf_today:.0f} (目標: ¥{target_cpf})",
                    })
                elif cpf_today > thresholds.get("cpf_warning", 100):
                    issues.append({
                        "severity": "warning",
                        "message": f"CPF注意: ¥{cpf_today:.0f} (目標: ¥{target_cpf})",
                    })
                
                # 7日平均との比較
                if cpf_7d and cpf_7d > 0:
                    cpf_change = ((cpf_today - cpf_7d) / cpf_7d) * 100
                    comparisons.append({
                        "metric": "CPF",
                        "today": cpf_today,
                        "avg_7d": cpf_7d,
                        "change_percent": cpf_change,
                        "comparison": "vs7日平均",
                    })
            elif follows_today == 0 and today.get("spend", 0) > 0:
                # フォローがゼロなのに消化がある
                issues.append({
                    "severity": "warning",
                    "message": f"フォロー0件で¥{today.get('spend', 0):,.0f}消化中",
                })
        
        elif primary_kpi == "roas":
            # ROAS重視キャンペーン（ASC等）
            roas_today = today.get("roas", 0)
            roas_7d = avg_7d.get("roas", 0)
            target_roas = targets.get("target_roas", thresholds.get("roas_good", 3.0))
            
            if roas_today > 0:
                if roas_today >= target_roas:
                    positives.append(f"ROAS達成: {roas_today:.2f}x (目標: {target_roas}x)")
                elif roas_today < thresholds.get("roas_critical", 1.0):
                    issues.append({
                        "severity": "critical",
                        "message": f"ROAS赤字: {roas_today:.2f}x (目標: {target_roas}x)",
                    })
                elif roas_today < thresholds.get("roas_warning", 2.0):
                    issues.append({
                        "severity": "warning",
                        "message": f"ROAS低下: {roas_today:.2f}x (目標: {target_roas}x)",
                    })
            
            # 7日平均との比較
            if roas_7d > 0 and roas_today > 0:
                roas_change = ((roas_today - roas_7d) / roas_7d) * 100
                comparisons.append({
                    "metric": "ROAS",
                    "today": roas_today,
                    "avg_7d": roas_7d,
                    "change_percent": roas_change,
                    "direction": "up" if roas_change > 0 else "down",
                })
        
        elif primary_kpi == "cpa":
            # CPA重視キャンペーン
            cpa_today = today.get("cpa", 0)
            cpa_yesterday = yesterday.get("cpa", 0)
            cpa_7d = avg_7d.get("cpa", 0)
            target_cpa = targets.get("target_cpa")
            
            if target_cpa and cpa_today > 0:
                cpa_ratio = cpa_today / target_cpa
                if cpa_ratio <= thresholds.get("cpa_good_ratio", 0.7):
                    positives.append(f"CPA好調: ¥{cpa_today:,.0f} (目標: ¥{target_cpa:,})")
                elif cpa_ratio >= thresholds.get("cpa_critical_ratio", 1.3):
                    issues.append({
                        "severity": "critical",
                        "message": f"CPA超過: ¥{cpa_today:,.0f} (目標: ¥{target_cpa:,}の{cpa_ratio:.0%})",
                    })
                elif cpa_ratio >= thresholds.get("cpa_warning_ratio", 1.0):
                    issues.append({
                        "severity": "warning",
                        "message": f"CPA注意: ¥{cpa_today:,.0f} (目標: ¥{target_cpa:,})",
                    })
            
            # 昨日との比較
            if cpa_yesterday > 0 and cpa_today > 0:
                cpa_change_vs_yesterday = ((cpa_today - cpa_yesterday) / cpa_yesterday) * 100
                comparisons.append({
                    "metric": "CPA",
                    "today": cpa_today,
                    "yesterday": cpa_yesterday,
                    "change_percent": cpa_change_vs_yesterday,
                    "comparison": "vs昨日",
                })
            
            # 7日平均との比較
            if cpa_7d > 0 and cpa_today > 0:
                cpa_change_vs_7d = ((cpa_today - cpa_7d) / cpa_7d) * 100
                comparisons.append({
                    "metric": "CPA",
                    "today": cpa_today,
                    "avg_7d": cpa_7d,
                    "change_percent": cpa_change_vs_7d,
                    "comparison": "vs7日平均",
                })
        
        # =================================================================
        # 共通指標のチェック
        # =================================================================
        
        # CTR比較
        # ★トラフィックキャンペーンではCTRは高くて当然なので、アラートは出さない（参考値のみ）
        ctr_today = today.get("ctr", 0)
        ctr_yesterday = yesterday.get("ctr", 0)
        ctr_7d = avg_7d.get("ctr", 0)
        
        if ctr_yesterday > 0 and ctr_today > 0:
            ctr_change = ((ctr_today - ctr_yesterday) / ctr_yesterday) * 100
            
            # ★ CTR低下は50%以上の場合のみアラート（トラフィック除く）
            if not is_traffic and ctr_change < -50:
                issues.append({
                    "severity": "warning",
                    "message": f"CTR急落: {ctr_yesterday:.2f}% → {ctr_today:.2f}% ({ctr_change:+.0f}%)",
                })
            
            comparisons.append({
                "metric": "CTR",
                "today": ctr_today,
                "yesterday": ctr_yesterday,
                "change_percent": ctr_change,
                "comparison": "vs昨日",
                "note": "（トラフィックでは参考値）" if is_traffic else "",
            })
        
        # CVR比較（トラフィックキャンペーンでは無視）
        if not ignore_conversions:
            cvr_today = today.get("cvr", 0)
            cvr_yesterday = yesterday.get("cvr", 0)
            cvr_7d = avg_7d.get("cvr", 0)
            
            if cvr_yesterday > 0 and cvr_today > 0:
                cvr_change = ((cvr_today - cvr_yesterday) / cvr_yesterday) * 100
                # ★ CVR低下は50%以上の場合のみアラート
                if cvr_change < -50:
                    issues.append({
                        "severity": "warning",
                        "message": f"CVR急落: {cvr_yesterday:.2f}% → {cvr_today:.2f}% ({cvr_change:+.0f}%)",
                    })
                comparisons.append({
                    "metric": "CVR",
                    "today": cvr_today,
                    "yesterday": cvr_yesterday,
                    "change_percent": cvr_change,
                    "comparison": "vs昨日",
                })
        
        # 消化比較（参考情報のみ、アラートは出さない）
        spend_yesterday = yesterday.get("spend", 0)
        spend_7d = avg_7d.get("spend", 0)
        
        if spend_yesterday > 0 and spend_today > 0:
            spend_change = ((spend_today - spend_yesterday) / spend_yesterday) * 100
            # ★ 消化の変動はアラートしない（参考情報として比較データに追加するのみ）
            # 消化の急変は設定変更やオーディエンスの影響であり「問題」ではない
            comparisons.append({
                "metric": "消化",
                "today": spend_today,
                "yesterday": spend_yesterday,
                "change_percent": spend_change,
                "comparison": "vs昨日",
            })
        
        # 7日平均との消化比較（参考情報のみ）
        if spend_7d > 0 and spend_today > 0:
            spend_change_7d = ((spend_today - spend_7d) / spend_7d) * 100
            comparisons.append({
                "metric": "消化",
                "today": spend_today,
                "avg_7d": spend_7d,
                "change_percent": spend_change_7d,
                "comparison": "vs7日平均",
            })
        
        # =================================================================
        # 総合判定（★ノイズ削減: シンプルに判定）
        # =================================================================
        
        critical_count = len([i for i in issues if i.get("severity") == "critical"])
        warning_count = len([i for i in issues if i.get("severity") == "warning"])
        positive_count = len(positives)
        
        # ★ 判定ルール:
        # 1. criticalがあれば問答無用でアラート
        # 2. warningだけの場合は、positiveが多ければ「好調」扱い（矛盾を排除）
        # 3. warningとpositiveが同数なら「通常」扱い（ノイズ削減）
        
        if critical_count > 0:
            status = "critical"
            severity = "high"
            summary = f"🔴 要対応: {critical_count}件の重大な問題"
        elif positive_count > 0 and positive_count > warning_count:
            # ポジティブがwarningより多い → 好調
            status = "opportunity"
            severity = "none"
            summary = f"🟢 好調: {positive_count}件のポジティブ要素"
        elif warning_count > 0 and warning_count > positive_count:
            # warningがポジティブより多い → 注意
            status = "warning"
            severity = "medium"
            summary = f"🟡 注意: {warning_count}件の確認事項"
        else:
            # 同数または両方ゼロ → 通常（アラートなし）
            status = "normal"
            severity = "none"
            summary = "✅ 正常稼働中"
        
        return {
            "status": status,
            "severity": severity,
            "summary": summary,
            "issues": issues,
            "positives": positives,
            "comparisons": comparisons,
            "budget_status": budget_status,
        }

    def _format_alert(self, campaign_result: dict) -> dict:
        """アラートをフォーマット"""
        judgment = campaign_result.get("judgment", {})
        issues = judgment.get("issues", [])
        comparisons = judgment.get("comparisons", [])
        
        # 比較情報を見やすくフォーマット
        comparison_text = []
        for c in comparisons:
            if c.get("change_percent"):
                comparison_text.append(
                    f"{c['metric']}: {c.get('today', 0):.2f} ({c['change_percent']:+.0f}% {c.get('comparison', '')})"
                )
        
        severity = "high" if judgment.get("status") == "critical" else "medium"
        
        return {
            "type": "performance_issue",
            "severity": severity,
            "campaign_id": campaign_result.get("id"),
            "campaign_name": campaign_result.get("name"),
            "objective": campaign_result.get("objective_display"),
            "message": judgment.get("summary"),
            "issues": issues,
            "comparisons": comparison_text,
            "data": {
                "today": campaign_result.get("periods", {}).get("today", {}),
                "yesterday": campaign_result.get("periods", {}).get("yesterday", {}),
                "budget_status": judgment.get("budget_status"),
            },
        }

    def _format_opportunity(self, campaign_result: dict) -> dict:
        """チャンスをフォーマット"""
        judgment = campaign_result.get("judgment", {})
        
        return {
            "type": "opportunity",
            "campaign_id": campaign_result.get("id"),
            "campaign_name": campaign_result.get("name"),
            "objective": campaign_result.get("objective_display"),
            "message": judgment.get("summary"),
            "positives": judgment.get("positives", []),
            "suggested_action": self._suggest_action(campaign_result),
        }

    def _suggest_action(self, campaign_result: dict) -> str:
        """具体的なアクションを提案"""
        judgment = campaign_result.get("judgment", {})
        budget = campaign_result.get("daily_budget", 0)
        objective = campaign_result.get("objective")
        
        if judgment.get("status") == "opportunity":
            if budget > 0:
                suggested_increase = int(budget * 0.2)  # 20%増額
                return f"予算を¥{budget:,} → ¥{budget + suggested_increase:,}に増額検討（+20%）"
            return "予算増額を検討"
        
        return ""

    def _generate_recommendations(self, account_result: dict) -> list[dict]:
        """AIによる具体的な推奨アクションを生成"""
        try:
            # キャンペーン情報を整理
            campaign_summaries = []
            for c in account_result.get("campaigns", []):
                judgment = c.get("judgment", {})
                periods = c.get("periods", {})
                today = periods.get("today", {})
                yesterday = periods.get("yesterday", {})
                avg_7d = periods.get("last_7d", {})
                
                # キャンペーン目的を判定
                objective = c.get("objective", "")
                is_traffic = objective in ["LINK_CLICKS", "POST_ENGAGEMENT", "OUTCOME_TRAFFIC", "OUTCOME_ENGAGEMENT"]
                
                campaign_summaries.append({
                    "name": c.get("name"),
                    "objective": c.get("objective_display"),
                    "is_traffic_campaign": is_traffic,
                    "status": judgment.get("status"),
                    "issues": judgment.get("issues", []),
                    "positives": judgment.get("positives", []),
                    "today": {
                        "spend": today.get("spend", 0),
                        "daily_budget": c.get("daily_budget", 0),
                        # フォロー関連（トラフィックキャンペーン向け）
                        "follows": today.get("follows", 0),
                        "cpf": today.get("cpf", 0),
                        # 従来の指標
                        "cpa": today.get("cpa", 0),
                        "roas": today.get("roas", 0),
                        "ctr": today.get("ctr", 0),
                        "cvr": today.get("cvr", 0),
                    },
                    "vs_yesterday": {
                        "spend_change": self._calc_change(today.get("spend", 0), yesterday.get("spend", 0)),
                        "cpf_change": self._calc_change(today.get("cpf", 0), yesterday.get("cpf", 0)),
                        "cpa_change": self._calc_change(today.get("cpa", 0), yesterday.get("cpa", 0)),
                        "ctr_change": self._calc_change(today.get("ctr", 0), yesterday.get("ctr", 0)),
                    },
                    "vs_7d_avg": {
                        "spend_change": self._calc_change(today.get("spend", 0), avg_7d.get("spend", 0)),
                        "cpf_change": self._calc_change(today.get("cpf", 0), avg_7d.get("cpf", 0)),
                        "cpa_change": self._calc_change(today.get("cpa", 0), avg_7d.get("cpa", 0)),
                    },
                    "budget_status": judgment.get("budget_status", {}),
                })
            
            # 日本時間を取得
            now_jst = datetime.now(JST)
            
            prompt = f"""以下の広告キャンペーンの監視結果を分析し、具体的で実行可能な推奨アクションを生成してください。

## 現在時刻
{now_jst.strftime("%Y-%m-%d %H:%M")} JST（日本時間）

## キャンペーン別サマリー
{campaign_summaries}

## アラート一覧
{account_result.get('alerts', [])}

## 拡大チャンス一覧
{account_result.get('opportunities', [])}

## 過去の学習（類似アクションの結果）
{self._get_learning_context()}

## 関連する運用知識・ベストプラクティス
{self._get_knowledge_context(account_result)}

## 重要ルール
1. 抽象的な提案（「確認してください」「見直してください」）は絶対禁止
2. 具体的な数値を含めた提案をする（例: 「予算を¥2,000 → ¥2,400に増額（+20%）」）
3. キャンペーンの目的を必ず考慮する:
   - **トラフィック/フォロー獲得キャンペーン**: CPF（フォロー単価）が重要指標。CTRは高くて当然なので無視。CVは生まれにくいのでCV関連の提案は禁止。
   - **売上/ASCキャンペーン**: ROAS/CPAが重要指標
4. 短期的な変動（昨日との比較）と長期的なトレンド（7日平均との比較）の両方を考慮する
5. 昨日と比べて悪くても、7日平均と比べて問題なければ「様子見で問題なし」と判断
6. 日予算の消化状況は、現在の日本時間を考慮する（例: 17時で50%消化なら正常）
7. 早朝〜午前中は消化が少なくて当然なのでアラートしない

以下のJSON形式で回答してください（★即実行できる形式）:
[
  {{
    "priority": "high/medium/low",
    "campaign_name": "対象キャンペーン名（上記サマリーのnameと完全一致）",
    "action_type": "budget_increase/budget_decrease/pause/resume/none",
    "action_display": "人間が読む用のアクション説明（例: 予算を¥5,000→¥6,000に増額）",
    "params": {{
      "current_value": 5000,
      "new_value": 6000,
      "change_percent": 20
    }},
    "reason": "なぜこのアクションが必要か（比較データを引用）",
    "risk": "リスクや注意点",
    "expected_impact": "期待される効果"
  }}
]

★重要:
- action_typeは上記5種類のいずれか
- params.current_value, params.new_valueは数値（予算変更の場合は円単位）
- 様子見の場合はaction_type: "none"
- campaign_nameはサマリーのnameと完全一致させること

特に問題がなければ、空の配列 [] を返してください。
最大3件まで、優先度順に出力してください。
"""
            
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            
            import json
            response_text = response.content[0].text
            
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            return json.loads(json_str)
            
        except Exception as e:
            logger.error(f"推奨アクション生成エラー: {e}")
            return []

    def _calc_change(self, current: float, previous: float) -> float:
        """変化率を計算"""
        if previous and previous > 0:
            return ((current - previous) / previous) * 100
        return 0

    def _get_learning_context(self) -> str:
        """過去の学習を提案用にフォーマット"""
        if not self.learner:
            return "学習データなし"
        
        summary = self.learner.get_learning_summary()
        
        if summary["total_learnings"] == 0:
            return "まだ学習データがありません（アクション実行後24時間で効果が学習されます）"
        
        lines = []
        
        # アクションタイプ別の成功率
        for action_type, stats in summary["by_action_type"].items():
            if stats["total"] > 0:
                lines.append(
                    f"- {action_type}: 成功率{stats['success_rate']:.0f}% "
                    f"(成功{stats['improved']}/失敗{stats['worsened']}/中立{stats['neutral']})"
                )
        
        # 最近の学習事例
        recent = summary.get("recent_learnings", [])
        if recent:
            lines.append("\n### 直近の学習事例:")
            for l in recent[-3:]:
                effect = l.get("effect", "neutral")
                icon = {"improved": "✅", "worsened": "❌", "neutral": "➖"}.get(effect, "❓")
                lines.append(f"{icon} {l.get('effect_detail', '詳細なし')}")
        
        return "\n".join(lines) if lines else "学習データなし"

    def _get_knowledge_context(self, account_result: dict) -> str:
        """関連する運用知識を取得"""
        if not self.knowledge_base:
            return "知識ベース未接続"
        
        try:
            # 状況に応じた検索クエリを生成
            alerts = account_result.get("alerts", [])
            opportunities = account_result.get("opportunities", [])
            
            queries = []
            
            # アラートに基づくクエリ
            for alert in alerts[:2]:
                message = alert.get("message", "")
                if "CPA" in message or "cpa" in message.lower():
                    queries.append("CPA改善 コスト削減")
                elif "ROAS" in message:
                    queries.append("ROAS改善 売上")
                elif "CPF" in message:
                    queries.append("フォロワー獲得 CPF")
                elif "予算" in message or "消化" in message:
                    queries.append("予算 学習期間 20%ルール")
            
            # 機会に基づくクエリ
            for opp in opportunities[:2]:
                message = opp.get("message", "")
                if "好調" in message or "良好" in message:
                    queries.append("予算増額 スケール")
            
            if not queries:
                queries = ["広告運用 最適化"]
            
            # 検索実行
            all_results = []
            for query in queries[:2]:
                results = self.knowledge_base.search_knowledge(query, n_results=2)
                all_results.extend(results)
            
            if not all_results:
                return "関連知識なし"
            
            # 結果をフォーマット
            lines = []
            seen_titles = set()
            
            for r in all_results:
                metadata = r.get("metadata", {})
                title = metadata.get("title", "")
                
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                
                content = r.get("document", "")[:300]  # 300文字まで
                lines.append(f"### {title}")
                lines.append(content)
                lines.append("")
                
                if len(lines) > 20:  # 行数制限
                    break
            
            return "\n".join(lines) if lines else "関連知識なし"
            
        except Exception as e:
            logger.warning(f"知識ベース検索エラー: {e}")
            return "知識ベース検索エラー"

    def _generate_summary(self, results: dict) -> dict:
        """全体サマリーを生成"""
        total_alerts = len(results.get("alerts", []))
        total_opportunities = len(results.get("opportunities", []))
        
        high_alerts = len([a for a in results.get("alerts", []) if a.get("severity") == "high"])
        
        if high_alerts > 0:
            status = "critical"
            status_message = f"🔴 緊急対応が必要: {high_alerts}件の重大なアラート"
        elif total_alerts > 0:
            status = "warning"
            status_message = f"🟡 確認が必要: {total_alerts}件のアラート"
        elif total_opportunities > 0:
            status = "opportunity"
            status_message = f"🟢 拡大チャンス: {total_opportunities}件"
        else:
            status = "normal"
            status_message = "✅ 全て正常"
        
        return {
            "status": status,
            "status_message": status_message,
            "total_alerts": total_alerts,
            "high_alerts": high_alerts,
            "total_opportunities": total_opportunities,
            "accounts_checked": len(results.get("accounts", {})),
        }
