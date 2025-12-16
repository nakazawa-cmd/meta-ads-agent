"""
Claude連携 - パフォーマンス分析モジュール
"""
import json
import logging
from typing import Any

from anthropic import Anthropic

import config

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """Claudeを使用してパフォーマンス分析を行うクラス"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.ANTHROPIC_API_KEY
        self.model = config.CLAUDE_MODEL
        self.client = None

        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)

    def analyze_performance(
        self,
        performance_data: dict[str, Any],
        target_cpa: float = None,
        target_roas: float = None,
    ) -> dict[str, Any]:
        """
        パフォーマンスデータを分析し、改善提案を生成

        Args:
            performance_data: パフォーマンスデータ
            target_cpa: 目標CPA
            target_roas: 目標ROAS

        Returns:
            dict: 分析結果と提案
        """
        if not self.client:
            logger.error("Claude APIキーが設定されていません")
            return {"error": "APIキーが設定されていません"}

        target_cpa = target_cpa or config.BID_OPTIMIZATION["default_target_cpa"]
        target_roas = target_roas or config.BID_OPTIMIZATION["default_target_roas"]

        prompt = self._build_analysis_prompt(performance_data, target_cpa, target_roas)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                system="""あなたは広告運用の専門家です。
Meta広告（Facebook/Instagram広告）のパフォーマンスデータを分析し、
具体的で実行可能な改善提案を日本語で提供してください。
回答はJSON形式で返してください。""",
            )

            # レスポンスをパース
            content = response.content[0].text
            
            # JSONを抽出
            try:
                # JSON部分を抽出
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                else:
                    json_str = content.strip()
                
                result = json.loads(json_str)
            except json.JSONDecodeError:
                # JSONパースに失敗した場合はテキストとして返す
                result = {
                    "analysis": content,
                    "recommendations": [],
                }

            logger.info("パフォーマンス分析が完了しました")
            return result

        except Exception as e:
            logger.error(f"パフォーマンス分析に失敗しました: {e}")
            return {"error": str(e)}

    def suggest_bid_adjustment(
        self,
        adset_data: dict[str, Any],
        target_cpa: float = None,
        target_roas: float = None,
    ) -> dict[str, Any]:
        """
        入札調整の提案を生成

        Args:
            adset_data: 広告セットのパフォーマンスデータ
            target_cpa: 目標CPA
            target_roas: 目標ROAS

        Returns:
            dict: 入札調整の提案
        """
        if not self.client:
            logger.error("Claude APIキーが設定されていません")
            return {"error": "APIキーが設定されていません"}

        target_cpa = target_cpa or config.BID_OPTIMIZATION["default_target_cpa"]
        target_roas = target_roas or config.BID_OPTIMIZATION["default_target_roas"]

        prompt = f"""以下のMeta広告セットのパフォーマンスデータに基づいて、入札調整の提案を行ってください。

## 現在のパフォーマンス
```json
{json.dumps(adset_data, ensure_ascii=False, indent=2)}
```

## 目標値
- 目標CPA: {target_cpa}円
- 目標ROAS: {target_roas}倍

## 制約条件
- 入札額の変更は現在値の±{config.BID_OPTIMIZATION['max_bid_change_percent']}%以内
- 最小データ期間: {config.BID_OPTIMIZATION['min_data_days']}日
- 最小コンバージョン数: {config.BID_OPTIMIZATION['min_conversions']}件

以下のJSON形式で回答してください:
{{
  "should_adjust": true/false,
  "current_bid": 現在の入札額,
  "recommended_bid": 推奨入札額,
  "change_percent": 変更率(%),
  "reason": "調整理由",
  "confidence": "high/medium/low",
  "warnings": ["注意事項があれば"]
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
                system="あなたは広告入札最適化の専門家です。データに基づいた慎重な判断を行ってください。",
            )

            content = response.content[0].text
            
            try:
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                else:
                    json_str = content.strip()
                
                result = json.loads(json_str)
            except json.JSONDecodeError:
                result = {"error": "JSONパースエラー", "raw_response": content}

            return result

        except Exception as e:
            logger.error(f"入札調整提案の生成に失敗しました: {e}")
            return {"error": str(e)}

    def analyze_creative_performance(
        self,
        creative_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        クリエイティブのパフォーマンスを分析

        Args:
            creative_data: クリエイティブごとのパフォーマンスデータ

        Returns:
            dict: 分析結果
        """
        if not self.client:
            logger.error("Claude APIキーが設定されていません")
            return {"error": "APIキーが設定されていません"}

        prompt = f"""以下のMeta広告クリエイティブのパフォーマンスデータを分析してください。

## クリエイティブデータ
```json
{json.dumps(creative_data, ensure_ascii=False, indent=2)}
```

## 分析観点
1. 最もパフォーマンスの良いクリエイティブ
2. 停止を検討すべきクリエイティブ
3. 改善のポイント

以下のJSON形式で回答してください:
{{
  "top_performers": [
    {{"ad_id": "xxx", "ad_name": "xxx", "reason": "理由"}}
  ],
  "should_pause": [
    {{"ad_id": "xxx", "ad_name": "xxx", "reason": "理由", "confidence": "high/medium/low"}}
  ],
  "insights": ["気づき1", "気づき2"],
  "recommendations": ["改善提案1", "改善提案2"]
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
                system="あなたは広告クリエイティブ分析の専門家です。データに基づいた客観的な分析を行ってください。",
            )

            content = response.content[0].text
            
            try:
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                else:
                    json_str = content.strip()
                
                result = json.loads(json_str)
            except json.JSONDecodeError:
                result = {"error": "JSONパースエラー", "raw_response": content}

            return result

        except Exception as e:
            logger.error(f"クリエイティブ分析に失敗しました: {e}")
            return {"error": str(e)}

    def _build_analysis_prompt(
        self,
        data: dict[str, Any],
        target_cpa: float,
        target_roas: float,
    ) -> str:
        """分析用プロンプトを構築"""
        return f"""以下のMeta広告パフォーマンスデータを分析し、改善提案を行ってください。

## パフォーマンスデータ
```json
{json.dumps(data, ensure_ascii=False, indent=2)}
```

## 目標値
- 目標CPA: {target_cpa}円
- 目標ROAS: {target_roas}倍

## 分析してほしい観点
1. 全体的なパフォーマンス評価
2. 目標値との乖離
3. トレンド（改善傾向/悪化傾向）
4. 具体的な改善アクション

以下のJSON形式で回答してください:
{{
  "overall_score": 1-10の評価,
  "summary": "全体サマリー",
  "kpi_status": {{
    "cpa": {{"current": 値, "target": 値, "status": "達成/未達"}},
    "roas": {{"current": 値, "target": 値, "status": "達成/未達"}}
  }},
  "trend": "improving/stable/declining",
  "recommendations": [
    {{"priority": "high/medium/low", "action": "アクション内容", "expected_impact": "期待効果"}}
  ],
  "warnings": ["注意事項があれば"]
}}"""


