"""
予測シミュレーター
「予算を増やしたらどうなる？」などのシミュレーション
"""
import json
import logging
from typing import Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)


class Predictor:
    """
    広告パフォーマンスの予測シミュレーター
    
    機能:
    1. 予算変更シミュレーション
    2. アクション効果予測
    3. トレンド予測
    """

    def __init__(self, anthropic_api_key: str = None):
        if anthropic_api_key:
            self.claude = Anthropic(api_key=anthropic_api_key)
        else:
            import config
            self.claude = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # =========================================================================
    # 予算変更シミュレーション
    # =========================================================================

    def simulate_budget_change(
        self,
        current_performance: dict,
        current_budget: float,
        new_budget: float,
        context: dict = None,
    ) -> dict[str, Any]:
        """
        予算変更のシミュレーション
        
        Args:
            current_performance: 現在のパフォーマンス
            current_budget: 現在の日予算
            new_budget: 新しい日予算
            context: コンテキスト（案件情報など）
        
        Returns:
            dict: シミュレーション結果
        """
        change_percent = ((new_budget - current_budget) / current_budget) * 100
        change_amount = abs(new_budget - current_budget)
        is_small_change = context.get("is_small_change", change_amount <= 5000) if context else change_amount <= 5000
        
        prompt = f"""## 予算変更シミュレーション

### 重要な考慮事項
- 変更額: ¥{change_amount:,.0f}
- 小額変更（5,000円以下）かどうか: {"はい - 学習への影響は軽微と考えられます" if is_small_change else "いいえ - 変更率に応じた影響を考慮"}
- 予算の絶対値も重要: ¥1,000→¥3,000（200%増）と¥100,000→¥300,000（200%増）は同じ倍率でも影響が異なる

### 現在の状況
- 日予算: ¥{current_budget:,.0f}
- 消化額: ¥{current_performance.get('spend', 0):,.0f}
- インプレッション: {current_performance.get('impressions', 0):,}
- クリック: {current_performance.get('clicks', 0):,}
- コンバージョン: {current_performance.get('conversions', 0):,}
- CTR: {current_performance.get('ctr', 0):.2f}%
- CVR: {current_performance.get('cvr', 0):.2f}%
- CPC: ¥{current_performance.get('cpc', 0):,.0f}
- CPA: ¥{current_performance.get('cpa', 0):,.0f}
- ROAS: {current_performance.get('roas', 0):.2f}x

### 変更内容
- 新日予算: ¥{new_budget:,.0f}
- 変更率: {change_percent:+.1f}%

### コンテキスト
{json.dumps(context or {}, ensure_ascii=False, indent=2)}

### 予測してください
1. 予算変更後の予想パフォーマンス
2. 学習フェーズへの影響
3. リスクと注意点
4. 推奨される進め方

JSON形式で回答:
{{
  "predicted_performance": {{
    "impressions": 0,
    "clicks": 0,
    "conversions": 0,
    "ctr": 0.0,
    "cvr": 0.0,
    "cpa": 0,
    "roas": 0.0,
    "confidence_interval": "±10%"
  }},
  "learning_phase_impact": {{
    "will_reset": true/false,
    "expected_duration_days": 0,
    "severity": "none/low/medium/high"
  }},
  "risks": [],
  "recommendations": [],
  "optimal_strategy": "推奨される予算変更戦略"
}}
"""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system="""あなたはMeta広告のパフォーマンス予測エキスパートです。

予測の原則:
1. 予算増加は単純比例しない（限界効用逓減）
2. 20%超の変更は学習フェーズに影響する可能性
3. オーディエンス飽和を考慮する
4. 競合状況により変動する
5. 保守的な予測を心がける

予測は確実なものではなく、あくまで参考値として提供してください。""",
                messages=[{"role": "user", "content": prompt}],
            )
            
            return self._parse_json_response(response.content[0].text)
            
        except Exception as e:
            logger.error(f"予算シミュレーションエラー: {e}")
            return {"error": str(e)}

    # =========================================================================
    # アクション効果予測
    # =========================================================================

    def predict_action_effect(
        self,
        current_performance: dict,
        proposed_action: str,
        context: dict = None,
    ) -> dict[str, Any]:
        """
        アクションの効果を予測
        
        Args:
            current_performance: 現在のパフォーマンス
            proposed_action: 提案されたアクション
            context: コンテキスト
        
        Returns:
            dict: 予測結果
        """
        prompt = f"""## アクション効果予測

### 現在のパフォーマンス
- CTR: {current_performance.get('ctr', 0):.2f}%
- CVR: {current_performance.get('cvr', 0):.2f}%
- CPC: ¥{current_performance.get('cpc', 0):,.0f}
- CPA: ¥{current_performance.get('cpa', 0):,.0f}
- ROAS: {current_performance.get('roas', 0):.2f}x

### 提案されたアクション
{proposed_action}

### コンテキスト
{json.dumps(context or {}, ensure_ascii=False, indent=2)}

### 予測してください
このアクションを実行した場合の効果を予測してください。

JSON形式で回答:
{{
  "expected_impact": {{
    "ctr_change": "+0.2%",
    "cvr_change": "+0.1%",
    "cpa_change": "-10%",
    "timeline": "1-2週間"
  }},
  "confidence": "high/medium/low",
  "prerequisites": ["前提条件"],
  "risks": ["リスク"],
  "alternatives": ["代替案"],
  "recommendation": "実行すべきか、別の方法か"
}}
"""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system="""あなたはMeta広告の運用エキスパートです。
提案されたアクションの効果を、過去の経験と広告プラットフォームの仕組みに基づいて予測してください。
楽観的すぎず、現実的な予測を心がけてください。""",
                messages=[{"role": "user", "content": prompt}],
            )
            
            return self._parse_json_response(response.content[0].text)
            
        except Exception as e:
            logger.error(f"アクション予測エラー: {e}")
            return {"error": str(e)}

    # =========================================================================
    # トレンド予測
    # =========================================================================

    def predict_trend(
        self,
        historical_data: list[dict],
        days_to_predict: int = 7,
    ) -> dict[str, Any]:
        """
        過去データからトレンドを予測
        
        Args:
            historical_data: 過去のパフォーマンスデータ（日別）
            days_to_predict: 予測する日数
        
        Returns:
            dict: トレンド予測
        """
        if len(historical_data) < 3:
            return {"error": "予測には最低3日分のデータが必要です"}
        
        # データを整形
        data_summary = []
        for d in historical_data[-14:]:  # 直近14日
            data_summary.append({
                "date": d.get("date"),
                "spend": d.get("spend", 0),
                "conversions": d.get("conversions", 0),
                "cpa": d.get("cpa", 0),
                "roas": d.get("roas", 0),
            })
        
        prompt = f"""## トレンド予測

### 過去データ
```json
{json.dumps(data_summary, ensure_ascii=False, indent=2)}
```

### 予測してください
今後{days_to_predict}日間のトレンドを予測してください。

JSON形式で回答:
{{
  "trend_direction": "improving/stable/declining",
  "key_observations": ["観察された傾向"],
  "predicted_metrics": {{
    "avg_cpa": 0,
    "avg_roas": 0.0,
    "total_spend": 0,
    "total_conversions": 0
  }},
  "confidence": "high/medium/low",
  "risk_factors": ["リスク要因"],
  "opportunities": ["改善機会"],
  "recommended_actions": ["推奨アクション"]
}}
"""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system="""あなたは広告パフォーマンスの分析エキスパートです。
過去データのトレンドを分析し、今後のパフォーマンスを予測してください。

考慮すべき要素:
- 季節変動
- 曜日効果
- 学習フェーズの進行
- オーディエンス飽和
- 市場動向""",
                messages=[{"role": "user", "content": prompt}],
            )
            
            return self._parse_json_response(response.content[0].text)
            
        except Exception as e:
            logger.error(f"トレンド予測エラー: {e}")
            return {"error": str(e)}

    # =========================================================================
    # 「もし〜したら」シミュレーション
    # =========================================================================

    def what_if(
        self,
        current_state: dict,
        scenario: str,
    ) -> dict[str, Any]:
        """
        自由形式の「もし〜したら」シミュレーション
        
        Args:
            current_state: 現在の状態（パフォーマンス、コンテキスト）
            scenario: シナリオ（自然言語）
        
        Returns:
            dict: シミュレーション結果
        """
        prompt = f"""## 「もし〜したら」シミュレーション

### 現在の状態
```json
{json.dumps(current_state, ensure_ascii=False, indent=2)}
```

### シナリオ
{scenario}

### 分析してください
このシナリオを実行した場合、どのような結果になるか予測してください。

JSON形式で回答:
{{
  "scenario_analysis": "シナリオの分析",
  "likely_outcome": {{
    "short_term": "短期的な影響（1週間）",
    "medium_term": "中期的な影響（1ヶ月）",
    "long_term": "長期的な影響（3ヶ月以上）"
  }},
  "probability_of_success": 0.0,
  "key_factors": ["成功を左右する要因"],
  "risks": ["リスク"],
  "mitigation_strategies": ["リスク軽減策"],
  "alternative_scenarios": [
    {{"scenario": "代替案1", "pros": "メリット", "cons": "デメリット"}}
  ],
  "recommendation": "総合的な推奨"
}}
"""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2500,
                system="""あなたはMeta広告運用の戦略アドバイザーです。
「もし〜したら」というシナリオについて、現実的で実用的な分析を提供してください。

分析の原則:
1. 希望的観測を避ける
2. 複数の可能性を考慮する
3. リスクを正直に伝える
4. 実行可能な代替案を提示する
5. Metaのアルゴリズム特性を踏まえる""",
                messages=[{"role": "user", "content": prompt}],
            )
            
            return self._parse_json_response(response.content[0].text)
            
        except Exception as e:
            logger.error(f"What-Ifシミュレーションエラー: {e}")
            return {"error": str(e)}

    def _parse_json_response(self, response_text: str) -> dict:
        """JSONレスポンスをパース"""
        try:
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"raw_response": response_text, "error": "JSON parse error"}


