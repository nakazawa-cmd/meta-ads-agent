"""
レポート生成モジュール
週次・月次レポートの自動生成
"""
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    パフォーマンスレポートを生成するクラス
    
    機能:
    1. 日次サマリー
    2. 週次レポート
    3. 月次レポート
    4. カスタム期間レポート
    """

    def __init__(self, integrated_agent=None):
        self.agent = integrated_agent
        logger.info("ReportGenerator初期化完了")

    def generate_daily_summary(self, account_id: str) -> dict:
        """
        日次サマリーを生成
        
        Args:
            account_id: アカウントID
        
        Returns:
            dict: レポートデータ
        """
        return self._generate_report(account_id, "today", "日次サマリー")

    def generate_weekly_report(self, account_id: str) -> dict:
        """
        週次レポートを生成（過去7日間）
        
        Args:
            account_id: アカウントID
        
        Returns:
            dict: レポートデータ
        """
        return self._generate_report(account_id, "last_7d", "週次レポート")

    def generate_monthly_report(self, account_id: str) -> dict:
        """
        月次レポートを生成（過去30日間）
        
        Args:
            account_id: アカウントID
        
        Returns:
            dict: レポートデータ
        """
        return self._generate_report(account_id, "last_30d", "月次レポート")

    def _generate_report(self, account_id: str, date_preset: str, report_type: str) -> dict:
        """レポート生成の共通処理"""
        if not self.agent or not self.agent.meta_initialized:
            return {"error": "Meta API未接続"}

        try:
            managers = self.agent._get_managers(account_id)
            if not managers:
                return {"error": "マネージャー取得失敗"}

            # キャンペーン一覧を取得
            campaigns = managers["campaign"].get_campaigns(status_filter=["ACTIVE", "PAUSED"])
            
            # パフォーマンスデータを取得
            campaign_data = []
            total_spend = 0
            total_conversions = 0
            total_revenue = 0
            total_clicks = 0
            total_impressions = 0

            for campaign in campaigns:
                insights = managers["insight"].get_campaign_insights(
                    campaign_id=campaign["id"],
                    date_preset=date_preset,
                )
                
                if insights:
                    insight = insights[0] if isinstance(insights, list) else insights
                    
                    spend = insight.get("spend", 0)
                    conversions = insight.get("conversions", 0)
                    revenue = insight.get("conversion_value", 0) or insight.get("purchase_value", 0)
                    clicks = insight.get("clicks", 0)
                    impressions = insight.get("impressions", 0)
                    
                    total_spend += spend
                    total_conversions += conversions
                    total_revenue += revenue
                    total_clicks += clicks
                    total_impressions += impressions
                    
                    # ROAS, CPA計算
                    roas = revenue / spend if spend > 0 else 0
                    cpa = spend / conversions if conversions > 0 else 0
                    ctr = (clicks / impressions * 100) if impressions > 0 else 0
                    
                    campaign_data.append({
                        "id": campaign["id"],
                        "name": campaign["name"],
                        "status": campaign["effective_status"],
                        "objective": campaign.get("objective", ""),
                        "spend": spend,
                        "conversions": conversions,
                        "revenue": revenue,
                        "roas": round(roas, 2),
                        "cpa": round(cpa, 0),
                        "clicks": clicks,
                        "impressions": impressions,
                        "ctr": round(ctr, 2),
                    })

            # 全体指標
            overall_roas = total_revenue / total_spend if total_spend > 0 else 0
            overall_cpa = total_spend / total_conversions if total_conversions > 0 else 0
            overall_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0

            # キャンペーンをパフォーマンス順にソート
            top_performers = sorted(campaign_data, key=lambda x: x.get("roas", 0), reverse=True)[:5]
            needs_attention = sorted(
                [c for c in campaign_data if c.get("spend", 0) > 1000 and c.get("roas", 0) < 2],
                key=lambda x: x.get("roas", 0)
            )[:5]

            report = {
                "report_type": report_type,
                "date_preset": date_preset,
                "generated_at": datetime.now().isoformat(),
                "account_id": account_id,
                "summary": {
                    "total_spend": round(total_spend, 0),
                    "total_conversions": total_conversions,
                    "total_revenue": round(total_revenue, 0),
                    "overall_roas": round(overall_roas, 2),
                    "overall_cpa": round(overall_cpa, 0),
                    "overall_ctr": round(overall_ctr, 2),
                    "total_clicks": total_clicks,
                    "total_impressions": total_impressions,
                    "campaign_count": len(campaign_data),
                },
                "campaigns": campaign_data,
                "top_performers": top_performers,
                "needs_attention": needs_attention,
            }

            logger.info(f"{report_type}を生成しました: {account_id}")
            return report

        except Exception as e:
            logger.error(f"レポート生成エラー: {e}")
            return {"error": str(e)}

    def format_slack_report(self, report: dict) -> dict:
        """
        レポートをSlack Block Kit形式に変換
        
        Args:
            report: generate_xxx_report()の結果
        
        Returns:
            dict: Slack Block Kit形式
        """
        if "error" in report:
            return {
                "text": f"❌ レポート生成エラー: {report['error']}",
                "blocks": [],
            }

        summary = report.get("summary", {})
        report_type = report.get("report_type", "レポート")
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 {report_type} ({datetime.now().strftime('%Y/%m/%d')})",
                    "emoji": True,
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*💰 総消化*\n¥{summary.get('total_spend', 0):,.0f}"},
                    {"type": "mrkdwn", "text": f"*📈 ROAS*\n{summary.get('overall_roas', 0):.2f}"},
                    {"type": "mrkdwn", "text": f"*🎯 CV数*\n{summary.get('total_conversions', 0):,}件"},
                    {"type": "mrkdwn", "text": f"*💵 CPA*\n¥{summary.get('overall_cpa', 0):,.0f}"},
                ],
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*💎 売上*\n¥{summary.get('total_revenue', 0):,.0f}"},
                    {"type": "mrkdwn", "text": f"*👆 CTR*\n{summary.get('overall_ctr', 0):.2f}%"},
                    {"type": "mrkdwn", "text": f"*👁️ IMP*\n{summary.get('total_impressions', 0):,}"},
                    {"type": "mrkdwn", "text": f"*🏷️ キャンペーン*\n{summary.get('campaign_count', 0)}件"},
                ],
            },
        ]

        # トップパフォーマー
        top_performers = report.get("top_performers", [])
        if top_performers:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*🏆 トップパフォーマー*"},
            })
            
            for i, camp in enumerate(top_performers[:3], 1):
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{i}. *{camp['name'][:30]}*\nROAS: {camp['roas']:.2f} | 消化: ¥{camp['spend']:,.0f}",
                    },
                })

        # 要注意キャンペーン
        needs_attention = report.get("needs_attention", [])
        if needs_attention:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*⚠️ 要注意キャンペーン*"},
            })
            
            for camp in needs_attention[:3]:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• *{camp['name'][:30]}*\nROAS: {camp['roas']:.2f} | 消化: ¥{camp['spend']:,.0f}",
                    },
                })

        # フッター
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"🤖 Meta Ads AI Agent | {report.get('generated_at', '')[:19]}"},
            ],
        })

        return {
            "text": f"📊 {report_type} - ROAS: {summary.get('overall_roas', 0):.2f}",
            "blocks": blocks,
        }

    def export_csv(self, report: dict) -> str:
        """
        レポートをCSV形式でエクスポート
        
        Args:
            report: generate_xxx_report()の結果
        
        Returns:
            str: CSVデータ
        """
        if "error" in report:
            return ""

        campaigns = report.get("campaigns", [])
        
        # ヘッダー
        headers = [
            "キャンペーン名", "ステータス", "目的",
            "消化", "CV数", "売上", "ROAS", "CPA",
            "クリック", "IMP", "CTR"
        ]
        
        rows = [",".join(headers)]
        
        for camp in campaigns:
            row = [
                f'"{camp.get("name", "")}"',
                camp.get("status", ""),
                camp.get("objective", ""),
                str(camp.get("spend", 0)),
                str(camp.get("conversions", 0)),
                str(camp.get("revenue", 0)),
                str(camp.get("roas", 0)),
                str(camp.get("cpa", 0)),
                str(camp.get("clicks", 0)),
                str(camp.get("impressions", 0)),
                str(camp.get("ctr", 0)),
            ]
            rows.append(",".join(row))
        
        return "\n".join(rows)


def generate_and_send_report(
    agent,
    notifier,
    account_id: str,
    report_type: str = "weekly",
) -> bool:
    """
    レポートを生成してSlack送信
    
    Args:
        agent: IntegratedAgent
        notifier: SlackNotifier
        account_id: アカウントID
        report_type: "daily", "weekly", or "monthly"
    
    Returns:
        bool: 送信成功したか
    """
    generator = ReportGenerator(integrated_agent=agent)
    
    if report_type == "daily":
        report = generator.generate_daily_summary(account_id)
    elif report_type == "weekly":
        report = generator.generate_weekly_report(account_id)
    elif report_type == "monthly":
        report = generator.generate_monthly_report(account_id)
    else:
        return False
    
    if "error" in report:
        logger.error(f"レポート生成エラー: {report['error']}")
        return False
    
    slack_data = generator.format_slack_report(report)
    
    return notifier.send_message(
        text=slack_data["text"],
        blocks=slack_data["blocks"],
    )

