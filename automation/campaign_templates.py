"""
キャンペーンテンプレート
ワンクリックでキャンペーンを作成するためのプリセット
"""
import logging
from datetime import datetime
from typing import Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)


# =============================================================================
# キャンペーンテンプレート定義
# =============================================================================

CAMPAIGN_TEMPLATES = {
    "asc_broad": {
        "name": "ASC ブロード配信",
        "description": "Advantage+ ショッピングキャンペーンをブロード配信で開始",
        "icon": "🚀",
        "objective": "OUTCOME_SALES",
        "is_asc": True,
        "defaults": {
            "daily_budget": 10000,  # 日予算1万円
            "optimization_goal": "OFFSITE_CONVERSIONS",
            "billing_event": "IMPRESSIONS",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "targeting": {
                "geo_locations": {"countries": ["JP"]},
                "age_min": 18,
                "age_max": 65,
                # ブロード = 興味関心なし
            },
        },
        "ad_defaults": {
            "call_to_action": "SHOP_NOW",
        },
    },
    "asc_retargeting": {
        "name": "ASC リターゲティング",
        "description": "サイト訪問者へのリターゲティング配信",
        "icon": "🎯",
        "objective": "OUTCOME_SALES",
        "is_asc": True,
        "defaults": {
            "daily_budget": 5000,
            "optimization_goal": "OFFSITE_CONVERSIONS",
            "billing_event": "IMPRESSIONS",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "targeting": {
                "geo_locations": {"countries": ["JP"]},
                # リターゲティング = カスタムオーディエンス使用
            },
        },
        "ad_defaults": {
            "call_to_action": "SHOP_NOW",
        },
        "requires": ["custom_audience"],
    },
    "traffic_follower": {
        "name": "トラフィック / フォロワー獲得",
        "description": "Instagramプロフィール訪問を促進",
        "icon": "👥",
        "objective": "OUTCOME_TRAFFIC",
        "is_asc": False,
        "defaults": {
            "daily_budget": 3000,
            "optimization_goal": "LINK_CLICKS",
            "billing_event": "IMPRESSIONS",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "targeting": {
                "geo_locations": {"countries": ["JP"]},
                "age_min": 18,
                "age_max": 45,
            },
        },
        "ad_defaults": {
            "call_to_action": "LEARN_MORE",
        },
    },
    "engagement": {
        "name": "エンゲージメント",
        "description": "投稿へのいいね・コメント・シェアを促進",
        "icon": "💬",
        "objective": "OUTCOME_ENGAGEMENT",
        "is_asc": False,
        "defaults": {
            "daily_budget": 2000,
            "optimization_goal": "POST_ENGAGEMENT",
            "billing_event": "IMPRESSIONS",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "targeting": {
                "geo_locations": {"countries": ["JP"]},
                "age_min": 18,
                "age_max": 55,
            },
        },
        "ad_defaults": {
            "call_to_action": "LIKE_PAGE",
        },
    },
}


# =============================================================================
# テキスト自動生成
# =============================================================================

