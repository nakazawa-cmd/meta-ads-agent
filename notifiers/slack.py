"""
Slack通知モジュール
"""
import json
import logging
from datetime import datetime
from typing import Any

import requests

import config

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Slackへの通知を行うクラス"""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or config.SLACK_WEBHOOK_URL

    def send_message(self, message: dict[str, Any]) -> bool:
        """
        Slackにメッセージを送信

        Args:
            message: Slack Block Kit形式のメッセージ

        Returns:
            bool: 送信成功したかどうか
        """
        if not self.webhook_url:
            logger.warning("Slack Webhook URLが設定されていません")
            return False

        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=30,
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Slack送信エラー: {e}")
            return False

    def send_performance_report(
        self,
        account_name: str,
        summary: dict[str, Any],
    ) -> bool:
        """
        パフォーマンスレポートを送信

        Args:
            account_name: 広告アカウント名
            summary: パフォーマンスサマリー

        Returns:
            bool: 送信成功したかどうか
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 {account_name} パフォーマンスレポート",
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📅 {summary.get('period', '期間不明')}",
                    }
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*💰 広告費*\n¥{summary.get('total_spend', 0):,.0f}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*👁️ インプレッション*\n{summary.get('total_impressions', 0):,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*👆 クリック*\n{summary.get('total_clicks', 0):,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*🎯 コンバージョン*\n{summary.get('total_conversions', 0):,}",
                    },
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*CTR*\n{summary.get('avg_ctr', 0):.2f}%",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*CPC*\n¥{summary.get('avg_cpc', 0):,.0f}" if summary.get('avg_cpc') else "*CPC*\n-",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*CPA*\n¥{summary.get('avg_cpa', 0):,.0f}" if summary.get('avg_cpa') else "*CPA*\n-",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*ROAS*\n{summary.get('roas', 0):.2f}x" if summary.get('roas') else "*ROAS*\n-",
                    },
                ],
            },
        ]

        return self.send_message({"blocks": blocks})

    def send_alert(
        self,
        title: str,
        message: str,
        level: str = "warning",
    ) -> bool:
        """
        アラートを送信

        Args:
            title: アラートタイトル
            message: アラートメッセージ
            level: レベル (info, warning, error)

        Returns:
            bool: 送信成功したかどうか
        """
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "🚨",
        }
        emoji = emoji_map.get(level, "📢")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {title}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    }
                ],
            },
        ]

        return self.send_message({"blocks": blocks})

    def send_optimization_report(
        self,
        results: list[dict[str, Any]],
        optimization_type: str = "bid",
    ) -> bool:
        """
        最適化レポートを送信

        Args:
            results: 最適化結果のリスト
            optimization_type: 最適化タイプ (bid, creative)

        Returns:
            bool: 送信成功したかどうか
        """
        if optimization_type == "bid":
            title = "📈 入札最適化レポート"
            adjusted = [r for r in results if r.get("suggestion", {}).get("should_adjust")]
        else:
            title = "🎨 クリエイティブ最適化レポート"
            adjusted = results

        if not adjusted:
            return True  # 通知不要

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title,
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{len(adjusted)}件* の調整を実行/提案しました",
                },
            },
            {"type": "divider"},
        ]

        for item in adjusted[:5]:
            if optimization_type == "bid":
                suggestion = item.get("suggestion", {})
                text = (
                    f"*{item.get('adset_name', item.get('adset_id'))}*\n"
                    f"入札: ¥{suggestion.get('current_bid', 0):,.0f} → ¥{suggestion.get('recommended_bid', 0):,.0f} "
                    f"({suggestion.get('change_percent', 0):+.1f}%)\n"
                    f"理由: {suggestion.get('reason', '-')}"
                )
            else:
                text = (
                    f"*{item.get('ad_name', item.get('ad_id'))}*\n"
                    f"理由: {item.get('reason', '-')}"
                )

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            })

        if len(adjusted) > 5:
            blocks.append({
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"_...他 {len(adjusted) - 5} 件_"}
                ],
            })

        return self.send_message({"blocks": blocks})

    def send_test(self) -> bool:
        """テスト通知を送信"""
        return self.send_message({
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Meta Ads Agent テスト通知",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Slack通知の設定が正しく完了しました！",
                    },
                },
            ]
        })


