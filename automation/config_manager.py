"""
監視設定管理モジュール
監視対象アカウント、スケジュール等を管理
"""
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_FILE = Path(__file__).parent.parent / "storage" / "monitor_config.json"


class MonitorConfigManager:
    """
    監視設定を管理するクラス
    
    機能:
    1. 監視対象アカウントの管理
    2. スケジュール設定
    3. 通知設定
    """

    def __init__(self):
        self.config_file = CONFIG_FILE
        self.config = self._load_config()
        logger.info("MonitorConfigManager初期化完了")

    def _load_config(self) -> dict:
        """設定をファイルから読み込み"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"設定読み込みエラー: {e}")
        
        # デフォルト設定
        return {
            "enabled_accounts": [],
            "schedule": {
                "check_interval_minutes": 60,
                "daily_report_hour": 9,
                "daily_report_minute": 0,
            },
            "notifications": {
                "send_hourly_alerts": True,
                "send_daily_report": True,
                "alert_severity_threshold": "medium",
            },
        }

    def _save_config(self):
        """設定をファイルに保存"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info("監視設定を保存しました")
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")

    # =========================================================================
    # アカウント管理
    # =========================================================================

    def get_enabled_accounts(self) -> list[dict]:
        """
        監視対象アカウント一覧を取得
        
        Returns:
            list[dict]: [{"id": "act_xxx", "name": "アカウント名", "enabled": True}, ...]
        """
        return self.config.get("enabled_accounts", [])

    def get_enabled_account_ids(self) -> list[str]:
        """
        有効な監視対象アカウントIDのみ取得
        
        Returns:
            list[str]: ["act_xxx", "act_yyy", ...]
        """
        accounts = self.get_enabled_accounts()
        return [a["id"] for a in accounts if a.get("enabled", True)]

    def set_enabled_accounts(self, accounts: list[dict]):
        """
        監視対象アカウントを設定
        
        Args:
            accounts: [{"id": "act_xxx", "name": "アカウント名", "enabled": True}, ...]
        """
        self.config["enabled_accounts"] = accounts
        self._save_config()
        logger.info(f"監視対象アカウントを更新: {len(accounts)}件")

    def add_account(self, account_id: str, account_name: str, enabled: bool = True):
        """アカウントを追加"""
        accounts = self.get_enabled_accounts()
        
        # 既存チェック
        for acc in accounts:
            if acc["id"] == account_id:
                acc["name"] = account_name
                acc["enabled"] = enabled
                self._save_config()
                return
        
        # 新規追加
        accounts.append({
            "id": account_id,
            "name": account_name,
            "enabled": enabled,
        })
        self.config["enabled_accounts"] = accounts
        self._save_config()

    def remove_account(self, account_id: str):
        """アカウントを削除"""
        accounts = self.get_enabled_accounts()
        self.config["enabled_accounts"] = [a for a in accounts if a["id"] != account_id]
        self._save_config()

    def toggle_account(self, account_id: str, enabled: bool):
        """アカウントの有効/無効を切り替え"""
        accounts = self.get_enabled_accounts()
        for acc in accounts:
            if acc["id"] == account_id:
                acc["enabled"] = enabled
                break
        self._save_config()

    # =========================================================================
    # スケジュール設定
    # =========================================================================

    def get_schedule(self) -> dict:
        """スケジュール設定を取得"""
        return self.config.get("schedule", {
            "check_interval_minutes": 60,
            "daily_report_hour": 9,
            "daily_report_minute": 0,
        })

    def set_schedule(
        self,
        check_interval_minutes: int = None,
        daily_report_hour: int = None,
        daily_report_minute: int = None,
    ):
        """スケジュール設定を更新"""
        schedule = self.get_schedule()
        
        if check_interval_minutes is not None:
            schedule["check_interval_minutes"] = check_interval_minutes
        if daily_report_hour is not None:
            schedule["daily_report_hour"] = daily_report_hour
        if daily_report_minute is not None:
            schedule["daily_report_minute"] = daily_report_minute
        
        self.config["schedule"] = schedule
        self._save_config()

    # =========================================================================
    # 通知設定
    # =========================================================================

    def get_notifications(self) -> dict:
        """通知設定を取得"""
        return self.config.get("notifications", {
            "send_hourly_alerts": True,
            "send_daily_report": True,
            "alert_severity_threshold": "medium",
        })

    def set_notifications(
        self,
        send_hourly_alerts: bool = None,
        send_daily_report: bool = None,
        alert_severity_threshold: str = None,
    ):
        """通知設定を更新"""
        notifications = self.get_notifications()
        
        if send_hourly_alerts is not None:
            notifications["send_hourly_alerts"] = send_hourly_alerts
        if send_daily_report is not None:
            notifications["send_daily_report"] = send_daily_report
        if alert_severity_threshold is not None:
            notifications["alert_severity_threshold"] = alert_severity_threshold
        
        self.config["notifications"] = notifications
        self._save_config()


# シングルトンインスタンス
_config_manager = None


def get_config_manager() -> MonitorConfigManager:
    """MonitorConfigManagerのシングルトンインスタンスを取得"""
    global _config_manager
    if _config_manager is None:
        _config_manager = MonitorConfigManager()
    return _config_manager