class AdTextGenerator:
    """AIで広告テキストを自動生成"""

    def __init__(self):
        try:
            import config
            self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        except Exception as e:
            logger.warning(f"Anthropic初期化エラー: {e}")
            self.client = None

    def generate_ad_texts(
        self,
        product_name: str,
        product_description: str = "",
        target_audience: str = "",
        campaign_type: str = "sales",
        num_variations: int = 3,
    ) -> list[dict]:
        """
        広告テキストを自動生成
        
        Args:
            product_name: 商品/サービス名
            product_description: 商品説明
            target_audience: ターゲット層
            campaign_type: キャンペーンタイプ（sales, traffic, engagement）
            num_variations: 生成するバリエーション数
        
        Returns:
            list[dict]: [{"headline": "...", "primary_text": "...", "description": "..."}, ...]
        """
        if not self.client:
            return self._get_default_texts(product_name, campaign_type)

        prompt = f"""あなたはMeta広告（Instagram/Facebook）の広告コピーライターです。
以下の商品/サービスの広告テキストを{num_variations}パターン生成してください。

【商品/サービス】
名前: {product_name}
説明: {product_description or "（なし）"}
ターゲット: {target_audience or "一般"}
キャンペーンタイプ: {campaign_type}

【生成するテキスト】
各パターンについて以下を生成:
1. headline（見出し）: 25文字以内、インパクトのある一言
2. primary_text（メインテキスト）: 125文字以内、商品の魅力を伝える本文
3. description（説明）: 30文字以内、CTAを促す短い説明

【ルール】
- 日本語で生成
- 絵文字は適度に使用OK
- 誇大広告にならないよう注意
- {campaign_type}に適したトーンで

JSON形式で出力してください:
[
  {{"headline": "...", "primary_text": "...", "description": "..."}},
  ...
]
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
            
            # JSONをパース
            import json
            content = response.content[0].text
            
            # JSON部分を抽出
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
            
        except Exception as e:
            logger.error(f"テキスト生成エラー: {e}")
        
        return self._get_default_texts(product_name, campaign_type)

    def _get_default_texts(self, product_name: str, campaign_type: str) -> list[dict]:
        """デフォルトのテキストテンプレート"""
        if campaign_type == "traffic":
            return [
                {
                    "headline": f"{product_name}をチェック",
                    "primary_text": f"{product_name}の最新情報をプロフィールでチェック！フォローして最新情報をゲットしよう。",
                    "description": "プロフィールを見る",
                },
            ]
        elif campaign_type == "engagement":
            return [
                {
                    "headline": "いいね！してね",
                    "primary_text": f"{product_name}の投稿に「いいね！」お願いします✨",
                    "description": "いいね！する",
                },
            ]
        else:  # sales
            return [
                {
                    "headline": f"{product_name}を今すぐ購入",
                    "primary_text": f"✨ {product_name}が今だけお得！\n\n詳細はショップでチェック👇",
                    "description": "今すぐ購入",
                },
            ]


# =============================================================================
# ワンクリック入稿エンジン
# =============================================================================

class QuickLaunchEngine:
    """
    ワンクリックでキャンペーンを作成・入稿
    """

    def __init__(self, meta_auth, integrated_agent=None):
        self.meta_auth = meta_auth
        self.agent = integrated_agent
        self.text_generator = AdTextGenerator()
        logger.info("QuickLaunchEngine初期化完了")

    def get_available_templates(self) -> list[dict]:
        """利用可能なテンプレート一覧を取得"""
        templates = []
        for key, template in CAMPAIGN_TEMPLATES.items():
            templates.append({
                "id": key,
                "name": template["name"],
                "description": template["description"],
                "icon": template["icon"],
                "defaults": template["defaults"],
                "requires": template.get("requires", []),
            })
        return templates

    def get_creative_library(self, account_id: str, limit: int = 20) -> list[dict]:
        """
        クリエイティブライブラリから画像/動画を取得
        
        Args:
            account_id: アカウントID
            limit: 取得件数
        
        Returns:
            list[dict]: [{"id": "...", "url": "...", "type": "image/video"}, ...]
        """
        try:
            from meta_api.creative import CreativeManager
            ad_account = self.meta_auth.get_ad_account(account_id)
            creative_manager = CreativeManager(ad_account)
            
            # 既存のクリエイティブを取得
            creatives = creative_manager.get_creatives(limit=limit)
            
            result = []
            for cr in creatives:
                result.append({
                    "id": cr.get("id"),
                    "name": cr.get("name", ""),
                    "thumbnail_url": cr.get("thumbnail_url"),
                    "type": "creative",
                })
            
            return result
            
        except Exception as e:
            logger.error(f"クリエイティブライブラリ取得エラー: {e}")
            return []

    def get_ad_images(self, account_id: str, limit: int = 50) -> list[dict]:
        """
        アカウントの画像一覧を取得
        
        Args:
            account_id: アカウントID
            limit: 取得件数
        
        Returns:
            list[dict]: [{"hash": "...", "url": "...", "name": "..."}, ...]
        """
        try:
            ad_account = self.meta_auth.get_ad_account(account_id)
            
            images = ad_account.get_ad_images(
                fields=["hash", "url", "name", "created_time"],
                params={"limit": limit},
            )
            
            result = []
            for img in images:
                result.append({
                    "hash": img.get("hash"),
                    "url": img.get("url"),
                    "name": img.get("name", ""),
                    "created_time": img.get("created_time"),
                })
            
            return result
            
        except Exception as e:
            logger.error(f"画像一覧取得エラー: {e}")
            return []

    def quick_launch(
        self,
        account_id: str,
        template_id: str,
        product_name: str,
        page_id: str,
        link_url: str,
        image_hashes: list[str] = None,
        creative_ids: list[str] = None,
        custom_budget: int = None,
        custom_texts: list[dict] = None,
        auto_generate_texts: bool = True,
        campaign_name_prefix: str = "",
    ) -> dict:
        """
        ワンクリックでキャンペーンを作成
        
        Args:
            account_id: アカウントID
            template_id: テンプレートID
            product_name: 商品/サービス名
            page_id: FacebookページID
            link_url: リンク先URL
            image_hashes: 使用する画像のハッシュリスト
            creative_ids: 既存クリエイティブIDリスト
            custom_budget: カスタム予算（省略でテンプレートデフォルト）
            custom_texts: カスタムテキスト（省略で自動生成）
            auto_generate_texts: テキストを自動生成するか
            campaign_name_prefix: キャンペーン名のプレフィックス
        
        Returns:
            dict: 作成結果
        """
        template = CAMPAIGN_TEMPLATES.get(template_id)
        if not template:
            return {"success": False, "error": f"テンプレート {template_id} が見つかりません"}

        try:
            # マネージャー取得
            from meta_api.campaigns import CampaignManager
            from meta_api.adsets import AdSetManager
            from meta_api.ads import AdManager
            
            ad_account = self.meta_auth.get_ad_account(account_id)
            campaign_manager = CampaignManager(ad_account)
            adset_manager = AdSetManager(ad_account)
            ad_manager = AdManager(ad_account)
            
            defaults = template["defaults"]
            ad_defaults = template.get("ad_defaults", {})
            
            # 予算
            daily_budget = custom_budget or defaults["daily_budget"]
            
            # キャンペーン名
            date_str = datetime.now().strftime("%Y%m%d")
            campaign_name = f"{campaign_name_prefix}{template['name']}_{product_name}_{date_str}"
            
            # 1. キャンペーン作成
            campaign_result = campaign_manager.create_campaign(
                name=campaign_name,
                objective=template["objective"],
                status="PAUSED",  # 最初は停止状態
                daily_budget=daily_budget if template.get("is_asc") else None,
            )
            
            if not campaign_result:
                return {"success": False, "error": "キャンペーン作成に失敗"}
            
            campaign_id = campaign_result["id"]
            
            # 2. 広告セット作成（ASC以外）
            adset_id = None
            if not template.get("is_asc"):
                adset_result = adset_manager.create_adset(
                    campaign_id=campaign_id,
                    name=f"{campaign_name}_adset",
                    daily_budget=daily_budget,
                    optimization_goal=defaults.get("optimization_goal", "LINK_CLICKS"),
                    billing_event=defaults.get("billing_event", "IMPRESSIONS"),
                    bid_strategy=defaults.get("bid_strategy", "LOWEST_COST_WITHOUT_CAP"),
                    targeting=defaults.get("targeting", {}),
                    status="PAUSED",
                )
                
                if not adset_result:
                    return {
                        "success": False,
                        "error": "広告セット作成に失敗",
                        "campaign_id": campaign_id,
                    }
                
                adset_id = adset_result["id"]
            
            # 3. テキスト生成
            if custom_texts:
                ad_texts = custom_texts
            elif auto_generate_texts:
                campaign_type = "traffic" if "traffic" in template_id.lower() else "sales"
                ad_texts = self.text_generator.generate_ad_texts(
                    product_name=product_name,
                    campaign_type=campaign_type,
                    num_variations=1,
                )
            else:
                ad_texts = [{"headline": product_name, "primary_text": "", "description": ""}]
            
            # 4. 広告作成
            created_ads = []
            ad_text = ad_texts[0] if ad_texts else {}
            
            # 画像ハッシュから広告を作成
            if image_hashes:
                for i, image_hash in enumerate(image_hashes[:5]):  # 最大5つ
                    ad_result = ad_manager.create_ad_with_creative(
                        adset_id=adset_id or campaign_id,  # ASCの場合はキャンペーンID
                        name=f"{campaign_name}_ad_{i+1}",
                        page_id=page_id,
                        image_hash=image_hash,
                        message=ad_text.get("primary_text", ""),
                        link_url=link_url,
                        headline=ad_text.get("headline", ""),
                        description=ad_text.get("description", ""),
                        call_to_action=ad_defaults.get("call_to_action", "LEARN_MORE"),
                        status="PAUSED",
                    )
                    if ad_result:
                        created_ads.append(ad_result)
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "adset_id": adset_id,
                "ads_created": len(created_ads),
                "budget": daily_budget,
                "template": template["name"],
                "message": f"✅ {template['name']}キャンペーンを作成しました！（停止状態）",
            }
            
        except Exception as e:
            logger.error(f"ワンクリック入稿エラー: {e}")
            return {"success": False, "error": str(e)}

