"""
知識ベース統合モジュール
ベクトル検索 + Notion + Claude を統合
"""
import logging
from typing import Any

from anthropic import Anthropic

from .vector_store import VectorStore
from .document_collector import DocumentCollector

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """知識ベースを統合管理するクラス"""

    def __init__(
        self,
        anthropic_api_key: str = None,
        notion_token: str = None,
    ):
        self.vector_store = VectorStore()
        self.collector = DocumentCollector()
        
        # Claude
        if anthropic_api_key:
            self.claude = Anthropic(api_key=anthropic_api_key)
        else:
            import config
            self.claude = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        
        # Notion（オプション）
        self.notion_token = notion_token

    def initialize_knowledge(self) -> dict[str, int]:
        """
        知識ベースを初期化（ドキュメント収集・ベクトル化）
        
        Returns:
            dict: 各コレクションに追加されたドキュメント数
        """
        logger.info("知識ベースを初期化中...")
        results = {}
        
        # Meta公式ドキュメント
        meta_docs = self.collector.collect_meta_marketing_api_docs()
        if meta_docs:
            documents = [d["content"] for d in meta_docs]
            metadatas = [{
                "title": d["title"],
                "category": d["category"],
                "source": d["source"],
            } for d in meta_docs]
            
            self.vector_store.add_documents(
                "meta_official_docs",
                documents,
                metadatas,
            )
            results["meta_official_docs"] = len(meta_docs)
        
        # 業界知見
        industry_docs = self.collector.collect_industry_knowledge()
        if industry_docs:
            documents = [d["content"] for d in industry_docs]
            metadatas = [{
                "title": d["title"],
                "category": d["category"],
                "source": d["source"],
            } for d in industry_docs]
            
            self.vector_store.add_documents(
                "industry_knowledge",
                documents,
                metadatas,
            )
            results["industry_knowledge"] = len(industry_docs)
        
        logger.info(f"知識ベース初期化完了: {results}")
        return results

    def search_knowledge(
        self,
        query: str,
        n_results: int = 5,
        collections: list[str] = None,
    ) -> list[dict[str, Any]]:
        """
        知識を検索
        
        Args:
            query: 検索クエリ
            n_results: 取得件数
            collections: 検索対象コレクション（Noneなら全て）
        
        Returns:
            list[dict]: 検索結果
        """
        if collections:
            results = []
            for col in collections:
                results.extend(self.vector_store.search(col, query, n_results))
            return results
        else:
            all_results = self.vector_store.search_all(query, n_results)
            # フラット化
            flat_results = []
            for col_name, col_results in all_results.items():
                for r in col_results:
                    r["collection"] = col_name
                    flat_results.append(r)
            return flat_results

    def get_ai_judgment(
        self,
        context: dict[str, Any],
        question: str = None,
    ) -> dict[str, Any]:
        """
        AIによる総合判断を取得
        
        Args:
            context: 判断に必要なコンテキスト
                - performance: パフォーマンスデータ
                - project: 案件情報
                - history: 過去の履歴
            question: 具体的な質問（オプション）
        
        Returns:
            dict: AIの判断結果
        """
        # 関連知識を検索
        search_query = self._build_search_query(context)
        relevant_knowledge = self.search_knowledge(search_query, n_results=5)
        
        # プロンプトを構築
        prompt = self._build_judgment_prompt(context, relevant_knowledge, question)
        
        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                system=self._get_system_prompt(),
                messages=[{"role": "user", "content": prompt}],
            )
            
            return self._parse_judgment_response(response.content[0].text)
        except Exception as e:
            logger.error(f"AI判断エラー: {e}")
            return {"error": str(e)}

    def _get_system_prompt(self) -> str:
        """システムプロンプトを取得"""
        return """あなたはMeta広告（Facebook/Instagram広告）の運用エキスパートAIです。

あなたの特徴:
1. Meta広告のアルゴリズムを深く理解している
2. 単純なルールベースではなく、状況を総合的に判断する
3. データに基づいた論理的な判断を行う
4. 具体的で実行可能なアドバイスを提供する

判断の原則:
- 「CPAが高いから停止」のような単純な判断はしない
- なぜその数値になっているのか、原因を分析する
- 改善余地があるかを検討する
- 短期的な変動と長期的なトレンドを区別する
- 案件の特性（記事LP有無、オファー内容など）を考慮する

回答フォーマット:
必ずJSON形式で回答してください。
{
  "judgment": "継続/様子見/停止/調整",
  "confidence": "high/medium/low",
  "reasoning": "判断の理由（詳細）",
  "analysis": {
    "current_status": "現状の評価",
    "root_cause": "問題の根本原因（あれば）",
    "improvement_potential": "改善の余地"
  },
  "recommendations": [
    {"priority": "high/medium/low", "action": "具体的なアクション", "expected_impact": "期待効果"}
  ],
  "risks": ["リスクや注意点"],
  "next_steps": ["次にすべきこと"]
}"""

    def _build_search_query(self, context: dict) -> str:
        """検索クエリを構築"""
        queries = []
        
        performance = context.get("performance", {})
        project = context.get("project", {})
        
        # パフォーマンスに基づくクエリ
        if performance.get("cpa") and project.get("target_cpa"):
            if performance["cpa"] > project["target_cpa"] * 1.2:
                queries.append("CPA改善 コスト削減")
        
        if performance.get("ctr") and performance["ctr"] < 1.0:
            queries.append("CTR改善 クリエイティブ")
        
        if performance.get("cvr") and performance["cvr"] < 1.0:
            queries.append("CVR改善 LP最適化")
        
        # 案件特性に基づくクエリ
        if project.get("has_article_lp"):
            queries.append("記事LP 最適化")
        
        if not queries:
            queries.append("広告運用 最適化 ベストプラクティス")
        
        return " ".join(queries)

    def _build_judgment_prompt(
        self,
        context: dict,
        knowledge: list[dict],
        question: str = None,
    ) -> str:
        """判断用プロンプトを構築"""
        prompt_parts = []
        
        # 案件情報
        project = context.get("project", {})
        if project:
            prompt_parts.append(f"""## 案件情報
- 案件名: {project.get('name', '不明')}
- 目標CPA: {project.get('target_cpa', '未設定')}円
- 目標ROAS: {project.get('target_roas', '未設定')}
- 記事LP: {'あり' if project.get('has_article_lp') else 'なし'}
- オファー: {project.get('offer', '不明')}
""")
        
        # パフォーマンスデータ
        performance = context.get("performance", {})
        if performance:
            prompt_parts.append(f"""## 現在のパフォーマンス
- 広告費: ¥{performance.get('spend', 0):,.0f}
- インプレッション: {performance.get('impressions', 0):,}
- クリック: {performance.get('clicks', 0):,}
- コンバージョン: {performance.get('conversions', 0):,}
- CTR: {performance.get('ctr', 0):.2f}%
- CPC: ¥{performance.get('cpc', 0):,.0f}
- CVR: {performance.get('cvr', 0):.2f}%
- CPA: ¥{performance.get('cpa', 0):,.0f}
- ROAS: {performance.get('roas', 0):.2f}x
""")
        
        # 関連知識
        if knowledge:
            prompt_parts.append("## 関連する知識・ベストプラクティス")
            for k in knowledge[:3]:  # 上位3件
                prompt_parts.append(f"""
### {k.get('metadata', {}).get('title', '無題')}
{k.get('document', '')[:500]}
""")
        
        # 質問
        if question:
            prompt_parts.append(f"\n## 質問\n{question}")
        else:
            prompt_parts.append("""
## 質問
このパフォーマンスデータと案件情報に基づいて、総合的な判断と推奨アクションを教えてください。
単純にCPAが高い/低いという判断ではなく、なぜその数値になっているのか、改善余地はあるか、
具体的に何をすべきかを分析してください。
""")
        
        return "\n".join(prompt_parts)

    def _parse_judgment_response(self, response_text: str) -> dict:
        """AIレスポンスをパース"""
        import json
        
        try:
            # JSON部分を抽出
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {
                "judgment": "unknown",
                "raw_response": response_text,
                "error": "JSON parse error",
            }

    def add_operation_tip(
        self,
        title: str,
        content: str,
        category: str,
        source: str = "自社検証",
    ) -> bool:
        """
        運用Tipsを追加
        
        Args:
            title: タイトル
            content: 内容
            category: カテゴリ
            source: ソース
        
        Returns:
            bool: 成功したかどうか
        """
        return self.vector_store.add_documents(
            "operation_tips",
            [content],
            [{"title": title, "category": category, "source": source}],
        )

    def add_performance_pattern(
        self,
        pattern_description: str,
        conditions: dict,
        outcome: str,
    ) -> bool:
        """
        パフォーマンスパターンを追加
        
        Args:
            pattern_description: パターンの説明
            conditions: 条件（CTR > 1.5%, CPC < 50円 など）
            outcome: 結果（CPA達成/未達成 など）
        
        Returns:
            bool: 成功したかどうか
        """
        content = f"""
パターン: {pattern_description}
条件: {conditions}
結果: {outcome}
"""
        return self.vector_store.add_documents(
            "performance_patterns",
            [content],
            [{"description": pattern_description, "outcome": outcome}],
        )

    def get_stats(self) -> dict[str, Any]:
        """知識ベースの統計を取得"""
        return self.vector_store.get_collection_stats()


