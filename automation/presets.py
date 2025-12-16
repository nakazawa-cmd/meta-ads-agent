"""
入稿プリセット管理モジュール
商品情報、ページ設定などを保存・呼び出し
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

PRESETS_FILE = Path(__file__).parent.parent / "storage" / "presets.json"


class PresetManager:
    """
    入稿プリセットを管理するクラス
    
    機能:
    1. 商品プリセット（名前、URL、説明等）
    2. ページプリセット（ページID、Instagram ID）
    3. デフォルト設定（予算、テキスト生成ON/OFF）
    """

    def __init__(self):
        self.presets_file = PRESETS_FILE
        self.presets = self._load_presets()
        logger.info("PresetManager初期化完了")

    def _load_presets(self) -> dict:
        """プリセットをファイルから読み込み"""
        if self.presets_file.exists():
            try:
                with open(self.presets_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"プリセット読み込みエラー: {e}")
        
        return {
            "products": [],
            "pages": [],
            "default_settings": {
                "daily_budget": 10000,
                "auto_generate_texts": True,
            },
        }

    def _save_presets(self):
        """プリセットをファイルに保存"""
        try:
            self.presets_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.presets_file, "w", encoding="utf-8") as f:
                json.dump(self.presets, f, ensure_ascii=False, indent=2)
            logger.info("プリセットを保存しました")
        except Exception as e:
            logger.error(f"プリセット保存エラー: {e}")

    # =========================================================================
    # 商品プリセット
    # =========================================================================

    def get_products(self) -> list[dict]:
        """商品プリセット一覧を取得"""
        return self.presets.get("products", [])

    def add_product(
        self,
        name: str,
        url: str,
        description: str = "",
        target_audience: str = "",
        default_budget: int = None,
    ) -> str:
        """
        商品プリセットを追加
        
        Returns:
            str: 商品ID
        """
        product_id = f"product_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        product = {
            "id": product_id,
            "name": name,
            "url": url,
            "description": description,
            "target_audience": target_audience,
            "default_budget": default_budget,
            "created_at": datetime.now().isoformat(),
        }
        
        if "products" not in self.presets:
            self.presets["products"] = []
        
        self.presets["products"].append(product)
        self._save_presets()
        
        logger.info(f"商品プリセットを追加: {name}")
        return product_id

    def update_product(self, product_id: str, **kwargs):
        """商品プリセットを更新"""
        products = self.presets.get("products", [])
        for product in products:
            if product["id"] == product_id:
                product.update(kwargs)
                product["updated_at"] = datetime.now().isoformat()
                self._save_presets()
                return True
        return False

    def delete_product(self, product_id: str):
        """商品プリセットを削除"""
        products = self.presets.get("products", [])
        self.presets["products"] = [p for p in products if p["id"] != product_id]
        self._save_presets()

    def get_product(self, product_id: str) -> dict | None:
        """商品プリセットを取得"""
        products = self.presets.get("products", [])
        for product in products:
            if product["id"] == product_id:
                return product
        return None

    # =========================================================================
    # ページプリセット
    # =========================================================================

    def get_pages(self) -> list[dict]:
        """ページプリセット一覧を取得"""
        return self.presets.get("pages", [])

    def add_page(
        self,
        name: str,
        page_id: str,
        instagram_id: str = "",
    ) -> str:
        """
        ページプリセットを追加
        
        Returns:
            str: 内部ID
        """
        internal_id = f"page_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        page = {
            "internal_id": internal_id,
            "name": name,
            "page_id": page_id,
            "instagram_id": instagram_id,
            "created_at": datetime.now().isoformat(),
        }
        
        if "pages" not in self.presets:
            self.presets["pages"] = []
        
        self.presets["pages"].append(page)
        self._save_presets()
        
        logger.info(f"ページプリセットを追加: {name}")
        return internal_id

    def delete_page(self, internal_id: str):
        """ページプリセットを削除"""
        pages = self.presets.get("pages", [])
        self.presets["pages"] = [p for p in pages if p["internal_id"] != internal_id]
        self._save_presets()

    def get_page(self, internal_id: str) -> dict | None:
        """ページプリセットを取得"""
        pages = self.presets.get("pages", [])
        for page in pages:
            if page["internal_id"] == internal_id:
                return page
        return None

    # =========================================================================
    # デフォルト設定
    # =========================================================================

    def get_defaults(self) -> dict:
        """デフォルト設定を取得"""
        return self.presets.get("default_settings", {
            "daily_budget": 10000,
            "auto_generate_texts": True,
        })

    def set_defaults(self, **kwargs):
        """デフォルト設定を更新"""
        if "default_settings" not in self.presets:
            self.presets["default_settings"] = {}
        
        self.presets["default_settings"].update(kwargs)
        self._save_presets()


# シングルトンインスタンス
_preset_manager = None


def get_preset_manager() -> PresetManager:
    """PresetManagerのシングルトンインスタンスを取得"""
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = PresetManager()
    return _preset_manager

