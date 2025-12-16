"""
市場・競合分析モジュール
業界トレンド、競合分析、市場インサイトを提供
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """
    市場・競合分析エンジン
    
    機能:
    1. 業界トレンド分析
    2. 競合ポジショニング分析
    3. クリエイティブトレンド分析
    4. 市場機会の特定
    """

    def __init__(self, storage_dir: str = None, anthropic_api_key: str = None):
        if storage_dir is None:
            storage_dir = str(Path(__file__).parent.parent / "storage" / "market")
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Claude
        if anthropic_api_key:
            self.claude = Anthropic(api_key=anthropic_api_key)
        else:
            import config
            self.claude = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        
        # 業界ベンチマーク（Meta公式データ + 業界知見）
        self.industry_benchmarks = self._load_benchmarks()

    def _load_benchmarks(self) -> dict:
        """業界別ベンチマークデータを読み込み"""
        # Meta公式発表や業界調査に基づくベンチマーク
        return {
            "美容・コスメ": {
                "avg_ctr": 1.2,
                "avg_cvr": 0.8,
                "avg_cpa_range": [3000, 8000],
                "avg_cpm": 350,
                "peak_seasons": ["3月", "12月"],
                "effective_formats": ["動画", "カルーセル"],
            },
            "健康食品・サプリ": {
                "avg_ctr": 1.0,
                "avg_cvr": 0.5,
                "avg_cpa_range": [4000, 12000],
                "avg_cpm": 300,
                "peak_seasons": ["1月", "4月", "9月"],
                "effective_formats": ["画像", "動画"],
            },
            "EC・物販": {
                "avg_ctr": 0.9,
                "avg_cvr": 1.5,
                "avg_cpa_range": [500, 3000],
                "avg_cpm": 250,
                "peak_seasons": ["11月", "12月"],
                "effective_formats": ["ダイナミック広告", "カルーセル"],
            },
            "教育・オンライン講座": {
                "avg_ctr": 1.5,
                "avg_cvr": 0.3,
                "avg_cpa_range": [5000, 20000],
                "avg_cpm": 400,
                "peak_seasons": ["1月", "4月", "9月"],
                "effective_formats": ["動画", "リード広告"],
            },
            "BtoB・SaaS": {
                "avg_ctr": 0.8,
                "avg_cvr": 0.2,
                "avg_cpa_range": [10000, 50000],
                "avg_cpm": 500,
                "peak_seasons": ["4月", "10月"],
                "effective_formats": ["リード広告", "動画"],
            },
            "金融・保険": {
                "avg_ctr": 0.7,
                "avg_cvr": 0.3,
                "avg_cpa_range": [8000, 30000],
                "avg_cpm": 450,
                "peak_seasons": ["3月", "9月"],
                "effective_formats": ["リード広告", "カルーセル"],
            },
        }

    # =========================================================================
    # 業界ベンチマーク比較
    # =========================================================================

    def compare_to_benchmark(
        self,
        industry: str,
        current_metrics: dict,
    ) -> dict[str, Any]:
        """
        現在のパフォーマンスを業界ベンチマークと比較
        
        Args:
            industry: 業界カテゴリ
            current_metrics: 現在の指標
        
        Returns:
            dict: ベンチマーク比較結果
        """
        benchmark = self.industry_benchmarks.get(industry)
        if not benchmark:
            # 類似業界を推測
            industry = self._guess_industry(industry)
            benchmark = self.industry_benchmarks.get(industry, {})
        
        comparison = {
            "industry": industry,
            "benchmark": benchmark,
            "current": current_metrics,
            "comparison": {},
        }
        
        # CTR比較
        if "avg_ctr" in benchmark and "ctr" in current_metrics:
            diff = current_metrics["ctr"] - benchmark["avg_ctr"]
            comparison["comparison"]["ctr"] = {
                "benchmark": benchmark["avg_ctr"],
                "current": current_metrics["ctr"],
                "diff": diff,
                "status": "above_average" if diff > 0 else "below_average",
                "percentile": self._estimate_percentile(current_metrics["ctr"], benchmark["avg_ctr"], 0.5),
            }
        
        # CVR比較
        if "avg_cvr" in benchmark and "cvr" in current_metrics:
            diff = current_metrics["cvr"] - benchmark["avg_cvr"]
            comparison["comparison"]["cvr"] = {
                "benchmark": benchmark["avg_cvr"],
                "current": current_metrics["cvr"],
                "diff": diff,
                "status": "above_average" if diff > 0 else "below_average",
            }
        
        # CPA比較
        if "avg_cpa_range" in benchmark and "cpa" in current_metrics:
            cpa_range = benchmark["avg_cpa_range"]
            cpa = current_metrics["cpa"]
            if cpa < cpa_range[0]:
                status = "excellent"
            elif cpa < cpa_range[1]:
                status = "average"
            else:
                status = "below_average"
            
            comparison["comparison"]["cpa"] = {
                "benchmark_range": cpa_range,
                "current": cpa,
                "status": status,
            }
        
        # 総合評価
        comparison["overall_assessment"] = self._generate_overall_assessment(comparison)
        
        return comparison

    def _guess_industry(self, input_industry: str) -> str:
        """入力から業界を推測"""
        mapping = {
            "美容": "美容・コスメ",
            "コスメ": "美容・コスメ",
            "化粧品": "美容・コスメ",
            "健康": "健康食品・サプリ",
            "サプリ": "健康食品・サプリ",
            "食品": "健康食品・サプリ",
            "EC": "EC・物販",
            "通販": "EC・物販",
            "物販": "EC・物販",
            "教育": "教育・オンライン講座",
            "講座": "教育・オンライン講座",
            "スクール": "教育・オンライン講座",
            "BtoB": "BtoB・SaaS",
            "SaaS": "BtoB・SaaS",
            "金融": "金融・保険",
            "保険": "金融・保険",
        }
        
        for key, value in mapping.items():
            if key in input_industry:
                return value
        
        return "健康食品・サプリ"  # デフォルト

    def _estimate_percentile(self, value: float, avg: float, std: float) -> str:
        """パーセンタイルを推定"""
        z = (value - avg) / std
        if z > 1.5:
            return "上位10%"
        elif z > 0.5:
            return "上位30%"
        elif z > -0.5:
            return "平均（50%）"
        elif z > -1.5:
            return "下位30%"
        else:
            return "下位10%"

    def _generate_overall_assessment(self, comparison: dict) -> dict:
        """総合評価を生成"""
        scores = []
        
        for metric, data in comparison.get("comparison", {}).items():
            if data.get("status") == "excellent":
                scores.append(3)
            elif data.get("status") == "above_average":
                scores.append(2)
            elif data.get("status") == "average":
                scores.append(1)
            else:
                scores.append(0)
        
        if not scores:
            return {"grade": "N/A", "message": "比較データ不足"}
        
        avg_score = sum(scores) / len(scores)
        
        if avg_score >= 2.5:
            grade = "A"
            message = "業界トップクラスのパフォーマンス"
        elif avg_score >= 1.5:
            grade = "B"
            message = "業界平均以上のパフォーマンス"
        elif avg_score >= 0.5:
            grade = "C"
            message = "業界平均レベル"
        else:
            grade = "D"
            message = "改善の余地あり"
        
        return {"grade": grade, "message": message, "avg_score": avg_score}

    # =========================================================================
    # クリエイティブトレンド分析
    # =========================================================================

    def analyze_creative_trends(
        self,
        industry: str,
        current_creatives: list[dict] = None,
    ) -> dict[str, Any]:
        """
        クリエイティブトレンドを分析
        
        Args:
            industry: 業界
            current_creatives: 現在使用中のクリエイティブ情報（オプション）
        
        Returns:
            dict: トレンド分析結果
        """
        prompt = f"""## クリエイティブトレンド分析

