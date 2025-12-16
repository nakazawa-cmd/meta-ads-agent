"""
キャンペーン目標値管理モジュール
ダッシュボードから動的に目標値を設定・変更
"""
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TARGETS_FILE = Path(__file__).parent.parent / "storage" / "campaign_targets.json"


class TargetManager:
    """
    キャンペーン目標値を管理するクラス
    
    機能:
    1. キャンペーン別の目標値（CPF, CPA, ROAS等）を管理
    2. フェーズごとに目標値を変更可能
    3. JSONファイルに永続化
    """

    def __init__(self):
        self.targets_file = TARGETS_FILE
        self.targets = self._load_targets()
        logger.info("TargetManager初期化完了")

    def _load_targets(self) -> dict:
        """目標値をファイルから読み込み"""
        if self.targets_file.exists():
            try:
                with open(self.targets_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"目標値読み込みエラー: {e}")
        
        # デフォルト値
        return {
            "defaults": {
                "traffic": {
                    "target_cpf": 50,
                    "cpf_warning": 100,
                    "cpf_critical": 200,
                },
                "sales": {
                    "target_cpa": 5000,
                    "target_roas": 3.0,
                },
            },
            "campaigns": {},
        }

    def _save_targets(self):
        """目標値をファイルに保存"""
        try:
            self.targets_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.targets_file, "w", encoding="utf-8") as f:
                json.dump(self.targets, f, ensure_ascii=False, indent=2)
            logger.info("目標値を保存しました")
        except Exception as e:
            logger.error(f"目標値保存エラー: {e}")

    def get_campaign_targets(self, campaign_id: str, campaign_type: str = "traffic") -> dict:
        """
        キャンペーンの目標値を取得
        
        Args:
            campaign_id: キャンペーンID
            campaign_type: キャンペーンタイプ（"traffic" or "sales"）
        
        Returns:
            dict: 目標値
        """
        # キャンペーン固有の設定があればそれを使用
        if campaign_id in self.targets.get("campaigns", {}):
            return self.targets["campaigns"][campaign_id]
        
        # なければデフォルト値
        return self.targets.get("defaults", {}).get(campaign_type, {})

    def set_campaign_targets(
        self,
        campaign_id: str,
        campaign_name: str,
        targets: dict,
    ):
        """
        キャンペーンの目標値を設定
        
        Args:
            campaign_id: キャンペーンID
            campaign_name: キャンペーン名（表示用）
            targets: 目標値（target_cpf, target_cpa, target_roas など）
        """
        if "campaigns" not in self.targets:
            self.targets["campaigns"] = {}
        
        self.targets["campaigns"][campaign_id] = {
            "name": campaign_name,
            **targets,
            "updated_at": __import__("datetime").datetime.now().isoformat(),
        }
        
        self._save_targets()
        logger.info(f"キャンペーン {campaign_name} の目標値を更新: {targets}")

    def set_default_targets(self, campaign_type: str, targets: dict):
        """
        デフォルト目標値を設定
        
        Args:
            campaign_type: "traffic" or "sales"
            targets: 目標値
        """
        if "defaults" not in self.targets:
            self.targets["defaults"] = {}
        
        self.targets["defaults"][campaign_type] = targets
        self._save_targets()
        logger.info(f"{campaign_type}のデフォルト目標値を更新: {targets}")

    def get_all_campaign_targets(self) -> dict:
        """全キャンペーンの目標値を取得"""
        return self.targets.get("campaigns", {})

    def get_defaults(self) -> dict:
        """デフォルト目標値を取得"""
        return self.targets.get("defaults", {})

    def remove_campaign_targets(self, campaign_id: str):
        """キャンペーン固有の目標値を削除（デフォルトに戻す）"""
        if campaign_id in self.targets.get("campaigns", {}):
            del self.targets["campaigns"][campaign_id]
            self._save_targets()
            logger.info(f"キャンペーン {campaign_id} の目標値を削除（デフォルトに戻す）")


# シングルトンインスタンス
_target_manager = None


def get_target_manager() -> TargetManager:
    """TargetManagerのシングルトンインスタンスを取得"""
    global _target_manager
    if _target_manager is None:
        _target_manager = TargetManager()
    return _target_manager

