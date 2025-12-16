"""
自動入稿提案モジュール
AIがパフォーマンスを分析し、クリエイティブ追加・広告セット作成などを提案
"""
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class AutoCreativeProposer:
    """
    AIによる自動入稿提案を生成するクラス
    
    機能:
    1. パフォーマンス分析に基づくクリエイティブ追加提案
    2. 好調キャンペーン/広告セットの複製提案
    3. 新規キャンペーン作成提案
    """

    def __init__(self, integrated_agent=None, action_executor=None):
        """
        初期化
        
        Args:
            integrated_agent: IntegratedAgentインスタンス
            action_executor: ActionExecutorインスタンス
        """
        self.agent = integrated_agent
        self.executor = action_executor
        logger.info("AutoCreativeProposer初期化完了")

    def analyze_and_propose(
        self,
        account_id: str,
        monitor_results: dict,
    ) -> list[dict]:
        """
        監視結果を分析し、入稿提案を生成
        
        Args:
            account_id: アカウントID
            monitor_results: PerformanceMonitorの結果
        
        Returns:
            list[dict]: 入稿提案のリスト
        """
        proposals = []
        
        campaigns = monitor_results.get("campaigns", [])
        opportunities = monitor_results.get("opportunities", [])
        
        # 1. 好調キャンペーンへのクリエイティブ追加提案
        proposals.extend(self._propose_creative_additions(campaigns, opportunities))
        
        # 2. 好調広告セットの複製提案
        proposals.extend(self._propose_adset_duplications(campaigns, opportunities))
        
        # 3. ASCキャンペーンのクリエイティブ追加提案
        proposals.extend(self._propose_asc_creative_additions(campaigns))
        
        # 各提案にメタ情報を追加
        for proposal in proposals:
            proposal["account_id"] = account_id
            proposal["proposed_at"] = datetime.now().isoformat()
            proposal["status"] = "pending_approval"
        
        logger.info(f"{len(proposals)}件の入稿提案を生成しました")
        return proposals

    def _propose_creative_additions(
        self,
        campaigns: list[dict],
        opportunities: list[dict],
    ) -> list[dict]:
        """好調キャンペーンへのクリエイティブ追加を提案"""
        proposals = []
        
        # 拡大チャンスのあるキャンペーンを対象に
        opportunity_campaign_ids = {o.get("campaign_id") for o in opportunities}
        
        for campaign in campaigns:
            campaign_id = campaign.get("id")
            campaign_name = campaign.get("name", "Unknown")
            judgment = campaign.get("judgment", {})
            
            # 好調（opportunity）なキャンペーンのみ
            if campaign_id not in opportunity_campaign_ids:
                continue
            
            # ROASまたはCPFが目標達成している場合
            positives = judgment.get("positives", [])
            if not positives:
                continue
            
            proposals.append({
                "type": "creative_addition",
                "action": "add_creative",
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "reason": f"好調なキャンペーンにクリエイティブを追加して配信拡大",
                "details": {
                    "positive_signals": [p.get("message") for p in positives[:3]],
                },
                "priority": "medium",
                "expected_impact": "配信ボリューム増加＆学習データ蓄積",
                "required_inputs": [
                    "画像/動画ファイル",
                    "広告テキスト",
                    "見出し",
                ],
            })
        
        return proposals

    def _propose_adset_duplications(
        self,
        campaigns: list[dict],
        opportunities: list[dict],
    ) -> list[dict]:
        """好調広告セットの複製を提案"""
        proposals = []
        
        opportunity_campaign_ids = {o.get("campaign_id") for o in opportunities}
        
        for campaign in campaigns:
            campaign_id = campaign.get("id")
            campaign_name = campaign.get("name", "Unknown")
            judgment = campaign.get("judgment", {})
            periods = campaign.get("periods", {})
            
            # 好調なキャンペーンのみ
            if campaign_id not in opportunity_campaign_ids:
                continue
            
            # 7日間で安定して好調な場合
            last_7d = periods.get("last_7d", {})
            roas = last_7d.get("roas", 0)
            conversions = last_7d.get("conversions", 0)
            
            if roas >= 3.0 and conversions >= 10:
                proposals.append({
                    "type": "adset_duplication",
                    "action": "duplicate_adset",
                    "campaign_id": campaign_id,
                    "campaign_name": campaign_name,
                    "reason": f"ROAS {roas:.1f}、CV {conversions}件で安定好調のため広告セット複製",
                    "details": {
                        "last_7d_roas": roas,
                        "last_7d_conversions": conversions,
                    },
                    "priority": "low",
                    "expected_impact": "同一ターゲティングでの配信拡大",
                    "required_inputs": [],
                })
        
        return proposals

    def _propose_asc_creative_additions(self, campaigns: list[dict]) -> list[dict]:
        """ASCキャンペーンへのクリエイティブ追加提案"""
        proposals = []
        
        for campaign in campaigns:
            is_asc = campaign.get("is_asc", False)
            
            if not is_asc:
                continue
            
            campaign_id = campaign.get("id")
            campaign_name = campaign.get("name", "Unknown")
            judgment = campaign.get("judgment", {})
            periods = campaign.get("periods", {})
            
            # ASCは常にクリエイティブ追加が効果的
            last_7d = periods.get("last_7d", {})
            roas = last_7d.get("roas", 0)
            
            if roas >= 2.0:  # ROASが2以上なら追加提案
                proposals.append({
                    "type": "asc_creative_addition",
                    "action": "add_creative_to_asc",
                    "campaign_id": campaign_id,
                    "campaign_name": campaign_name,
                    "reason": f"ASCキャンペーン（ROAS {roas:.1f}）にクリエイティブ追加で機械学習を強化",
                    "details": {
                        "current_roas": roas,
                        "note": "ASCは多様なクリエイティブで学習効率が向上",
                    },
                    "priority": "high" if roas >= 3.0 else "medium",
                    "expected_impact": "機械学習の精度向上＆配信拡大",
                    "required_inputs": [
                        "商品画像（複数推奨）",
                        "動画素材（あれば）",
                    ],
                })
        
        return proposals

    def create_proposal_action(self, proposal: dict) -> str | None:
        """
        提案をアクションキューに追加
        
        Args:
            proposal: 入稿提案
        
        Returns:
            str: アクションID（成功時）
        """
        if not self.executor:
            logger.error("ActionExecutorが未設定")
            return None
        
        action_type = proposal.get("action", "unknown")
        
        # アクション作成
        action = {
            "type": action_type,
            "campaign_id": proposal.get("campaign_id"),
            "campaign_name": proposal.get("campaign_name"),
            "account_id": proposal.get("account_id"),
            "reason": proposal.get("reason"),
            "params": {
                "proposal_type": proposal.get("type"),
                "details": proposal.get("details"),
                "expected_impact": proposal.get("expected_impact"),
                "required_inputs": proposal.get("required_inputs"),
            },
        }
        
        action_id = self.executor.add_to_queue(action, priority=proposal.get("priority", "medium"))
        
        logger.info(f"入稿提案をキューに追加: {action_id}")
        return action_id


def analyze_and_propose_creatives(
    agent,
    action_executor,
    account_id: str,
    monitor_results: dict,
) -> list[dict]:
    """
    ヘルパー関数: クリエイティブ提案を生成してキューに追加
    
    Args:
        agent: IntegratedAgent
        action_executor: ActionExecutor
        account_id: アカウントID
        monitor_results: 監視結果
    
    Returns:
        list[dict]: 生成した提案のリスト
    """
    proposer = AutoCreativeProposer(
        integrated_agent=agent,
        action_executor=action_executor,
    )
    
    proposals = proposer.analyze_and_propose(account_id, monitor_results)
    
    # 各提案をアクションキューに追加
    for proposal in proposals:
        proposer.create_proposal_action(proposal)
    
    return proposals