業界: {industry}

現在のクリエイティブ:
{json.dumps(current_creatives or [], ensure_ascii=False, indent=2)}

### 分析してください
1. この業界で現在効果的なクリエイティブトレンド
2. 訴求軸の傾向
3. フォーマット（静止画/動画/カルーセル）のトレンド
4. UGC（ユーザー生成コンテンツ）風の効果
5. 改善提案

JSON形式で回答:
{{
  "current_trends": [
    {{"trend": "トレンド名", "description": "説明", "effectiveness": "high/medium/low"}}
  ],
  "effective_appeals": ["訴求軸1", "訴求軸2"],
  "format_recommendations": {{
    "best_format": "動画/静止画/カルーセル",
    "reasoning": "理由",
    "format_mix": {{"video": 50, "image": 30, "carousel": 20}}
  }},
  "ugc_effectiveness": {{
    "recommended": true/false,
    "reasoning": "理由"
  }},
  "improvement_suggestions": [
    {{"priority": "high/medium/low", "suggestion": "具体的な提案"}}
  ]
}}
"""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system="""あなたはMeta広告のクリエイティブ戦略エキスパートです。
業界のトレンドと効果的なクリエイティブ戦略について分析してください。

考慮すべき点:
- Meta/Instagramのアルゴリズム特性
- ユーザーの視聴習慣
- プラットフォームごとの最適化
- 広告疲労への対策""",
                messages=[{"role": "user", "content": prompt}],
            )
            
            return self._parse_json_response(response.content[0].text)
            
        except Exception as e:
            logger.error(f"クリエイティブトレンド分析エラー: {e}")
            return {"error": str(e)}

    # =========================================================================
    # 市場機会分析
    # =========================================================================

    def identify_opportunities(
        self,
        current_performance: dict,
        industry: str,
        budget_range: list[int] = None,
    ) -> dict[str, Any]:
        """
        市場機会を特定
        
        Args:
            current_performance: 現在のパフォーマンス
            industry: 業界
            budget_range: 予算範囲 [min, max]
        
        Returns:
            dict: 市場機会分析
        """
        benchmark = self.industry_benchmarks.get(
            self._guess_industry(industry),
            {}
        )
        
        prompt = f"""## 市場機会分析

### 現在のパフォーマンス
{json.dumps(current_performance, ensure_ascii=False, indent=2)}

