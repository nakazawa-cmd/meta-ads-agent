"""
アクション実行モジュール
推奨アクションを実行（Phase 2以降で本格実装）
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ActionQueue:
    """
    承認待ちアクションのキュー
    """
    
    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = str(Path(__file__).parent.parent / "storage" / "actions")
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.queue_file = self.storage_dir / "pending_actions.json"
        self.history_file = self.storage_dir / "action_history.json"
        
        self.pending = self._load_json(self.queue_file, [])
        self.history = self._load_json(self.history_file, [])
        
        logger.info(f"ActionQueue初期化: 待機中{len(self.pending)}件")
    
    def _load_json(self, path: Path, default: Any) -> Any:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return default
    
    def _save_json(self, path: Path, data: Any):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_action(self, action: dict) -> str:
        """アクションを承認キューに追加"""
        action_id = str(uuid.uuid4())[:8]
        
        queued_action = {
            "id": action_id,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "action": action,
        }
        
        self.pending.append(queued_action)
        self._save_json(self.queue_file, self.pending)
        
        logger.info(f"アクション追加: {action_id}")
        return action_id
    
    def get_pending(self) -> list[dict]:
        """承認待ちアクションを取得"""
        return self.pending
    
    def approve(self, action_id: str) -> dict | None:
        """アクションを承認"""
        for i, action in enumerate(self.pending):
            if action["id"] == action_id:
                action["status"] = "approved"
                action["approved_at"] = datetime.now().isoformat()
                
                # 履歴に移動
                self.history.append(action)
                self.pending.pop(i)
                
                self._save_json(self.queue_file, self.pending)
                self._save_json(self.history_file, self.history)
                
                logger.info(f"アクション承認: {action_id}")
                return action
        
        return None
    
    def reject(self, action_id: str, reason: str = "") -> dict | None:
        """アクションを却下"""
        for i, action in enumerate(self.pending):
            if action["id"] == action_id:
                action["status"] = "rejected"
                action["rejected_at"] = datetime.now().isoformat()
                action["reject_reason"] = reason
                
                # 履歴に移動
                self.history.append(action)
                self.pending.pop(i)
                
                self._save_json(self.queue_file, self.pending)
                self._save_json(self.history_file, self.history)
                
                logger.info(f"アクション却下: {action_id}")
                return action
        
        return None

    def add_to_history(self, item: dict):
        """履歴に直接追加（直接実行用）"""
        self.history.append(item)
        self._save_json(self.history_file, self.history)
    
    def mark_executed(self, action_id: str, result: dict):
        """実行完了をマーク"""
        for action in self.history:
            if action["id"] == action_id:
                action["status"] = "executed"
                action["executed_at"] = datetime.now().isoformat()
                action["result"] = result
                self._save_json(self.history_file, self.history)
                logger.info(f"アクション実行完了: {action_id}")
                return
    
    def get_history(self, limit: int = 50) -> list[dict]:
        """実行履歴を取得"""
        return self.history[-limit:]
    
    def clear_pending(self):
        """承認待ちをクリア"""
        self.pending = []
        self._save_json(self.queue_file, self.pending)


class ActionExecutor:
    """
    アクション実行クラス
    
    Phase 1: 実行せず通知のみ
    Phase 2: 承認後に実行
    Phase 3: 自動実行
    
    + 実行履歴から学習して精度向上
    """

    def __init__(self, integrated_agent=None, mode: str = "approval_required"):
        """
        初期化
        
        Args:
            integrated_agent: IntegratedAgentインスタンス
            mode: 実行モード
                - "notify_only": 通知のみ（Phase 1）
                - "approval_required": 承認後実行（Phase 2）
                - "auto_execute": 自動実行（Phase 3）
        """
        self.agent = integrated_agent
        self.mode = mode
        self.queue = ActionQueue()
        
        # 学習モジュール
        from automation.learning import ActionLearner
        self.learner = ActionLearner(integrated_agent=integrated_agent)
        
        # 安全装置の設定
        self.safety_limits = {
            "max_budget_increase_percent": 20,  # 最大20%増
            "max_daily_budget": 500000,  # 最大日予算50万円
            "min_learning_days": 3,  # 学習期間最低3日
            "require_cv_for_increase": True,  # 増額にはCV必須
        }
        
        logger.info(f"ActionExecutor初期化: mode={mode}")

    def set_mode(self, mode: str):
        """実行モードを変更"""
        self.mode = mode
        logger.info(f"実行モード変更: {mode}")

    def execute(self, action: dict) -> dict:
        """
        アクションを実行
        
        Args:
            action: 実行するアクション
                {
                    "type": "budget_increase" | "budget_decrease" | "pause" | "resume",
                    "campaign_id": "...",
                    "params": {...}
                }
        
        Returns:
            dict: 実行結果
        """
        action_type = action.get("type")
        
        if self.mode == "notify_only":
            return {
                "success": True,
                "executed": False,
                "mode": "notify_only",
                "message": "通知モードのため実行はスキップ",
                "action": action,
            }
        
        # 安全チェック
        safety_check = self._safety_check(action)
        if not safety_check["passed"]:
            return {
                "success": False,
                "executed": False,
                "message": f"安全チェック失敗: {safety_check['reason']}",
                "action": action,
            }
        
        # アクション実行
        if action_type == "budget_change":
            return self._execute_budget_change(action, increase=True)
        elif action_type == "budget_increase":
            return self._execute_budget_change(action, increase=True)
        elif action_type == "budget_decrease":
            return self._execute_budget_change(action, increase=False)
        elif action_type == "status_change":
            new_status = action.get("params", {}).get("new_status", "PAUSED")
            return self._execute_status_change(action, status=new_status)
        elif action_type == "pause":
            return self._execute_status_change(action, status="PAUSED")
        elif action_type == "resume":
            return self._execute_status_change(action, status="ACTIVE")
        else:
            return {
                "success": False,
                "executed": False,
                "message": f"未対応のアクションタイプ: {action_type}",
            }

    def _safety_check(self, action: dict) -> dict:
        """安全チェック"""
        action_type = action.get("type")
        params = action.get("params", {})
        
        if action_type == "budget_increase":
            # 増額率チェック
            increase_percent = params.get("increase_percent", 0)
            if increase_percent > self.safety_limits["max_budget_increase_percent"]:
                return {
                    "passed": False,
                    "reason": f"増額率{increase_percent}%は上限{self.safety_limits['max_budget_increase_percent']}%を超えています",
                }
            
            # 最大日予算チェック
            new_budget = params.get("new_budget", 0)
            if new_budget > self.safety_limits["max_daily_budget"]:
                return {
                    "passed": False,
                    "reason": f"新予算¥{new_budget:,}は上限¥{self.safety_limits['max_daily_budget']:,}を超えています",
                }
        
        return {"passed": True}

    def _execute_budget_change(self, action: dict, increase: bool) -> dict:
        """予算変更を実行"""
        if not self.agent or not self.agent.meta_initialized:
            return {
                "success": False,
                "executed": False,
                "message": "Meta API未接続",
            }
        
        account_id = action.get("account_id")
        campaign_id = action.get("campaign_id")
        params = action.get("params", {})
        new_budget = params.get("new_budget")
        
        if not campaign_id or not new_budget:
            return {
                "success": False,
                "executed": False,
                "message": "campaign_idまたはnew_budgetが不足",
            }
        
        try:
            # Meta API経由で予算更新
            managers = self.agent._get_managers(account_id)
            if not managers:
                return {
                    "success": False,
                    "executed": False,
                    "message": "マネージャー取得失敗",
                }
            
            # 実行前のパフォーマンスを取得（学習用）
            baseline = {}
            try:
                insights = managers["insights"].get_campaign_insights(campaign_id, date_preset="last_7d")
                if insights:
                    baseline = {
                        "spend": insights.get("spend", 0),
                        "cpa": insights.get("cpa", 0),
                        "roas": insights.get("roas", 0),
                        "ctr": insights.get("ctr", 0),
                        "cpf": insights.get("cpf", 0),
                    }
            except Exception as e:
                logger.warning(f"ベースライン取得失敗: {e}")
            
            success = managers["campaign"].update_campaign_budget(
                campaign_id=campaign_id,
                daily_budget=int(new_budget),
            )
            
            if success:
                logger.info(f"✅ 予算変更実行: {campaign_id} -> ¥{new_budget:,.0f}")
                
                # 学習レコード作成（24時間後に効果分析）
                if baseline and self.learner:
                    self.learner.record_action_with_baseline(
                        action=action,
                        campaign_id=campaign_id,
                        account_id=account_id,
                        baseline_metrics=baseline,
                    )
                
                return {
                    "success": True,
                    "executed": True,
                    "message": f"予算を¥{new_budget:,.0f}に変更しました",
                    "action": action,
                }
            else:
                return {
                    "success": False,
                    "executed": False,
                    "message": "Meta APIからの予算更新に失敗しました",
                }
            
        except Exception as e:
            logger.error(f"予算変更エラー: {e}")
            return {
                "success": False,
                "executed": False,
                "message": f"予算変更エラー: {e}",
            }

    def _execute_status_change(self, action: dict, status: str) -> dict:
        """ステータス変更を実行"""
        if not self.agent or not self.agent.meta_initialized:
            return {
                "success": False,
                "executed": False,
                "message": "Meta API未接続",
            }
        
        account_id = action.get("account_id")
        campaign_id = action.get("campaign_id")
        params = action.get("params", {})
        new_status = params.get("new_status", status)
        
        if not campaign_id:
            return {
                "success": False,
                "executed": False,
                "message": "campaign_idが不足",
            }
        
        try:
            # Meta API経由でステータス更新
            managers = self.agent._get_managers(account_id)
            if not managers:
                return {
                    "success": False,
                    "executed": False,
                    "message": "マネージャー取得失敗",
                }
            
            success = managers["campaign"].update_campaign_status(
                campaign_id=campaign_id,
                status=new_status,
            )
            
            if success:
                logger.info(f"✅ ステータス変更実行: {campaign_id} -> {new_status}")
                return {
                    "success": True,
                    "executed": True,
                    "message": f"ステータスを{new_status}に変更しました",
                    "action": action,
                }
            else:
                return {
                    "success": False,
                    "executed": False,
                    "message": "Meta APIからのステータス更新に失敗しました",
                }
            
        except Exception as e:
            logger.error(f"ステータス変更エラー: {e}")
            return {
                "success": False,
                "executed": False,
                "message": f"ステータス変更エラー: {e}",
            }

    def propose_action(self, action: dict) -> str:
        """
        アクションを提案（承認キューに追加）
        
        Args:
            action: 提案するアクション
        
        Returns:
            str: アクションID
        """
        return self.queue.add_action(action)

    def get_pending_actions(self) -> list:
        """承認待ちアクションを取得"""
        return self.queue.get_pending()

    def approve_action(self, action_id: str) -> dict:
        """
        アクションを承認して実行
        
        Args:
            action_id: アクションID
        
        Returns:
            dict: 実行結果
        """
        # 承認
        approved = self.queue.approve(action_id)
        if not approved:
            return {"success": False, "message": f"アクション {action_id} が見つかりません"}
        
        # 実行
        result = self.execute(approved["action"])
        
        # 結果を記録
        self.queue.mark_executed(action_id, result)
        
        return result

    def reject_action(self, action_id: str, reason: str = "") -> dict:
        """
        アクションを却下
        
        Args:
            action_id: アクションID
            reason: 却下理由
        
        Returns:
            dict: 結果
        """
        rejected = self.queue.reject(action_id, reason)
        if not rejected:
            return {"success": False, "message": f"アクション {action_id} が見つかりません"}
        
        return {"success": True, "message": f"アクション {action_id} を却下しました"}

    def get_action_history(self, limit: int = 50) -> list:
        """実行履歴を取得"""
        return self.queue.get_history(limit)

    def create_budget_action(
        self,
        campaign_id: str,
        campaign_name: str,
        account_id: str,
        current_budget: float,
        new_budget: float,
        reason: str,
    ) -> str:
        """
        予算変更アクションを作成して提案
        
        Returns:
            str: アクションID
        """
        action = {
            "type": "budget_change",
            "account_id": account_id,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "params": {
                "current_budget": current_budget,
                "new_budget": new_budget,
                "change_percent": ((new_budget - current_budget) / current_budget * 100) if current_budget > 0 else 0,
            },
            "reason": reason,
        }
        
        return self.propose_action(action)

    def create_status_action(
        self,
        campaign_id: str,
        campaign_name: str,
        account_id: str,
        new_status: str,
        reason: str,
    ) -> str:
        """
        ステータス変更アクションを作成して提案
        
        Returns:
            str: アクションID
        """
        action = {
            "type": "status_change",
            "account_id": account_id,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "params": {
                "new_status": new_status,
            },
            "reason": reason,
        }
        
        return self.propose_action(action)

    # =========================================================================
    # 直接実行メソッド（承認キューをスキップ）
    # =========================================================================

    def execute_budget_change_direct(
        self,
        campaign_id: str,
        new_budget: int,
        account_id: str,
    ) -> dict:
        """
        予算変更を直接実行（承認キューなし）
        
        Args:
            campaign_id: キャンペーンID
            new_budget: 新しい予算（円）
            account_id: アカウントID
        
        Returns:
            dict: 実行結果
        """
        action = {
            "type": "budget_change",
            "account_id": account_id,
            "campaign_id": campaign_id,
            "params": {
                "new_budget": new_budget,
            },
        }
        
        # 安全チェック
        safety = self._safety_check(action)
        if not safety.get("passed"):
            return {
                "success": False,
                "error": safety.get("reason", "安全チェック失敗"),
            }
        
        # 実行
        result = self._execute_budget_change(action, increase=True)
        
        # 履歴に記録
        self.queue.add_to_history({
            "action": action,
            "result": result,
            "executed_at": __import__("datetime").datetime.now().isoformat(),
            "type": "direct_execution",
        })
        
        return result

    def execute_status_change_direct(
        self,
        campaign_id: str,
        new_status: str,
        account_id: str,
    ) -> dict:
        """
        ステータス変更を直接実行（承認キューなし）
        
        Args:
            campaign_id: キャンペーンID
            new_status: 新しいステータス（ACTIVE/PAUSED）
            account_id: アカウントID
        
        Returns:
            dict: 実行結果
        """
        action = {
            "type": "status_change",
            "account_id": account_id,
            "campaign_id": campaign_id,
            "params": {
                "new_status": new_status,
            },
        }
        
        # 実行
        result = self._execute_status_change(action, status=new_status)
        
        # 履歴に記録
        self.queue.add_to_history({
            "action": action,
            "result": result,
            "executed_at": __import__("datetime").datetime.now().isoformat(),
            "type": "direct_execution",
        })
        
        return result
