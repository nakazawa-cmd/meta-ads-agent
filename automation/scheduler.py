"""
自動実行スケジューラー
定期的にパフォーマンスチェックを実行
"""
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable

logger = logging.getLogger(__name__)


class AutomationScheduler:
    """
    自動実行スケジューラー
    
    機能:
    1. 定期チェックのスケジューリング
    2. 日次レポートの自動送信
    3. アラートの即時通知
    """

    def __init__(
        self,
        monitor=None,
        notifier=None,
        account_ids: list[str] = None,
    ):
        """
        初期化
        
        Args:
            monitor: PerformanceMonitorインスタンス
            notifier: SlackNotifierインスタンス
            account_ids: 監視対象アカウントIDリスト（省略時は設定ファイルから読み込み）
        """
        self.monitor = monitor
        self.notifier = notifier
        
        self._running = False
        self._thread = None
        self._tasks = []
        
        # 設定マネージャーを初期化
        try:
            from automation.config_manager import get_config_manager
            self.config_manager = get_config_manager()
        except Exception as e:
            logger.warning(f"設定マネージャー初期化エラー: {e}")
            self.config_manager = None
        
        # アカウントIDの設定（引数 > 設定ファイル）
        if account_ids:
            self.account_ids = account_ids
        elif self.config_manager:
            self.account_ids = self.config_manager.get_enabled_account_ids()
        else:
            self.account_ids = []
        
        # スケジュール設定を読み込み
        if self.config_manager:
            saved_schedule = self.config_manager.get_schedule()
            self.schedule = {
                "daily_report_hour": saved_schedule.get("daily_report_hour", 9),
                "daily_report_minute": saved_schedule.get("daily_report_minute", 0),
                "check_interval_minutes": saved_schedule.get("check_interval_minutes", 60),
            }
        else:
            self.schedule = {
                "daily_report_hour": 9,
                "daily_report_minute": 0,
                "check_interval_minutes": 60,
            }
        
        logger.info(f"AutomationScheduler初期化完了: 監視対象{len(self.account_ids)}アカウント")

    def set_schedule(
        self,
        daily_report_hour: int = 9,
        daily_report_minute: int = 0,
        check_interval_minutes: int = 60,
    ):
        """スケジュールを設定"""
        self.schedule = {
            "daily_report_hour": daily_report_hour,
            "daily_report_minute": daily_report_minute,
            "check_interval_minutes": check_interval_minutes,
        }
        logger.info(f"スケジュール設定: {self.schedule}")

    def set_accounts(self, account_ids: list[str]):
        """監視対象アカウントを設定"""
        self.account_ids = account_ids
        logger.info(f"監視アカウント設定: {len(account_ids)}件")

    def run_check_now(self) -> dict:
        """
        今すぐチェックを実行
        
        Returns:
            dict: 監視結果
        """
        if not self.monitor:
            logger.error("Monitorが未設定")
            return {"error": "Monitor未設定"}
        
        if not self.account_ids:
            logger.error("監視アカウントが未設定")
            return {"error": "監視アカウント未設定"}
        
        logger.info(f"手動チェック開始: {len(self.account_ids)}アカウント")
        
        # 監視実行
        results = self.monitor.check_all_accounts(self.account_ids)
        
        # 緊急アラートがあれば即時通知
        if self.notifier:
            high_alerts = [
                a for a in results.get("alerts", [])
                if a.get("severity") == "high"
            ]
            for alert in high_alerts:
                self.notifier.send_alert(alert)
        
        logger.info(f"チェック完了: アラート{len(results.get('alerts', []))}件")
        return results

    def run_daily_report(self) -> bool:
        """
        日次レポートを実行
        
        Returns:
            bool: 送信成功したか
        """
        if not self.monitor or not self.notifier:
            logger.error("MonitorまたはNotifierが未設定")
            return False
        
        logger.info("日次レポート生成開始")
        
        # 監視実行
        results = self.run_check_now()
        
        if "error" in results:
            logger.error(f"日次レポートエラー: {results['error']}")
            return False
        
        # レポート送信
        success = self.notifier.send_daily_report(results)
        
        logger.info(f"日次レポート送信: {'成功' if success else '失敗'}")
        return success

    def start(self):
        """スケジューラーを開始（バックグラウンド）"""
        if self._running:
            logger.warning("スケジューラーは既に実行中です")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("スケジューラー開始")

    def stop(self):
        """スケジューラーを停止"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("スケジューラー停止")

    def _run_loop(self):
        """メインループ"""
        last_check = None
        last_daily_report = None
        
        while self._running:
            now = datetime.now()
            
            # 通知設定を取得
            notifications = {}
            if self.config_manager:
                notifications = self.config_manager.get_notifications()
            send_hourly = notifications.get("send_hourly_alerts", True)
            send_daily = notifications.get("send_daily_report", True)
            severity_threshold = notifications.get("alert_severity_threshold", "medium")
            
            # 定期チェック（毎時間）
            check_interval = timedelta(minutes=self.schedule["check_interval_minutes"])
            if last_check is None or (now - last_check) >= check_interval:
                try:
                    logger.info(f"[定期チェック] {now.strftime('%Y-%m-%d %H:%M')} 実行開始")
                    results = self.run_check_now()
                    last_check = now
                    
                    # アラートがあれば即時Slack通知（通知設定に従う）
                    alerts = results.get("alerts", [])
                    if alerts and self.notifier and send_hourly:
                        # 閾値でフィルタリング
                        severity_order = {"low": 0, "medium": 1, "high": 2}
                        threshold_level = severity_order.get(severity_threshold, 1)
                        filtered_alerts = [
                            a for a in alerts
                            if severity_order.get(a.get("severity", "medium"), 1) >= threshold_level
                        ]
                        
                        if filtered_alerts:
                            logger.info(f"[定期チェック] {len(filtered_alerts)}件のアラートを通知")
                            results["alerts"] = filtered_alerts
                            self.notifier.send_hourly_alert_summary(results)
                        else:
                            logger.info(f"[定期チェック] {len(alerts)}件のアラート検出、閾値未満のため通知スキップ")
                    else:
                        logger.info("[定期チェック] 異常なし")
                        
                except Exception as e:
                    logger.error(f"定期チェックエラー: {e}")
            
            # 日次レポート（毎朝9時に提案含む）
            report_hour = self.schedule["daily_report_hour"]
            report_minute = self.schedule["daily_report_minute"]
            
            if (now.hour == report_hour and 
                now.minute >= report_minute and 
                now.minute < report_minute + 5):
                
                if last_daily_report is None or last_daily_report.date() < now.date():
                    try:
                        if send_daily:
                            logger.info(f"[日次レポート] {now.strftime('%Y-%m-%d %H:%M')} 実行開始")
                            self.run_daily_report()
                        else:
                            logger.info("[日次レポート] 通知設定OFFのためスキップ")
                        last_daily_report = now
                    except Exception as e:
                        logger.error(f"日次レポートエラー: {e}")
            
            # 1分待機
            time.sleep(60)

    @property
    def is_running(self) -> bool:
        """実行中かどうか"""
        return self._running

    def get_status(self) -> dict:
        """スケジューラーの状態を取得"""
        return {
            "running": self._running,
            "schedule": self.schedule,
            "account_ids": self.account_ids,
            "monitor_set": self.monitor is not None,
            "notifier_set": self.notifier is not None,
        }
