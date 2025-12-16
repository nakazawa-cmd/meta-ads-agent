"""
パフォーマンスパターン学習エンジン
過去のデータから成功/失敗パターンを抽出・学習
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)


class PatternLearner:
    """
    パフォーマンスパターンを学習するエンジン
    
    機能:
    1. 過去パフォーマンスの蓄積
    2. 成功/失敗パターンの抽出
    3. 類似ケースの検索
    4. パターンに基づく予測
    """

    def __init__(self, storage_dir: str = None, anthropic_api_key: str = None):
        if storage_dir is None:
            storage_dir = str(Path(__file__).parent.parent / "storage" / "patterns")
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # データファイルパス
        self.history_file = self.storage_dir / "performance_history.json"
        self.patterns_file = self.storage_dir / "learned_patterns.json"
        
        # データ読み込み
        self.history = self._load_json(self.history_file, [])
        self.patterns = self._load_json(self.patterns_file, [])
        
        # Claude
        if anthropic_api_key:
            self.claude = Anthropic(api_key=anthropic_api_key)
        else:
            import config
            self.claude = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        
        logger.info(f"PatternLearner初期化: 履歴{len(self.history)}件, パターン{len(self.patterns)}件")

    def _load_json(self, path: Path, default: Any) -> Any:
        """JSONファイルを読み込み"""
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return default

    def _save_json(self, path: Path, data: Any):
        """JSONファイルを保存"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # =========================================================================
    # パフォーマンス履歴の蓄積
    # =========================================================================

    def record_performance(
        self,
        project_id: str,
        project_name: str,
        date: str,
        metrics: dict[str, float],
        context: dict[str, Any] = None,
        actions_taken: list[str] = None,
    ) -> bool:
        """
        パフォーマンスを記録
        
        Args:
            project_id: 案件ID
            project_name: 案件名
            date: 日付 (YYYY-MM-DD)
            metrics: 指標 (spend, impressions, clicks, conversions, ctr, cvr, cpa, roas)
            context: コンテキスト情報 (target_cpa, has_article_lp, offer等)
            actions_taken: 取ったアクション
        
        Returns:
            bool: 成功したかどうか
        """
        record = {
            "project_id": project_id,
            "project_name": project_name,
            "date": date,
            "recorded_at": datetime.now().isoformat(),
            "metrics": metrics,
            "context": context or {},
            "actions_taken": actions_taken or [],
        }
        
        self.history.append(record)
        self._save_json(self.history_file, self.history)
        
        logger.info(f"パフォーマンス記録: {project_name} ({date})")
        return True

    def get_project_history(
        self,
        project_id: str,
        days: int = 30,
    ) -> list[dict]:
        """特定案件の履歴を取得"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        return [
            h for h in self.history
            if h["project_id"] == project_id and h["date"] >= cutoff
        ]

    # =========================================================================
    # パターン抽出
    # =========================================================================

    def extract_patterns(self, min_records: int = 5) -> list[dict]:
        """
        蓄積データからパターンを抽出（AIによる分析）
        
        Args:
            min_records: パターン抽出に必要な最小レコード数
        
        Returns:
            list[dict]: 抽出されたパターン
        """
        if len(self.history) < min_records:
            logger.warning(f"データ不足: {len(self.history)}件 < {min_records}件")
            return []
        
        # AIにパターン抽出を依頼
        prompt = self._build_pattern_extraction_prompt()
        
        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                system="""あなたは広告運用データのパターン分析エキスパートです。
与えられたパフォーマンスデータから、成功/失敗のパターンを抽出してください。

重要なポイント:
- 相関関係と因果関係を区別する
- 単純な閾値ではなく、複合的な条件を見つける
- 例外や外れ値にも注意する
- 実用的で actionable なパターンを重視する

