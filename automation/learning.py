"""
実行履歴学習モジュール
何をやったら改善/悪化したかを自動分析し、提案に活かす
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ActionLearner:
    """
    実行履歴から学習するクラス
    
    学習の流れ:
    1. アクション実行時に「実行前」のパフォーマンスを記録
    2. 24時間後に「実行後」のパフォーマンスを取得
    3. 改善/悪化を判定して学習データに保存
    4. 提案時に類似ケースを参照
    """

    def __init__(self, storage_dir: str = None, integrated_agent=None):
        if storage_dir is None:
            storage_dir = str(Path(__file__).parent.parent / "storage" / "learning")
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.learnings_file = self.storage_dir / "action_learnings.json"
        self.pending_file = self.storage_dir / "pending_analysis.json"
        
        self.learnings = self._load_json(self.learnings_file, [])
        self.pending = self._load_json(self.pending_file, [])
        
        self.agent = integrated_agent
        
        logger.info(f"ActionLearner初期化: 学習済み{len(self.learnings)}件, 分析待ち{len(self.pending)}件")

    def _load_json(self, path: Path, default: Any) -> Any:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return default

    def _save_json(self, path: Path, data: Any):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def record_action_with_baseline(
        self,
        action: dict,
        campaign_id: str,
        account_id: str,
        baseline_metrics: dict,
    ) -> str:
        """
        アクション実行時に「実行前」の状態を記録
        
        Args:
            action: 実行したアクション
            campaign_id: キャンペーンID
            account_id: アカウントID
            baseline_metrics: 実行前の指標 (spend, cpa, roas, ctr, cvr等)
        
        Returns:
            str: 学習レコードID
        """
        import uuid
        record_id = str(uuid.uuid4())[:8]
        
        record = {
            "id": record_id,
            "action": action,
            "campaign_id": campaign_id,
            "account_id": account_id,
            "executed_at": datetime.now().isoformat(),
            "analyze_after": (datetime.now() + timedelta(hours=24)).isoformat(),
            "baseline": baseline_metrics,
            "status": "pending_analysis",
        }
        
        self.pending.append(record)
        self._save_json(self.pending_file, self.pending)
        
        logger.info(f"学習レコード作成: {record_id} (24時間後に効果分析)")
        return record_id

    def analyze_pending_actions(self) -> list[dict]:
        """
        分析待ちのアクションを分析（24時間経過したもの）
        
        Returns:
            list: 分析結果のリスト
        """
        if not self.agent or not self.agent.meta_initialized:
            logger.warning("Meta API未接続のため分析スキップ")
            return []
        
        now = datetime.now()
        analyzed = []
        still_pending = []
        
        for record in self.pending:
            analyze_after = datetime.fromisoformat(record["analyze_after"])
            
            if now >= analyze_after:
                # 分析実行
                result = self._analyze_action_effect(record)
                if result:
                    self.learnings.append(result)
                    analyzed.append(result)
                    logger.info(f"学習完了: {record['id']} -> {result.get('effect')}")
            else:
                still_pending.append(record)
        
        # 保存
        self.pending = still_pending
        self._save_json(self.pending_file, self.pending)
        self._save_json(self.learnings_file, self.learnings)
        
        return analyzed

    def _analyze_action_effect(self, record: dict) -> Optional[dict]:
        """
        アクションの効果を分析
        
        比較ロジック:
        - 予算増: 消化が増えてCPA/CPFが維持or改善 → 成功
        - 予算減: 消化が減ってCPA/CPFが悪化しない → 成功
        - 停止: 無駄な消化を止めた → 成功
        """
        try:
            campaign_id = record["campaign_id"]
            account_id = record["account_id"]
            baseline = record["baseline"]
            action = record["action"]
            action_type = action.get("type", "")
            
            # 現在のパフォーマンスを取得（過去7日）
            managers = self.agent._get_managers(account_id)
            if not managers:
                return None
            
            current = managers["insights"].get_campaign_insights(
                campaign_id, date_preset="last_7d"
            )
            
            if not current:
                return None
            
            # 効果判定
            effect = self._determine_effect(action_type, baseline, current)
            
            return {
                "id": record["id"],
                "action": action,
                "campaign_id": campaign_id,
                "account_id": account_id,
                "executed_at": record["executed_at"],
                "analyzed_at": datetime.now().isoformat(),
                "baseline": baseline,
                "after": {
                    "spend": current.get("spend", 0),
                    "cpa": current.get("cpa", 0),
                    "roas": current.get("roas", 0),
                    "ctr": current.get("ctr", 0),
                    "cpf": current.get("cpf", 0),
                },
                "effect": effect["verdict"],
                "effect_detail": effect["detail"],
                "confidence": effect["confidence"],
            }
            
        except Exception as e:
            logger.error(f"効果分析エラー: {e}")
            return None

    def _determine_effect(
        self,
        action_type: str,
        baseline: dict,
        current: dict,
    ) -> dict:
        """
        効果を判定
        
        Returns:
            dict: {verdict: "improved/worsened/neutral", detail: str, confidence: float}
        """
        baseline_cpa = baseline.get("cpa", 0)
        baseline_roas = baseline.get("roas", 0)
        baseline_spend = baseline.get("spend", 0)
        baseline_cpf = baseline.get("cpf", 0)
        
        current_cpa = current.get("cpa", 0)
        current_roas = current.get("roas", 0)
        current_spend = current.get("spend", 0)
        current_cpf = current.get("cpf", 0)
        
        # 変化率計算
        def calc_change(before, after):
            if before and before > 0:
                return ((after - before) / before) * 100
            return 0
        
        cpa_change = calc_change(baseline_cpa, current_cpa)
        roas_change = calc_change(baseline_roas, current_roas)
        spend_change = calc_change(baseline_spend, current_spend)
        cpf_change = calc_change(baseline_cpf, current_cpf)
        
        # 判定ロジック
        if action_type in ["budget_increase", "budget_change"]:
            # 予算増加の場合
            if current_cpa > 0 and baseline_cpa > 0:
                # CPA基準
                if cpa_change < -10:
                    return {
                        "verdict": "improved",
                        "detail": f"CPA改善: ¥{baseline_cpa:,.0f}→¥{current_cpa:,.0f} ({cpa_change:+.0f}%)",
                        "confidence": 0.8,
                    }
                elif cpa_change > 20:
                    return {
                        "verdict": "worsened",
                        "detail": f"CPA悪化: ¥{baseline_cpa:,.0f}→¥{current_cpa:,.0f} ({cpa_change:+.0f}%)",
                        "confidence": 0.8,
                    }
            
            if current_roas > 0 and baseline_roas > 0:
                # ROAS基準
                if roas_change > 10:
                    return {
                        "verdict": "improved",
                        "detail": f"ROAS改善: {baseline_roas:.2f}→{current_roas:.2f} ({roas_change:+.0f}%)",
                        "confidence": 0.8,
                    }
                elif roas_change < -20:
                    return {
                        "verdict": "worsened",
                        "detail": f"ROAS悪化: {baseline_roas:.2f}→{current_roas:.2f} ({roas_change:+.0f}%)",
                        "confidence": 0.8,
                    }
            
            if current_cpf > 0 and baseline_cpf > 0:
                # CPF基準（フォロワー獲得）
                if cpf_change < -10:
                    return {
                        "verdict": "improved",
                        "detail": f"CPF改善: ¥{baseline_cpf:,.0f}→¥{current_cpf:,.0f} ({cpf_change:+.0f}%)",
                        "confidence": 0.8,
                    }
                elif cpf_change > 20:
                    return {
                        "verdict": "worsened",
                        "detail": f"CPF悪化: ¥{baseline_cpf:,.0f}→¥{current_cpf:,.0f} ({cpf_change:+.0f}%)",
                        "confidence": 0.8,
                    }
        
        elif action_type == "budget_decrease":
            # 予算減少の場合 → 効率が維持されていれば成功
            if current_cpa > 0 and baseline_cpa > 0 and cpa_change < 10:
                return {
                    "verdict": "improved",
                    "detail": f"予算削減しつつCPA維持: ¥{baseline_cpa:,.0f}→¥{current_cpa:,.0f}",
                    "confidence": 0.7,
                }
        
        elif action_type == "pause":
            # 停止の場合 → 無駄な消化を止めた
            return {
                "verdict": "improved",
                "detail": f"消化停止: ¥{baseline_spend:,.0f}/日の消化を停止",
                "confidence": 0.9,
            }
        
        # デフォルト: 中立
        return {
            "verdict": "neutral",
            "detail": "明確な効果は確認できず",
            "confidence": 0.5,
        }

    def get_similar_learnings(
        self,
        action_type: str,
        campaign_type: str = None,
        limit: int = 3,
    ) -> list[dict]:
        """
        類似のアクションの学習結果を取得
        
        Args:
            action_type: アクションタイプ (budget_increase等)
            campaign_type: キャンペーンタイプ (traffic/sales等)
            limit: 取得件数
        
        Returns:
            list: 類似の学習結果
        """
        similar = []
        
        for learning in reversed(self.learnings):  # 新しい順
            if learning.get("action", {}).get("type") == action_type:
                similar.append(learning)
                if len(similar) >= limit:
                    break
        
        return similar

    def get_success_rate(self, action_type: str) -> dict:
        """
        特定アクションタイプの成功率を取得
        
        Returns:
            dict: {total: int, improved: int, worsened: int, success_rate: float}
        """
        total = 0
        improved = 0
        worsened = 0
        
        for learning in self.learnings:
            if learning.get("action", {}).get("type") == action_type:
                total += 1
                effect = learning.get("effect", "neutral")
                if effect == "improved":
                    improved += 1
                elif effect == "worsened":
                    worsened += 1
        
        success_rate = (improved / total * 100) if total > 0 else 0
        
        return {
            "total": total,
            "improved": improved,
            "worsened": worsened,
            "neutral": total - improved - worsened,
            "success_rate": success_rate,
        }

    def get_learning_summary(self) -> dict:
        """
        学習のサマリーを取得
        """
        return {
            "total_learnings": len(self.learnings),
            "pending_analysis": len(self.pending),
            "by_action_type": {
                "budget_increase": self.get_success_rate("budget_increase"),
                "budget_decrease": self.get_success_rate("budget_decrease"),
                "pause": self.get_success_rate("pause"),
                "resume": self.get_success_rate("resume"),
            },
            "recent_learnings": self.learnings[-5:] if self.learnings else [],
        }

    def format_learning_for_prompt(self, learnings: list[dict]) -> str:
        """
        学習結果をAIプロンプト用にフォーマット
        """
        if not learnings:
            return "過去の類似アクションの学習データはありません。"
        
        lines = ["## 過去の類似アクションの結果"]
        
        for i, l in enumerate(learnings, 1):
            effect = l.get("effect", "neutral")
            effect_icon = {"improved": "✅", "worsened": "❌", "neutral": "➖"}.get(effect, "❓")
            
            lines.append(f"\n### {i}. {effect_icon} {l.get('effect_detail', '')}")
            lines.append(f"- 実行日: {l.get('executed_at', '')[:10]}")
            lines.append(f"- アクション: {l.get('action', {}).get('type', '')}")
            
            baseline = l.get("baseline", {})
            after = l.get("after", {})
            
            if baseline.get("cpa") and after.get("cpa"):
                lines.append(f"- CPA: ¥{baseline['cpa']:,.0f} → ¥{after['cpa']:,.0f}")
            if baseline.get("roas") and after.get("roas"):
                lines.append(f"- ROAS: {baseline['roas']:.2f} → {after['roas']:.2f}")
        
        return "\n".join(lines)

