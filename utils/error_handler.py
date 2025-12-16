"""
エラーハンドリングユーティリティ
API エラー、認証エラー等を適切に処理
"""
import logging
import functools
from typing import Any, Callable

logger = logging.getLogger(__name__)


class MetaAPIError(Exception):
    """Meta API関連のエラー"""
    
    def __init__(self, message: str, error_code: str = None, error_subcode: str = None):
        self.message = message
        self.error_code = error_code
        self.error_subcode = error_subcode
        super().__init__(self.message)

    def get_user_friendly_message(self) -> str:
        """ユーザーにわかりやすいエラーメッセージを返す"""
        error_messages = {
            "190": "アクセストークンが無効または期限切れです。再認証してください。",
            "17": "APIレート制限に達しました。しばらく待ってから再試行してください。",
            "100": "パラメータが無効です。入力内容を確認してください。",
            "200": "アクセス権限がありません。アカウントの権限を確認してください。",
            "294": "広告アカウントが無効化されています。",
            "1487390": "予算が最低金額を下回っています。",
        }
        
        if self.error_code:
            return error_messages.get(str(self.error_code), self.message)
        return self.message


class ConfigurationError(Exception):
    """設定関連のエラー"""
    pass


class ValidationError(Exception):
    """バリデーションエラー"""
    pass


def safe_api_call(default_return=None, log_error: bool = True):
    """
    API呼び出しを安全にラップするデコレータ
    
    Args:
        default_return: エラー時のデフォルト戻り値
        log_error: エラーをログに出力するか
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"{func.__name__} でエラー発生: {e}")
                
                # Meta APIエラーの解析
                error_str = str(e)
                if "OAuthException" in error_str or "Error validating access token" in error_str:
                    raise MetaAPIError(
                        "アクセストークンが無効です",
                        error_code="190"
                    )
                elif "Rate limit" in error_str or "(#17)" in error_str:
                    raise MetaAPIError(
                        "APIレート制限に達しました",
                        error_code="17"
                    )
                elif "(#100)" in error_str:
                    raise MetaAPIError(
                        f"パラメータエラー: {error_str}",
                        error_code="100"
                    )
                
                return default_return
        return wrapper
    return decorator


def validate_required_fields(data: dict, required_fields: list[str]) -> list[str]:
    """
    必須フィールドのバリデーション
    
    Args:
        data: 検証するデータ
        required_fields: 必須フィールドのリスト
    
    Returns:
        list[str]: 欠けているフィールドのリスト
    """
    missing = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing.append(field)
    return missing


def format_error_for_ui(error: Exception) -> dict:
    """
    エラーをUI表示用にフォーマット
    
    Args:
        error: 発生した例外
    
    Returns:
        dict: {"type": str, "message": str, "suggestion": str}
    """
    if isinstance(error, MetaAPIError):
        return {
            "type": "api_error",
            "message": error.get_user_friendly_message(),
            "suggestion": "設定を確認するか、しばらく待ってから再試行してください。",
        }
    elif isinstance(error, ConfigurationError):
        return {
            "type": "config_error",
            "message": str(error),
            "suggestion": ".envファイルの設定を確認してください。",
        }
    elif isinstance(error, ValidationError):
        return {
            "type": "validation_error",
            "message": str(error),
            "suggestion": "入力内容を確認してください。",
        }
    else:
        return {
            "type": "unknown_error",
            "message": str(error),
            "suggestion": "問題が続く場合は、ログを確認してください。",
        }


def log_api_call(func_name: str, params: dict = None, result: Any = None, error: Exception = None):
    """
    API呼び出しをログに記録
    
    Args:
        func_name: 関数名
        params: パラメータ（機密情報は除く）
        result: 結果
        error: エラー
    """
    if error:
        logger.error(f"[API] {func_name} - ERROR: {error}")
    elif result:
        logger.info(f"[API] {func_name} - SUCCESS")
    else:
        logger.debug(f"[API] {func_name} - params: {params}")

