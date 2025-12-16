"""
Slack通知モジュール
アラート、レポート、推奨アクションをSlackに送信
"""
import json
import logging
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)


class SlackNotifier:
    """
    Slack通知を送信するクラス
    
    機能:
    1. アラート通知（緊急度別）
    2. 日次レポート
    3. 推奨アクション通知
    4. チャンス通知
    """

    def __init__(self, webhook_url: str = None):
        """
        初期化
        
        Args:
            webhook_url: Slack Webhook URL
        """
        if webhook_url:
            self.webhook_url = webhook_url
        else:
            import config
            self.webhook_url = getattr(config, "SLACK_WEBHOOK_URL", None)
        
        if not self.webhook_url:
            logger.warning("Slack Webhook URLが設定されていません")

    def send_message(self, text: str, blocks: list = None) -> bool:
        """
        メッセージを送信
        
        Args:
            text: フォールバックテキスト
            blocks: Block Kit形式のブロック
        
        Returns:
            bool: 送信成功したか
        """
        if not self.webhook_url:
            logger.error("Webhook URLが未設定")
            return False
        
        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Slack通知送信成功")
            return True
        except Exception as e:
            logger.error(f"Slack通知エラー: {e}")
            return False

    def send_daily_report(self, monitor_results: dict) -> bool:
        """
        日次レポートを送信
        
        Args:
            monitor_results: PerformanceMonitorの結果
        
        Returns:
            bool: 送信成功したか
        """
        summary = monitor_results.get("summary", {})
        alerts = monitor_results.get("alerts", [])
        opportunities = monitor_results.get("opportunities", [])
        
        # ヘッダー
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 Meta広告 日次レポート ({datetime.now().strftime('%Y/%m/%d')})",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": summary.get("status_message", ""),
                },
            },
            {"type": "divider"},
        ]
        
        # サマリー統計
        blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*チェックアカウント数*\n{summary.get('accounts_checked', 0)}"},
                {"type": "mrkdwn", "text": f"*アラート*\n{summary.get('total_alerts', 0)}件"},
                {"type": "mrkdwn", "text": f"*緊急アラート*\n{summary.get('high_alerts', 0)}件"},
                {"type": "mrkdwn", "text": f"*拡大チャンス*\n{summary.get('total_opportunities', 0)}件"},
            ],
        })
        
        # アラート詳細
        if alerts:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*🚨 アラート*"},
            })
            
            for alert in alerts[:5]:  # 最大5件
                severity_emoji = "🔴" if alert.get("severity") == "high" else "🟡"
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{severity_emoji} *{alert.get('campaign_name', '')}*\n{alert.get('message', '')}",
                    },
                })
        
        # チャンス詳細
        if opportunities:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*🚀 拡大チャンス*"},
            })
            
            for opp in opportunities[:5]:  # 最大5件
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🟢 *{opp.get('campaign_name', '')}*\n{opp.get('message', '')}",
                    },
                })
        
        # 推奨アクション
        recommendations = []
        for account in monitor_results.get("accounts", {}).values():
            if isinstance(account, dict):
                recommendations.extend(account.get("recommendations", []))
        
        if recommendations:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*💡 推奨アクション*"},
            })
            
            for i, rec in enumerate(recommendations[:5], 1):
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec.get("priority", ""), "⚪")
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{priority_emoji} *{i}. {rec.get('action', '')}*\n{rec.get('reason', '')}",
                    },
                })
        
        # フッター
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🤖 Meta Ads AI Agent | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                },
            ],
        })
        
        return self.send_message(
            text=f"📊 Meta広告日次レポート - {summary.get('status_message', '')}",
            blocks=blocks,
        )

    def send_alert(self, alert: dict) -> bool:
        """
        単一アラートを送信（緊急用）
        
        Args:
            alert: アラート情報
        
        Returns:
            bool: 送信成功したか
        """
        severity = alert.get("severity", "medium")
        severity_emoji = "🔴" if severity == "high" else "🟡"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} アラート検知",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*キャンペーン:* {alert.get('campaign_name', 'Unknown')}\n*内容:* {alert.get('message', '')}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"検知時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
                ],
            },
        ]
        
        return self.send_message(
            text=f"{severity_emoji} アラート: {alert.get('message', '')}",
            blocks=blocks,
        )

    def send_opportunity(self, opportunity: dict) -> bool:
        """
        拡大チャンス通知を送信
        
        Args:
            opportunity: チャンス情報
        
        Returns:
            bool: 送信成功したか
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚀 拡大チャンス検知！",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*キャンペーン:* {opportunity.get('campaign_name', 'Unknown')}\n*内容:* {opportunity.get('message', '')}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*推奨アクション:* {opportunity.get('suggested_action', '予算増額を検討')}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"検知時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
                ],
            },
        ]
        
        return self.send_message(
            text=f"🚀 拡大チャンス: {opportunity.get('message', '')}",
            blocks=blocks,
        )

    def send_action_executed(self, action: dict, result: dict) -> bool:
        """
        アクション実行結果を通知（Phase 2以降用）
        
        Args:
            action: 実行したアクション
            result: 実行結果
        
        Returns:
            bool: 送信成功したか
        """
        success = result.get("success", False)
        status_emoji = "✅" if success else "❌"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} アクション実行完了",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*アクション:* {action.get('type', 'Unknown')}\n*対象:* {action.get('target', '')}\n*結果:* {'成功' if success else '失敗'}",
                },
            },
        ]
        
        if result.get("details"):
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*詳細:* {result.get('details', '')}"},
            })
        
        return self.send_message(
            text=f"{status_emoji} アクション実行: {action.get('type', '')} - {'成功' if success else '失敗'}",
            blocks=blocks,
        )

    def send_hourly_alert_summary(self, monitor_results: dict) -> bool:
        """
        毎時チェックでアラートがあった場合のサマリー通知
        （日次レポートより簡潔）
        
        Args:
            monitor_results: PerformanceMonitorの結果
        
        Returns:
            bool: 送信成功したか
        """
        alerts = monitor_results.get("alerts", [])
        if not alerts:
            return True  # アラートがなければ送信しない
        
        summary = monitor_results.get("summary", {})
        high_alerts = [a for a in alerts if a.get("severity") == "high"]
        
        # ヘッダー
        if high_alerts:
            header_text = f"🔴 緊急アラート {len(high_alerts)}件検知"
        else:
            header_text = f"🟡 アラート {len(alerts)}件検知"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header_text,
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"⏰ 定期チェック | {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
                ],
            },
            {"type": "divider"},
        ]
        
        # アラート一覧（最大5件）
        for alert in alerts[:5]:
            severity_emoji = "🔴" if alert.get("severity") == "high" else "🟡"
            objective = alert.get("objective", "")
            
            alert_text = f"{severity_emoji} *{alert.get('campaign_name', '')}*"
            if objective:
                alert_text += f" [{objective}]"
            alert_text += f"\n{alert.get('message', '')}"
            
            # 問題点があれば追加
            issues = alert.get("issues", [])
            if issues:
                issue_texts = [f"• {i.get('message', '')}" for i in issues[:3]]
                alert_text += "\n" + "\n".join(issue_texts)
            
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": alert_text},
            })
        
        # フッター
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "💡 詳細はダッシュボードで確認してください"},
            ],
        })
        
        return self.send_message(
            text=f"{header_text} - 定期チェック",
            blocks=blocks,
        )

    def test_connection(self) -> bool:
        """Slack接続テスト"""
        return self.send_message(
            text="🤖 Meta Ads AI Agent からのテストメッセージです",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "✅ *Slack連携テスト成功！*\n\nMeta Ads AI Agentからの通知を受信できます。",
                    },
                },
            ],
        )
