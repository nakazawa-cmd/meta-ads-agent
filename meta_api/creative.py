"""
クリエイティブ管理モジュール
画像/動画のアップロードとクリエイティブ作成
"""
import logging
from pathlib import Path
from typing import Any

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adimage import AdImage
from facebook_business.adobjects.advideo import AdVideo

logger = logging.getLogger(__name__)


class CreativeManager:
    """クリエイティブの作成・管理を行うクラス"""

    def __init__(self, ad_account: AdAccount):
        self.ad_account = ad_account
        self.account_id = ad_account.get_id()

    # =========================================================================
    # 画像のアップロード
    # =========================================================================

    def upload_image(self, image_path: str, name: str = None) -> dict | None:
        """
        画像をアップロード
        
        Args:
            image_path: 画像ファイルのパス
            name: 画像の名前（オプション）
        
        Returns:
            dict: アップロード結果（hash, url等）
        """
        try:
            path = Path(image_path)
            if not path.exists():
                logger.error(f"画像ファイルが見つかりません: {image_path}")
                return None
            
            image = AdImage(parent_id=self.account_id)
            image[AdImage.Field.filename] = str(path)
            image.remote_create()
            
            result = {
                "hash": image.get(AdImage.Field.hash),
                "url": image.get(AdImage.Field.url),
                "name": name or path.stem,
            }
            
            logger.info(f"画像をアップロードしました: {result['name']}")
            return result
            
        except Exception as e:
            logger.error(f"画像アップロードエラー: {e}")
            return None

    def upload_image_from_url(self, image_url: str, name: str = None) -> dict | None:
        """
        URLから画像をアップロード
        
        Args:
            image_url: 画像のURL
            name: 画像の名前（オプション）
        
        Returns:
            dict: アップロード結果
        """
        try:
            image = AdImage(parent_id=self.account_id)
            image[AdImage.Field.url] = image_url
            image.remote_create()
            
            result = {
                "hash": image.get(AdImage.Field.hash),
                "url": image.get(AdImage.Field.url),
                "name": name or "uploaded_image",
            }
            
            logger.info(f"URLから画像をアップロードしました: {result['name']}")
            return result
            
        except Exception as e:
            logger.error(f"URL画像アップロードエラー: {e}")
            return None

    # =========================================================================
    # 動画のアップロード
    # =========================================================================

    def upload_video(self, video_path: str, name: str = None) -> dict | None:
        """
        動画をアップロード
        
        Args:
            video_path: 動画ファイルのパス
            name: 動画の名前（オプション）
        
        Returns:
            dict: アップロード結果（id等）
        """
        try:
            path = Path(video_path)
            if not path.exists():
                logger.error(f"動画ファイルが見つかりません: {video_path}")
                return None
            
            video = AdVideo(parent_id=self.account_id)
            video[AdVideo.Field.filepath] = str(path)
            video.remote_create()
            
            result = {
                "id": video.get("id"),
                "name": name or path.stem,
            }
            
            logger.info(f"動画をアップロードしました: {result['name']}")
            return result
            
        except Exception as e:
            logger.error(f"動画アップロードエラー: {e}")
            return None

    # =========================================================================
    # クリエイティブの作成
    # =========================================================================

    def create_image_creative(
        self,
        name: str,
        image_hash: str,
        page_id: str,
        message: str = None,
        link_url: str = None,
        headline: str = None,
        description: str = None,
        call_to_action: str = "LEARN_MORE",
    ) -> dict | None:
        """
        画像クリエイティブを作成
        
        Args:
            name: クリエイティブ名
            image_hash: アップロードした画像のhash
            page_id: FacebookページID
            message: 投稿テキスト（本文）
            link_url: リンク先URL
            headline: 見出し
            description: 説明文
            call_to_action: CTAボタン（LEARN_MORE, SHOP_NOW, SIGN_UP等）
        
        Returns:
            dict: 作成したクリエイティブの情報
        """
        try:
            creative_params = {
                "name": name,
                "object_story_spec": {
                    "page_id": page_id,
                    "link_data": {
                        "image_hash": image_hash,
                        "link": link_url or "https://example.com",
                        "message": message or "",
                        "name": headline or "",
                        "description": description or "",
                        "call_to_action": {
                            "type": call_to_action,
                        },
                    },
                },
            }
            
            creative = self.ad_account.create_ad_creative(params=creative_params)
            
            result = {
                "id": creative.get("id"),
                "name": name,
            }
            
            logger.info(f"画像クリエイティブを作成しました: {name}")
            return result
            
        except Exception as e:
            logger.error(f"画像クリエイティブ作成エラー: {e}")
            return None

    def create_video_creative(
        self,
        name: str,
        video_id: str,
        page_id: str,
        thumbnail_url: str = None,
        message: str = None,
        link_url: str = None,
        headline: str = None,
        description: str = None,
        call_to_action: str = "LEARN_MORE",
    ) -> dict | None:
        """
        動画クリエイティブを作成
        
        Args:
            name: クリエイティブ名
            video_id: アップロードした動画のID
            page_id: FacebookページID
            thumbnail_url: サムネイル画像URL
            message: 投稿テキスト（本文）
            link_url: リンク先URL
            headline: 見出し
            description: 説明文
            call_to_action: CTAボタン
        
        Returns:
            dict: 作成したクリエイティブの情報
        """
        try:
            video_data = {
                "video_id": video_id,
                "message": message or "",
                "name": headline or "",
                "description": description or "",
                "call_to_action": {
                    "type": call_to_action,
                    "value": {
                        "link": link_url or "https://example.com",
                    },
                },
            }
            
            if thumbnail_url:
                video_data["thumbnail_url"] = thumbnail_url
            
            creative_params = {
                "name": name,
                "object_story_spec": {
                    "page_id": page_id,
                    "video_data": video_data,
                },
            }
            
            creative = self.ad_account.create_ad_creative(params=creative_params)
            
            result = {
                "id": creative.get("id"),
                "name": name,
            }
            
            logger.info(f"動画クリエイティブを作成しました: {name}")
            return result
            
        except Exception as e:
            logger.error(f"動画クリエイティブ作成エラー: {e}")
            return None

    def create_carousel_creative(
        self,
        name: str,
        page_id: str,
        cards: list[dict],
        message: str = None,
        link_url: str = None,
    ) -> dict | None:
        """
        カルーセルクリエイティブを作成
        
        Args:
            name: クリエイティブ名
            page_id: FacebookページID
            cards: カルーセルカードのリスト
                   各カード: {"image_hash": "xxx", "link": "url", "name": "見出し", "description": "説明"}
            message: 投稿テキスト（本文）
            link_url: デフォルトリンク先URL
        
        Returns:
            dict: 作成したクリエイティブの情報
        """
        try:
            child_attachments = []
            for card in cards:
                child_attachments.append({
                    "image_hash": card.get("image_hash"),
                    "link": card.get("link") or link_url or "https://example.com",
                    "name": card.get("name", ""),
                    "description": card.get("description", ""),
                })
            
            creative_params = {
                "name": name,
                "object_story_spec": {
                    "page_id": page_id,
                    "link_data": {
                        "link": link_url or "https://example.com",
                        "message": message or "",
                        "child_attachments": child_attachments,
                    },
                },
            }
            
            creative = self.ad_account.create_ad_creative(params=creative_params)
            
            result = {
                "id": creative.get("id"),
                "name": name,
            }
            
            logger.info(f"カルーセルクリエイティブを作成しました: {name}")
            return result
            
        except Exception as e:
            logger.error(f"カルーセルクリエイティブ作成エラー: {e}")
            return None

    # =========================================================================
    # クリエイティブの取得
    # =========================================================================

    def get_creatives(self, limit: int = 100) -> list[dict]:
        """
        クリエイティブ一覧を取得
        
        Args:
            limit: 取得件数上限
        
        Returns:
            list[dict]: クリエイティブ情報のリスト
        """
        try:
            creatives = self.ad_account.get_ad_creatives(
                fields=[
                    "id",
                    "name",
                    "status",
                    "object_story_spec",
                    "thumbnail_url",
                ],
                params={"limit": limit},
            )
            
            result = []
            for creative in creatives:
                result.append({
                    "id": creative.get("id"),
                    "name": creative.get("name"),
                    "status": creative.get("status"),
                    "thumbnail_url": creative.get("thumbnail_url"),
                })
            
            logger.info(f"{len(result)}件のクリエイティブを取得しました")
            return result
            
        except Exception as e:
            logger.error(f"クリエイティブ取得エラー: {e}")
            return []

    def get_creative(self, creative_id: str) -> dict | None:
        """
        特定のクリエイティブを取得
        
        Args:
            creative_id: クリエイティブID
        
        Returns:
            dict: クリエイティブ情報
        """
        try:
            creative = AdCreative(creative_id)
            data = creative.api_get(fields=[
                "id",
                "name",
                "status",
                "object_story_spec",
                "thumbnail_url",
            ])
            
            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "status": data.get("status"),
                "object_story_spec": data.get("object_story_spec"),
                "thumbnail_url": data.get("thumbnail_url"),
            }
            
        except Exception as e:
            logger.error(f"クリエイティブ {creative_id} の取得に失敗: {e}")
            return None

