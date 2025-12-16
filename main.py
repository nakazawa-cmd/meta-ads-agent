#!/usr/bin/env python3
"""
Meta Ads Agent - メインスクリプト

Meta広告の入札自動最適化・クリエイティブ自動管理を行うツール

Usage:
    python main.py status                    # 接続状況を確認
    python main.py accounts                  # 広告アカウント一覧
    python main.py campaigns                 # キャンペーン一覧
    python main.py performance               # パフォーマンスレポート
    python main.py optimize-bids --dry-run   # 入札最適化（ドライラン）
    python main.py check-creatives           # クリエイティブチェック
    python main.py auto-pause --dry-run      # 低パフォーマンス広告を停止
    python main.py dashboard                 # ダッシュボード起動
"""
import argparse
import json
import logging
import sys
from datetime import datetime

import config
from meta_api import MetaAuth, CampaignManager, AdSetManager, AdManager, InsightsManager
from agent import PerformanceAnalyzer, BidOptimizer, CreativeManager
from notifiers import SlackNotifier


def setup_logging(verbose: bool = False):
    """ロギングを設定"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


logger = logging.getLogger(__name__)


def get_auth() -> MetaAuth:
    """認証オブジェクトを取得"""
    auth = MetaAuth()
    if not auth.initialize():
        logger.error("Meta APIの初期化に失敗しました")
        logger.error("META_ACCESS_TOKEN が正しく設定されているか確認してください")
        sys.exit(1)
    return auth


def cmd_status(args):
    """接続状況を確認"""
    print("\n" + "=" * 50)
    print("🔍 Meta API 接続状況")
    print("=" * 50)

    auth = MetaAuth()
    
    # トークン検証
    print("\n📋 アクセストークン検証中...")
    user_info = auth.verify_token()
    
    if user_info:
        print(f"✅ 認証成功")
        print(f"   ユーザー: {user_info.get('name')}")
        print(f"   ID: {user_info.get('id')}")
    else:
        print("❌ 認証失敗")
        print("   META_ACCESS_TOKEN を確認してください")
        return

    # 広告アカウント
    print("\n📋 広告アカウント取得中...")
    accounts = auth.get_ad_accounts()
    print(f"✅ {len(accounts)} 件の広告アカウントにアクセス可能")

    # Claude API
    print("\n📋 Claude API 確認中...")
    if config.ANTHROPIC_API_KEY:
        print("✅ ANTHROPIC_API_KEY が設定されています")
    else:
        print("⚠️  ANTHROPIC_API_KEY が設定されていません")

    # Slack
    print("\n📋 Slack Webhook 確認中...")
    if config.SLACK_WEBHOOK_URL:
        print("✅ SLACK_WEBHOOK_URL が設定されています")
    else:
        print("⚠️  SLACK_WEBHOOK_URL が設定されていません（オプション）")

    print("\n" + "=" * 50)


def cmd_accounts(args):
    """広告アカウント一覧を表示"""
    auth = get_auth()
    accounts = auth.get_ad_accounts()

    print("\n" + "=" * 60)
    print("📋 広告アカウント一覧")
    print("=" * 60)

    for acc in accounts:
        status_emoji = "✅" if acc["status"] == "ACTIVE" else "⏸️"
        print(f"\n{status_emoji} {acc['name']}")
        print(f"   ID: {acc['id']}")
        print(f"   ステータス: {acc['status']}")
        print(f"   通貨: {acc['currency']}")
        print(f"   タイムゾーン: {acc['timezone']}")

    print(f"\n合計: {len(accounts)} アカウント")


def cmd_campaigns(args):
    """キャンペーン一覧を表示"""
    auth = get_auth()
    
    account_id = args.account or (config.META_AD_ACCOUNT_IDS[0] if config.META_AD_ACCOUNT_IDS else None)
    if not account_id:
        logger.error("広告アカウントIDを指定してください（--account または META_AD_ACCOUNT_IDS）")
        sys.exit(1)

    ad_account = auth.get_ad_account(account_id)
    if not ad_account:
        sys.exit(1)

    campaign_mgr = CampaignManager(ad_account)
    
    status_filter = ["ACTIVE"] if args.active_only else None
    campaigns = campaign_mgr.get_campaigns(status_filter=status_filter)

    print("\n" + "=" * 60)
    print(f"📋 キャンペーン一覧 (アカウント: {account_id})")
    print("=" * 60)

    for camp in campaigns:
        status_emoji = "✅" if camp["effective_status"] == "ACTIVE" else "⏸️"
        print(f"\n{status_emoji} {camp['name']}")
        print(f"   ID: {camp['id']}")
        print(f"   ステータス: {camp['effective_status']}")
        print(f"   目的: {camp['objective']}")
        if camp['daily_budget']:
            print(f"   日予算: ¥{camp['daily_budget']:,.0f}")

    print(f"\n合計: {len(campaigns)} キャンペーン")


def cmd_performance(args):
    """パフォーマンスレポートを表示"""
    auth = get_auth()
    
    account_id = args.account or (config.META_AD_ACCOUNT_IDS[0] if config.META_AD_ACCOUNT_IDS else None)
    if not account_id:
        logger.error("広告アカウントIDを指定してください")
        sys.exit(1)

    ad_account = auth.get_ad_account(account_id)
    if not ad_account:
        sys.exit(1)

    insights_mgr = InsightsManager(ad_account)
    summary = insights_mgr.get_daily_performance_summary(days=args.days)

    print("\n" + "=" * 60)
    print(f"📊 パフォーマンスレポート")
    print(f"   期間: {summary['period']}")
    print("=" * 60)

    print(f"\n💰 広告費: ¥{summary['total_spend']:,.0f}")
    print(f"👁️  インプレッション: {summary['total_impressions']:,}")
    print(f"👆 クリック: {summary['total_clicks']:,}")
    print(f"🎯 コンバージョン: {summary['total_conversions']:,}")
    print(f"💵 CV値: ¥{summary['total_conversion_value']:,.0f}")

    print("\n--- 指標 ---")
    print(f"CTR: {summary['avg_ctr']:.2f}%")
    print(f"CPC: ¥{summary['avg_cpc']:,.0f}" if summary['avg_cpc'] else "CPC: -")
    print(f"CPA: ¥{summary['avg_cpa']:,.0f}" if summary['avg_cpa'] else "CPA: -")
    print(f"ROAS: {summary['roas']:.2f}x" if summary['roas'] else "ROAS: -")

    # Slack通知
    if args.notify:
        notifier = SlackNotifier()
        notifier.send_performance_report(account_id, summary)
        print("\n✅ Slackに通知しました")


def cmd_optimize_bids(args):
    """入札を最適化"""
    auth = get_auth()
    
    account_id = args.account or (config.META_AD_ACCOUNT_IDS[0] if config.META_AD_ACCOUNT_IDS else None)
    if not account_id:
        logger.error("広告アカウントIDを指定してください")
        sys.exit(1)

    ad_account = auth.get_ad_account(account_id)
    if not ad_account:
        sys.exit(1)

    adset_mgr = AdSetManager(ad_account)
    insights_mgr = InsightsManager(ad_account)
    analyzer = PerformanceAnalyzer()
    optimizer = BidOptimizer(adset_mgr, insights_mgr, analyzer)

    print("\n" + "=" * 60)
    print("📈 入札最適化" + (" [ドライラン]" if args.dry_run else ""))
    print("=" * 60)

    results = optimizer.optimize_all_adsets(
        target_cpa=args.target_cpa,
        target_roas=args.target_roas,
        dry_run=args.dry_run,
    )

    adjusted = [r for r in results if r.get("suggestion", {}).get("should_adjust")]
    
    print(f"\n📋 結果: {len(adjusted)}/{len(results)} 件で調整を提案")

    for r in adjusted:
        suggestion = r.get("suggestion", {})
        print(f"\n  🔧 {r.get('adset_name', r.get('adset_id'))}")
        print(f"     現在: ¥{suggestion.get('current_bid', 0):,.0f}")
        print(f"     推奨: ¥{suggestion.get('recommended_bid', 0):,.0f} ({suggestion.get('change_percent', 0):+.1f}%)")
        print(f"     理由: {suggestion.get('reason', '-')}")

    if args.notify and not args.dry_run:
        notifier = SlackNotifier()
        notifier.send_optimization_report(results, "bid")


def cmd_check_creatives(args):
    """クリエイティブをチェック"""
    auth = get_auth()
    
    account_id = args.account or (config.META_AD_ACCOUNT_IDS[0] if config.META_AD_ACCOUNT_IDS else None)
    if not account_id:
        logger.error("広告アカウントIDを指定してください")
        sys.exit(1)

    ad_account = auth.get_ad_account(account_id)
    if not ad_account:
        sys.exit(1)

    ad_mgr = AdManager(ad_account)
    insights_mgr = InsightsManager(ad_account)
    creative_mgr = CreativeManager(ad_mgr, insights_mgr)

    print("\n" + "=" * 60)
    print("🎨 クリエイティブチェック")
    print("=" * 60)

    low_performers = creative_mgr.check_low_performers(days=args.days)

    if not low_performers:
        print("\n✅ 低パフォーマンスのクリエイティブはありません")
        return

    print(f"\n⚠️  {len(low_performers)} 件の低パフォーマンスクリエイティブを検出")

    for ad in low_performers:
        perf = ad.get("performance", {})
        print(f"\n  🔴 {ad.get('ad_name', ad.get('ad_id'))}")
        print(f"     CTR: {perf.get('ctr', 0):.2f}%")
        print(f"     CVR: {perf.get('cvr', '-')}%")
        print(f"     理由: {ad.get('reason', '-')}")


def cmd_auto_pause(args):
    """低パフォーマンス広告を自動停止"""
    auth = get_auth()
    
    account_id = args.account or (config.META_AD_ACCOUNT_IDS[0] if config.META_AD_ACCOUNT_IDS else None)
    if not account_id:
        logger.error("広告アカウントIDを指定してください")
        sys.exit(1)

    ad_account = auth.get_ad_account(account_id)
    if not ad_account:
        sys.exit(1)

    ad_mgr = AdManager(ad_account)
    insights_mgr = InsightsManager(ad_account)
    creative_mgr = CreativeManager(ad_mgr, insights_mgr)

    print("\n" + "=" * 60)
    print("🔴 クリエイティブ自動停止" + (" [ドライラン]" if args.dry_run else ""))
    print("=" * 60)

    result = creative_mgr.auto_pause_low_performers(
        days=args.days,
        dry_run=args.dry_run,
        notify=args.notify,
    )

    paused = result.get("paused_ads", [])
    
    if not paused:
        print("\n✅ 停止対象のクリエイティブはありません")
        return

    action = "停止予定" if args.dry_run else "停止済み"
    print(f"\n{action}: {len(paused)} 件")

    for ad in paused:
        print(f"  - {ad.get('ad_name', ad.get('ad_id'))}: {ad.get('reason')}")


def cmd_dashboard(args):
    """Streamlitダッシュボードを起動"""
    import subprocess
    
    dashboard_path = config.BASE_DIR / "dashboard" / "app.py"
    
    if not dashboard_path.exists():
        logger.error("ダッシュボードファイルが見つかりません")
        sys.exit(1)

    print("🚀 ダッシュボードを起動中...")
    print("   ブラウザで http://localhost:8501 を開いてください")
    print("   終了するには Ctrl+C を押してください")
    
    subprocess.run(["streamlit", "run", str(dashboard_path)])


def main():
    parser = argparse.ArgumentParser(
        description="Meta Ads Agent - 広告運用自動化ツール"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細ログを表示")
    
    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # status
    subparsers.add_parser("status", help="接続状況を確認")

    # accounts
    subparsers.add_parser("accounts", help="広告アカウント一覧")

    # campaigns
    p_campaigns = subparsers.add_parser("campaigns", help="キャンペーン一覧")
    p_campaigns.add_argument("--account", "-a", help="広告アカウントID")
    p_campaigns.add_argument("--active-only", action="store_true", help="アクティブのみ")

    # performance
    p_perf = subparsers.add_parser("performance", help="パフォーマンスレポート")
    p_perf.add_argument("--account", "-a", help="広告アカウントID")
    p_perf.add_argument("--days", "-d", type=int, default=7, help="集計日数")
    p_perf.add_argument("--notify", "-n", action="store_true", help="Slackに通知")

    # optimize-bids
    p_bids = subparsers.add_parser("optimize-bids", help="入札最適化")
    p_bids.add_argument("--account", "-a", help="広告アカウントID")
    p_bids.add_argument("--target-cpa", type=float, help="目標CPA")
    p_bids.add_argument("--target-roas", type=float, help="目標ROAS")
    p_bids.add_argument("--dry-run", action="store_true", help="ドライラン")
    p_bids.add_argument("--notify", "-n", action="store_true", help="Slackに通知")

    # check-creatives
    p_check = subparsers.add_parser("check-creatives", help="クリエイティブチェック")
    p_check.add_argument("--account", "-a", help="広告アカウントID")
    p_check.add_argument("--days", "-d", type=int, default=3, help="チェック期間")

    # auto-pause
    p_pause = subparsers.add_parser("auto-pause", help="低パフォーマンス広告を停止")
    p_pause.add_argument("--account", "-a", help="広告アカウントID")
    p_pause.add_argument("--days", "-d", type=int, default=3, help="チェック期間")
    p_pause.add_argument("--dry-run", action="store_true", help="ドライラン")
    p_pause.add_argument("--notify", "-n", action="store_true", help="Slackに通知")

    # dashboard
    subparsers.add_parser("dashboard", help="ダッシュボードを起動")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "status": cmd_status,
        "accounts": cmd_accounts,
        "campaigns": cmd_campaigns,
        "performance": cmd_performance,
        "optimize-bids": cmd_optimize_bids,
        "check-creatives": cmd_check_creatives,
        "auto-pause": cmd_auto_pause,
        "dashboard": cmd_dashboard,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()