### 業界: {industry}
### 業界ベンチマーク
{json.dumps(benchmark, ensure_ascii=False, indent=2)}

### 予算範囲
月額: ¥{budget_range[0] if budget_range else 1000000:,} 〜 ¥{budget_range[1] if budget_range else 5000000:,}

### 分析してください
1. 現在の強みと弱み
2. 未開拓の市場機会
3. 拡大可能性の評価
4. リスクと障壁
5. 具体的なアクションプラン

JSON形式で回答:
{{
  "swot_analysis": {{
    "strengths": ["強み"],
    "weaknesses": ["弱み"],
    "opportunities": ["機会"],
    "threats": ["脅威"]
  }},
  "untapped_opportunities": [
    {{
      "opportunity": "機会の名称",
      "description": "詳細",
      "potential_impact": "high/medium/low",
      "difficulty": "high/medium/low",
      "estimated_roi_improvement": "+20%"
    }}
  ],
  "scalability_assessment": {{
    "current_efficiency_grade": "A/B/C/D",
    "max_efficient_budget": 0,
    "scaling_strategy": "推奨戦略"
  }},
  "risks": ["リスク"],
  "action_plan": [
    {{"priority": 1, "action": "アクション", "timeline": "期間", "expected_outcome": "期待効果"}}
  ]
}}
"""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2500,
                system="""あなたは広告運用の戦略コンサルタントです。
データに基づいて市場機会を分析し、実行可能な戦略を提案してください。

分析の原則:
- 数値に基づいた客観的分析
- 実現可能性を重視
- リスクを正直に伝える
- 優先順位を明確に""",
                messages=[{"role": "user", "content": prompt}],
            )
            
            return self._parse_json_response(response.content[0].text)
            
        except Exception as e:
            logger.error(f"市場機会分析エラー: {e}")
            return {"error": str(e)}

    # =========================================================================
    # 季節性分析
    # =========================================================================

    def analyze_seasonality(
        self,
        industry: str,
        historical_data: list[dict] = None,
    ) -> dict[str, Any]:
        """
        季節性を分析
        
        Args:
            industry: 業界
            historical_data: 過去データ（オプション）
        
        Returns:
            dict: 季節性分析
        """
        benchmark = self.industry_benchmarks.get(
            self._guess_industry(industry),
            {}
        )
        
        current_month = datetime.now().strftime("%m月")
        
        analysis = {
            "industry": industry,
            "current_month": current_month,
            "peak_seasons": benchmark.get("peak_seasons", []),
            "is_peak_season": current_month.replace("0", "") in benchmark.get("peak_seasons", []),
            "recommendations": [],
        }
        
        # 季節に応じた推奨
        if analysis["is_peak_season"]:
            analysis["recommendations"] = [
                "ピークシーズンのため、予算増額を検討",
                "競合も活発化するためCPM上昇に注意",
                "クリエイティブの頻度を上げて鮮度を維持",
            ]
        else:
            analysis["recommendations"] = [
                "オフシーズンはCPMが安定しやすい",
                "この時期にテストや学習を進めるのが効果的",
                "ピークに向けた準備（クリエイティブ、LPなど）を進める",
            ]
        
        return analysis

    # =========================================================================
    # 競合ポジショニング推定
    # =========================================================================

    def estimate_competitive_position(
        self,
        industry: str,
        current_metrics: dict,
        budget_level: str = "medium",  # low/medium/high
    ) -> dict[str, Any]:
        """
        競合内でのポジションを推定
        
        Args:
            industry: 業界
            current_metrics: 現在の指標
            budget_level: 予算規模
        
        Returns:
            dict: 競合ポジショニング
        """
        benchmark = self.compare_to_benchmark(industry, current_metrics)
        
        prompt = f"""## 競合ポジショニング分析

### 業界: {industry}
### 予算規模: {budget_level}

### 現在のパフォーマンス vs ベンチマーク
{json.dumps(benchmark, ensure_ascii=False, indent=2)}

### 分析してください
この広告主が業界内でどのようなポジションにいるか推定してください。

JSON形式で回答:
{{
  "estimated_position": {{
    "market_share_estimate": "small/medium/large",
    "efficiency_rank": "上位10%/上位30%/平均/下位30%",
    "competitive_advantage": ["強み"],
    "competitive_disadvantage": ["弱み"]
  }},
  "competitor_landscape": {{
    "likely_competitors": ["競合タイプ"],
    "differentiation_opportunities": ["差別化機会"]
  }},
  "strategic_recommendations": [
    {{"strategy": "戦略", "rationale": "理由"}}
  ]
}}
"""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system="""あなたは広告市場の分析エキスパートです。
限られた情報から競合ポジションを推定し、戦略的な示唆を提供してください。

注意:
- 推定であることを明示する
- 確実なデータがない場合は保守的に判断
- 実行可能な戦略を提案""",
                messages=[{"role": "user", "content": prompt}],
            )
            
            return self._parse_json_response(response.content[0].text)
            
        except Exception as e:
            logger.error(f"競合ポジショニング分析エラー: {e}")
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