必ずJSON配列形式で回答:
[
  {
    "pattern_id": "pattern_001",
    "name": "パターン名",
    "type": "success/failure/warning",
    "conditions": {
      "ctr_range": [1.0, 3.0],
      "cvr_min": 0.3,
      "has_article_lp": true
    },
    "outcome": "期待される結果",
    "confidence": 0.85,
    "sample_count": 10,
    "description": "詳細説明",
    "recommendation": "このパターンの場合の推奨アクション"
  }
]""",
                messages=[{"role": "user", "content": prompt}],
            )
            
            patterns = self._parse_patterns_response(response.content[0].text)
            
            # パターンを保存
            self.patterns = patterns
            self._save_json(self.patterns_file, self.patterns)
            
            logger.info(f"{len(patterns)}件のパターンを抽出")
            return patterns
            
        except Exception as e:
            logger.error(f"パターン抽出エラー: {e}")
            return []

    def _build_pattern_extraction_prompt(self) -> str:
        """パターン抽出用プロンプトを構築"""
        # 履歴データを要約
        summary = []
        for h in self.history[-50:]:  # 直近50件
            m = h["metrics"]
            c = h.get("context", {})
            summary.append({
                "project": h["project_name"],
                "date": h["date"],
                "spend": m.get("spend", 0),
                "ctr": m.get("ctr", 0),
                "cvr": m.get("cvr", 0),
                "cpa": m.get("cpa", 0),
                "roas": m.get("roas", 0),
                "target_cpa": c.get("target_cpa"),
                "has_article_lp": c.get("has_article_lp"),
                "result": "success" if m.get("cpa", 999999) <= c.get("target_cpa", 0) else "failure"
            })
        
        return f"""以下の広告運用パフォーマンスデータから、成功/失敗のパターンを抽出してください。

## データ（{len(summary)}件）
```json
{json.dumps(summary, ensure_ascii=False, indent=2)}
```

## 分析指示
1. 成功パターン（CPA目標達成）の共通点を見つける
2. 失敗パターン（CPA目標未達成）の共通点を見つける
3. 注意が必要な警告パターンを見つける
4. 各パターンの条件、信頼度、推奨アクションを明確に

