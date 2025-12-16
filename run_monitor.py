#!/usr/bin/env python3
"""
監視システム実行スクリプト

使い方:
  # 手動で1回チェック実行
  python run_monitor.py --check
  
  # 日次レポートを送信
  python run_monitor.py --report
  
  # Slack接続テスト
  python run_monitor.py --test-slack
  
  # スケジューラーを起動（バックグラウンド）
  python run_monitor.py --start
"""
import argparse
import logging
import sys
from pathlib import Path

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# パス設定
sys.path.insert(0, str(Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(description="Meta Ads 監視システム")
    parser.add_argument("--check", action="store_true", help="手動チェック実行")
    parser.add_argument("--report", action="store_true", help="日次レポート送信")
    parser.add_argument("--test-slack", action="store_true", help="Slack接続テスト")
    parser.add_argument("--start", action="store_true", help="スケジューラー起動")
    parser.add_argument("--accounts", nargs="+", help="監視対象アカウントID")
    
    args = parser.parse_args()
    
    # エージェント初期化
    from agent import IntegratedAgent
    agent = IntegratedAgent()
    
    # 監視対象アカウント（優先順位: 引数 > 設定ファイル > Meta API）
    account_ids = args.accounts
    
    if not account_ids:
        # 設定ファイルから取得
        try:
            from automation.config_manager import get_config_manager
            config_manager = get_config_manager()
            account_ids = config_manager.get_enabled_account_ids()
            if account_ids:
                logger.info(f"設定ファイルから{len(account_ids)}アカウントを取得")
        except Exception as e:
            logger.warning(f"設定ファイル読み込みエラー: {e}")
    
    if not account_ids and agent.meta_initialized and agent.meta_auth:
        # Meta APIから全アカウントを取得（フォールバック）
        accounts = agent.meta_auth.get_ad_accounts()
        account_ids = [a["id"] for a in accounts]
        logger.info(f"Meta APIから{len(account_ids)}アカウントを取得（全アカウント）")
    
    if not account_ids:
        logger.error("監視対象アカウントがありません")
        logger.error("ダッシュボードの「自動運用」→「設定」で監視対象を設定してください")
        return
    
    # 監視エンジン
    from automation.monitor import PerformanceMonitor
    from automation.notifier import SlackNotifier
    from automation.scheduler import AutomationScheduler
    
    monitor = PerformanceMonitor(integrated_agent=agent)
    notifier = SlackNotifier()
    scheduler = AutomationScheduler(
        monitor=monitor,
        notifier=notifier,
        account_ids=account_ids,
    )
    
    if args.test_slack:
        logger.info("Slack接続テスト...")
        if notifier.test_connection():
            print("✅ Slack接続成功！")
        else:
            print("❌ Slack接続失敗。Webhook URLを確認してください。")
    
    elif args.check:
        logger.info("手動チェック実行...")
        results = scheduler.run_check_now()
        
        summary = results.get("summary", {})
        print(f"\n{summary.get('status_message', '')}")
        print(f"アラート: {summary.get('total_alerts', 0)}件")
        print(f"チャンス: {summary.get('total_opportunities', 0)}件")
        
        if results.get("alerts"):
            print("\n🚨 アラート:")
            for alert in results["alerts"]:
                severity = "🔴" if alert.get("severity") == "high" else "🟡"
                print(f"  {severity} {alert.get('campaign_name')}: {alert.get('message')}")
        
        if results.get("opportunities"):
            print("\n🚀 チャンス:")
            for opp in results["opportunities"]:
                print(f"  🟢 {opp.get('campaign_name')}: {opp.get('message')}")
    
    elif args.report:
        logger.info("日次レポート送信...")
        if scheduler.run_daily_report():
            print("✅ 日次レポート送信成功！")
        else:
            print("❌ 日次レポート送信失敗")
    
    elif args.start:
        logger.info("スケジューラー起動...")
        print("🤖 Meta Ads AI Agent 自動監視を開始します")
        print(f"  - 日次レポート: 毎日 {scheduler.schedule['daily_report_hour']}:{scheduler.schedule['daily_report_minute']:02d}")
        print(f"  - 定期チェック: {scheduler.schedule['check_interval_minutes']}分ごと")
        print("  - Ctrl+C で停止")
        
        try:
            scheduler.start()
            # メインスレッドを維持
            while scheduler.is_running:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n停止中...")
            scheduler.stop()
            print("✅ 停止完了")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
