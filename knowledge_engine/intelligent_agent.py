"""
統合インテリジェントエージェント
全ての知識エンジンを統合し、人間を超える判断を提供
"""
import json
import logging
from datetime import datetime
from typing import Any

from anthropic import Anthropic

from .knowledge_base import KnowledgeBase
from .pattern_learner import PatternLearner
from .predictor import Predictor
from .market_analyzer import MarketAnalyzer

logger = logging.getLogger(__name__)


class IntelligentAgent:
    """
    Meta広告の統合インテリジェントエージェント
    
    特徴:
    - RAG（知識ベース参照）による判断
    - パターン学習による予測
    - シミュレーションによる検証
    - 市場分析による文脈理解
    - 全てを統合した総合判断
    
    人間のルールを超える判断:
    - 単純な閾値判断ではない
    - 複合的な要因を考慮
    - 過去の学習を活かす
    - 市場環境を理解
    """

    def __init__(self, anthropic_api_key: str = None):
        # 各エンジンを初期化
        self.knowledge_base = KnowledgeBase(anthropic_api_key)
        self.pattern_learner = PatternLearner(anthropic_api_key=anthropic_api_key)
        self.predictor = Predictor(anthropic_api_key)
        self.market_analyzer = MarketAnalyzer(anthropic_api_key=anthropic_api_key)
        
        # Claude（最終判断用）
        if anthropic_api_key:
            self.claude = Anthropic(api_key=anthropic_api_key)
        else:
            import config
            self.claude = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        
        logger.info("🤖 IntelligentAgent 初期化完了")

    def analyze_and_decide(
        self,
        project: dict,
        performance: dict,
        question: str = None,
    ) -> dict[str, Any]:
        """
        総合分析と判断を実行
        
        Args:
            project: 案件情報
                - name: 案件名
                - industry: 業界
                - target_cpa: 目標CPA
                - target_roas: 目標ROAS
                - has_article_lp: 記事LP有無
                - offer: オファー内容
                - daily_budget: 日予算
            performance: パフォーマンスデータ
                - spend, impressions, clicks, conversions
                - ctr, cvr, cpc, cpa, roas
            question: 具体的な質問（オプション）
        
        Returns:
            dict: 総合判断結果
        """
        logger.info(f"🔍 分析開始: {project.get('name', '不明な案件')}")
        
        # =========================================================================
        # Step 1: 情報収集フェーズ
        # =========================================================================
        
        # 1-1: 関連知識を検索
        knowledge_query = self._build_knowledge_query(project, performance)
        relevant_knowledge = self.knowledge_base.search_knowledge(
            knowledge_query, n_results=5
        )
        
        # 1-2: パターンマッチング
        pattern_prediction = self.pattern_learner.predict_outcome(
            performance,
            {"target_cpa": project.get("target_cpa"), "has_article_lp": project.get("has_article_lp")},
        )
        
        # 1-3: 類似ケース検索
        similar_cases = self.pattern_learner.find_similar_cases(
            performance,
            {"target_cpa": project.get("target_cpa"), "has_article_lp": project.get("has_article_lp")},
            top_n=3,
        )
        
        # 1-4: 業界ベンチマーク比較
        benchmark = self.market_analyzer.compare_to_benchmark(
            project.get("industry", "健康食品"),
            performance,
        )
        
        # 1-5: 季節性分析
        seasonality = self.market_analyzer.analyze_seasonality(
            project.get("industry", "健康食品")
        )
        
        # =========================================================================
        # Step 2: 統合分析フェーズ
        # =========================================================================
        
        # 全情報を統合してClaudeに判断を依頼
        comprehensive_analysis = self._request_comprehensive_analysis(
            project=project,
            performance=performance,
            knowledge=relevant_knowledge,
            pattern_prediction=pattern_prediction,
            similar_cases=similar_cases,
            benchmark=benchmark,
            seasonality=seasonality,
            question=question,
        )
        
        # =========================================================================
        # Step 3: 結果構築フェーズ
        # =========================================================================
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "project": project.get("name"),
            "analysis_summary": {
                "benchmark_grade": benchmark.get("overall_assessment", {}).get("grade"),
                "pattern_match": pattern_prediction.get("prediction", {}).get("likely_outcome"),
                "similar_cases_found": len(similar_cases),
                "is_peak_season": seasonality.get("is_peak_season"),
            },
            "comprehensive_judgment": comprehensive_analysis,
            "data_sources_used": {
                "knowledge_base": len(relevant_knowledge),
                "patterns": len(pattern_prediction.get("matched_patterns", [])),
                "similar_cases": len(similar_cases),
                "benchmark": bool(benchmark),
                "seasonality": bool(seasonality),
            },
        }
        
        logger.info(f"✅ 分析完了: {result['analysis_summary']}")
        
        return result

    def _build_knowledge_query(self, project: dict, performance: dict) -> str:
        """知識検索クエリを構築"""
        queries = []
        
        # パフォーマンスに基づくクエリ
        if performance.get("cpa") and project.get("target_cpa"):
            if performance["cpa"] > project["target_cpa"] * 1.2:
                queries.append("CPA改善 最適化")
            elif performance["cpa"] < project["target_cpa"] * 0.8:
                queries.append("予算拡大 スケール")
        
        if performance.get("ctr", 0) < 1.0:
            queries.append("CTR改善 クリエイティブ")
        
        if performance.get("cvr", 0) < 0.3:
            queries.append("CVR改善 LP最適化")
        
        # 案件特性に基づくクエリ
        if project.get("has_article_lp"):
            queries.append("記事LP 最適化")
        else:
            queries.append("直接LP 改善")
        
        return " ".join(queries) if queries else "広告運用 ベストプラクティス"

    def _request_comprehensive_analysis(
        self,
        project: dict,
        performance: dict,
        knowledge: list,
        pattern_prediction: dict,
        similar_cases: list,
        benchmark: dict,
        seasonality: dict,
        question: str = None,
    ) -> dict:
        """Claudeに総合分析を依頼"""
        
        prompt = f"""# 広告運用の総合分析依頼

あなたは経験豊富な広告運用のエキスパートです。
以下の情報を統合して、**人間のルールを超える**総合判断を行ってください。

## 重要な原則
- 「CPAが目標を超えたら停止」のような単純なルールは使わない
- **なぜその数値になっているのか**を分析する
- **改善余地があるか**を検討する
- **市場環境や季節性**を考慮する
- **過去の類似ケース**から学ぶ
- **データに基づいた論理的判断**を行う

---

## 案件情報
```json
{json.dumps(project, ensure_ascii=False, indent=2)}
```

## 現在のパフォーマンス
```json
{json.dumps(performance, ensure_ascii=False, indent=2)}
```

## 業界ベンチマーク比較
- 業界: {benchmark.get('industry')}
- 総合評価: {benchmark.get('overall_assessment', {}).get('grade')} - {benchmark.get('overall_assessment', {}).get('message')}
- 詳細: {json.dumps(benchmark.get('comparison', {}), ensure_ascii=False)}

## 季節性
- 現在: {seasonality.get('current_month')}
- ピークシーズン: {seasonality.get('peak_seasons')}
- 現在ピーク?: {'はい' if seasonality.get('is_peak_season') else 'いいえ'}

## パターンマッチング結果
```json
{json.dumps(pattern_prediction, ensure_ascii=False, indent=2)}
```

## 類似ケース（過去の実績）
"""
        
        for i, case in enumerate(similar_cases[:3], 1):
            record = case.get("record", {})
            prompt += f"""
### 類似ケース {i}
- 案件: {record.get('project_name')}
- 類似度: {case.get('similarity_score', 0):.2f}
- 結果CPA: ¥{record.get('metrics', {}).get('cpa', 0):,.0f}
- 結果ROAS: {record.get('metrics', {}).get('roas', 0):.2f}x
"""

        prompt += f"""

## 関連知識（RAG検索結果）
"""
        for k in knowledge[:3]:
            prompt += f"""
### {k.get('metadata', {}).get('title', '無題')}
{k.get('document', '')[:300]}...
"""

        if question:
            prompt += f"""

## 質問
{question}
"""
        else:
            prompt += """

## 質問
この案件について、総合的な判断と推奨アクションを教えてください。
"""

        prompt += """

---

# 回答形式

以下のJSON形式で回答してください:
```json
{
  "overall_judgment": {
    "status": "good/warning/critical",
    "verdict": "継続強化/様子見/改善必要/緊急対応",
    "confidence": "high/medium/low",
    "one_line_summary": "一行サマリー"
  },
  "deep_analysis": {
    "why_this_performance": "なぜこの数値になっているのか（根本原因）",
    "improvement_potential": "改善の余地があるか、その根拠",
    "hidden_opportunities": "見落としている機会",
    "risks_not_obvious": "見落としているリスク"
  },
  "recommendations": [
    {
      "priority": "immediate/this_week/this_month",
      "action": "具体的なアクション",
      "expected_impact": "期待効果",
      "reasoning": "なぜこのアクションが有効か"
    }
  ],
  "what_not_to_do": [
    "やってはいけないこと（理由付き）"
  ],
  "metrics_to_watch": [
    {"metric": "指標", "threshold": "閾値", "action_if_breached": "閾値を超えたらどうするか"}
  ],
  "next_review_timing": "次に見直すべきタイミング",
  "learning_for_future": "今後の運用に活かせる学び"
}
```
"""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                system="""あなたはMeta広告運用の最高のエキスパートです。

あなたの特徴:
1. 10年以上の広告運用経験
2. 数百の案件を成功に導いた実績
3. Metaのアルゴリズムを深く理解
4. データだけでなく「文脈」を読む力
5. 単純なルールではなく「総合判断」ができる

判断の原則:
- 数値だけを見ない、「なぜ」を考える
- 短期と長期のバランスを考える
- リスクとリターンを天秤にかける
- 市場環境の変化を読む
- 常に改善の余地を探す""",
                messages=[{"role": "user", "content": prompt}],
            )
            
            return self._parse_json_response(response.content[0].text)
            
        except Exception as e:
            logger.error(f"総合分析エラー: {e}")
            return {"error": str(e)}

    def get_quick_recommendation(
        self,
        performance: dict,
        industry: str = "健康食品",
    ) -> str:
        """クイック推奨（シンプルな一言）"""
        
        # ベンチマーク比較
        benchmark = self.market_analyzer.compare_to_benchmark(industry, performance)
        grade = benchmark.get("overall_assessment", {}).get("grade", "C")
        
        if grade == "A":
            return "🟢 素晴らしいパフォーマンス！予算拡大を検討しましょう。"
        elif grade == "B":
            return "🟡 良好です。さらなる改善の余地があります。"
        elif grade == "C":
            return "🟠 業界平均レベル。CTRまたはCVRの改善に注力しましょう。"
        else:
            return "🔴 改善が必要です。クリエイティブとLPを見直しましょう。"

    def simulate_scenario(
        self,
        current_state: dict,
        scenario: str,
    ) -> dict:
        """シナリオシミュレーション（What-If分析）"""
        return self.predictor.what_if(current_state, scenario)

    def get_daily_briefing(
        self,
        projects: list[dict],
    ) -> dict[str, Any]:
        """
        毎日のブリーフィングを生成
        
        Args:
            projects: 案件リスト（各案件のパフォーマンスデータ含む）
        
        Returns:
            dict: 日次ブリーフィング
        """
        briefing = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "summary": {},
            "alerts": [],
            "opportunities": [],
            "recommendations": [],
        }
        
        total_spend = 0
        total_conversions = 0
        
        for proj in projects:
            perf = proj.get("performance", {})
            total_spend += perf.get("spend", 0)
            total_conversions += perf.get("conversions", 0)
            
            # アラートチェック
            target_cpa = proj.get("target_cpa", 0)
            current_cpa = perf.get("cpa", 0)
            
            if target_cpa and current_cpa > target_cpa * 1.5:
                briefing["alerts"].append({
                    "project": proj.get("name"),
                    "type": "critical",
                    "message": f"CPA ¥{current_cpa:,.0f} が目標の1.5倍を超過",
                })
            elif target_cpa and current_cpa > target_cpa * 1.2:
                briefing["alerts"].append({
                    "project": proj.get("name"),
                    "type": "warning",
                    "message": f"CPA ¥{current_cpa:,.0f} が目標を20%超過",
                })
            
            # 機会チェック
            if target_cpa and current_cpa < target_cpa * 0.7:
                briefing["opportunities"].append({
                    "project": proj.get("name"),
                    "message": f"CPA ¥{current_cpa:,.0f} が目標を30%下回る。予算拡大の検討を。",
                })
        
        briefing["summary"] = {
            "total_spend": total_spend,
            "total_conversions": total_conversions,
            "avg_cpa": total_spend / total_conversions if total_conversions > 0 else 0,
            "projects_count": len(projects),
            "alerts_count": len(briefing["alerts"]),
            "opportunities_count": len(briefing["opportunities"]),
        }
        
        return briefing

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