JSON形式で5-10個のパターンを出力してください。
"""

    def _parse_patterns_response(self, response_text: str) -> list[dict]:
        """AIレスポンスをパース"""
        try:
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSONパースエラー: {e}")
            return []

    # =========================================================================
    # 類似ケース検索
    # =========================================================================

    def find_similar_cases(
        self,
        current_metrics: dict,
        current_context: dict = None,
        top_n: int = 5,
    ) -> list[dict]:
        """
        現在の状況に類似した過去ケースを検索
        
        Args:
            current_metrics: 現在の指標
            current_context: 現在のコンテキスト
            top_n: 取得件数
        
        Returns:
            list[dict]: 類似ケースとその結果
        """
        if not self.history:
            return []
        
        scored_cases = []
        
        for h in self.history:
            score = self._calculate_similarity(
                current_metrics, h["metrics"],
                current_context, h.get("context", {}),
            )
            scored_cases.append({
                "record": h,
                "similarity_score": score,
            })
        
        # スコア降順でソート
        scored_cases.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return scored_cases[:top_n]

    def _calculate_similarity(
        self,
        metrics1: dict,
        metrics2: dict,
        context1: dict = None,
        context2: dict = None,
    ) -> float:
        """類似度スコアを計算"""
        score = 0.0
        
        # 指標の類似度（正規化した差分の逆数）
        metric_keys = ["ctr", "cvr", "cpc", "cpa", "roas"]
        for key in metric_keys:
            v1 = metrics1.get(key, 0)
            v2 = metrics2.get(key, 0)
            if v1 > 0 and v2 > 0:
                diff = abs(v1 - v2) / max(v1, v2)
                score += (1 - diff) * 0.15  # 各指標15%
        
        # コンテキストの類似度
        if context1 and context2:
            # 記事LP有無
            if context1.get("has_article_lp") == context2.get("has_article_lp"):
                score += 0.1
            
            # 目標CPA近似
            t1 = context1.get("target_cpa", 0)
            t2 = context2.get("target_cpa", 0)
            if t1 > 0 and t2 > 0:
                diff = abs(t1 - t2) / max(t1, t2)
                score += (1 - diff) * 0.15
        
        return min(score, 1.0)

    # =========================================================================
    # パターンに基づく予測
    # =========================================================================

    def predict_outcome(
        self,
        metrics: dict,
        context: dict = None,
    ) -> dict[str, Any]:
        """
        現在の指標からパターンマッチして結果を予測
        
        Args:
            metrics: 現在の指標
            context: コンテキスト
        
        Returns:
            dict: 予測結果
        """
        matched_patterns = []
        
        for pattern in self.patterns:
            if self._matches_pattern(metrics, context, pattern):
                matched_patterns.append(pattern)
        
        # 類似ケースも取得
        similar_cases = self.find_similar_cases(metrics, context, top_n=3)
        
        # 予測を生成
        prediction = {
            "matched_patterns": matched_patterns,
            "similar_cases": [
                {
                    "project": c["record"]["project_name"],
                    "date": c["record"]["date"],
                    "similarity": c["similarity_score"],
                    "outcome": c["record"]["metrics"],
                }
                for c in similar_cases
            ],
            "prediction": self._generate_prediction(matched_patterns, similar_cases),
        }
        
        return prediction

    def _matches_pattern(
        self,
        metrics: dict,
        context: dict,
        pattern: dict,
    ) -> bool:
        """パターンにマッチするかチェック"""
        conditions = pattern.get("conditions", {})
        
        for key, value in conditions.items():
            # 範囲条件
            if key.endswith("_range") and isinstance(value, list):
                actual_key = key.replace("_range", "")
                actual = metrics.get(actual_key, 0)
                if not (value[0] <= actual <= value[1]):
                    return False
            
            # 最小値条件
            elif key.endswith("_min"):
                actual_key = key.replace("_min", "")
                actual = metrics.get(actual_key, 0)
                if actual < value:
                    return False
            
            # 最大値条件
            elif key.endswith("_max"):
                actual_key = key.replace("_max", "")
                actual = metrics.get(actual_key, 0)
                if actual > value:
                    return False
            
            # 完全一致（コンテキスト）
            elif context and key in context:
                if context[key] != value:
                    return False
        
        return True

    def _generate_prediction(
        self,
        patterns: list[dict],
        similar_cases: list[dict],
    ) -> dict:
        """パターンと類似ケースから予測を生成"""
        if not patterns and not similar_cases:
            return {"confidence": "low", "message": "データ不足のため予測困難"}
        
        # 成功パターンの数
        success_patterns = [p for p in patterns if p.get("type") == "success"]
        failure_patterns = [p for p in patterns if p.get("type") == "failure"]
        
        # 類似ケースの結果分析（簡易）
        successful_cases = 0
        for c in similar_cases:
            if c.get("similarity", 0) > 0.5:
                successful_cases += 1
        
        if len(success_patterns) > len(failure_patterns):
            return {
                "likely_outcome": "success",
                "confidence": "high" if len(success_patterns) >= 2 else "medium",
                "message": f"成功パターン{len(success_patterns)}件にマッチ",
                "matched_success_patterns": [p["name"] for p in success_patterns],
            }
        elif len(failure_patterns) > len(success_patterns):
            return {
                "likely_outcome": "failure",
                "confidence": "high" if len(failure_patterns) >= 2 else "medium",
                "message": f"失敗パターン{len(failure_patterns)}件にマッチ",
                "matched_failure_patterns": [p["name"] for p in failure_patterns],
                "recommendations": [p.get("recommendation") for p in failure_patterns],
            }
        else:
            return {
                "likely_outcome": "uncertain",
                "confidence": "low",
                "message": "成功/失敗の判断が難しい状況",
            }

    # =========================================================================
    # サンプルデータ生成（テスト用）
    # =========================================================================

    def generate_sample_data(self) -> int:
        """テスト用のサンプルデータを生成"""
        from datetime import date
        
        samples = [
            # 成功ケース: 記事LPあり、CTR高め
            {
                "project_id": "proj_001",
                "project_name": "美容サプリA",
                "metrics": {"spend": 100000, "impressions": 300000, "clicks": 6000, "conversions": 25, "ctr": 2.0, "cvr": 0.42, "cpa": 4000, "roas": 3.75},
                "context": {"target_cpa": 5000, "has_article_lp": True, "offer": "初回500円"},
            },
            {
                "project_id": "proj_001",
                "project_name": "美容サプリA",
                "metrics": {"spend": 120000, "impressions": 350000, "clicks": 7000, "conversions": 28, "ctr": 2.0, "cvr": 0.40, "cpa": 4286, "roas": 3.5},
                "context": {"target_cpa": 5000, "has_article_lp": True, "offer": "初回500円"},
            },
            # 失敗ケース: 記事LPなし、CVR低い
            {
                "project_id": "proj_002",
                "project_name": "ダイエットB",
                "metrics": {"spend": 80000, "impressions": 400000, "clicks": 4000, "conversions": 8, "ctr": 1.0, "cvr": 0.2, "cpa": 10000, "roas": 1.0},
                "context": {"target_cpa": 5000, "has_article_lp": False, "offer": "初回980円"},
            },
            {
                "project_id": "proj_002",
                "project_name": "ダイエットB",
                "metrics": {"spend": 90000, "impressions": 450000, "clicks": 4500, "conversions": 7, "ctr": 1.0, "cvr": 0.16, "cpa": 12857, "roas": 0.8},
                "context": {"target_cpa": 5000, "has_article_lp": False, "offer": "初回980円"},
            },
            # 成功ケース: 高単価、ROAS重視
            {
                "project_id": "proj_003",
                "project_name": "オンライン講座C",
                "metrics": {"spend": 200000, "impressions": 400000, "clicks": 8000, "conversions": 20, "ctr": 2.0, "cvr": 0.25, "cpa": 10000, "roas": 10.0},
                "context": {"target_cpa": 15000, "target_roas": 5.0, "has_article_lp": True, "offer": "無料体験"},
            },
            {
                "project_id": "proj_003",
                "project_name": "オンライン講座C",
                "metrics": {"spend": 250000, "impressions": 500000, "clicks": 10000, "conversions": 22, "ctr": 2.0, "cvr": 0.22, "cpa": 11364, "roas": 8.8},
                "context": {"target_cpa": 15000, "target_roas": 5.0, "has_article_lp": True, "offer": "無料体験"},
            },
            # 失敗ケース: CTR低い
            {
                "project_id": "proj_004",
                "project_name": "EC商品D",
                "metrics": {"spend": 50000, "impressions": 250000, "clicks": 1250, "conversions": 5, "ctr": 0.5, "cvr": 0.4, "cpa": 10000, "roas": 1.5},
                "context": {"target_cpa": 3000, "has_article_lp": False, "offer": "送料無料"},
            },
            # 成功ケース: バランス良好
            {
                "project_id": "proj_005",
                "project_name": "健康食品E",
                "metrics": {"spend": 150000, "impressions": 500000, "clicks": 7500, "conversions": 30, "ctr": 1.5, "cvr": 0.4, "cpa": 5000, "roas": 4.0},
                "context": {"target_cpa": 6000, "has_article_lp": True, "offer": "初回半額"},
            },
            {
                "project_id": "proj_005",
                "project_name": "健康食品E",
                "metrics": {"spend": 180000, "impressions": 600000, "clicks": 9000, "conversions": 36, "ctr": 1.5, "cvr": 0.4, "cpa": 5000, "roas": 4.0},
                "context": {"target_cpa": 6000, "has_article_lp": True, "offer": "初回半額"},
            },
        ]
        
        # 日付を付けて保存
        today = date.today()
        for i, sample in enumerate(samples):
            sample_date = (today - timedelta(days=len(samples) - i)).strftime("%Y-%m-%d")
            self.record_performance(
                project_id=sample["project_id"],
                project_name=sample["project_name"],
                date=sample_date,
                metrics=sample["metrics"],
                context=sample["context"],
            )
        
        return len(samples)


