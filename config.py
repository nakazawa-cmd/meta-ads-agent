"""
Meta Ads Agent - 設定ファイル
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# ベースディレクトリ
BASE_DIR = Path(__file__).parent

# =============================================================================
# Meta API 設定
# =============================================================================
META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")

# 管理対象の広告アカウントID（複数可）
# フォーマット: "act_123456789" または "123456789"
META_AD_ACCOUNT_IDS = [
    aid.strip() 
    for aid in os.getenv("META_AD_ACCOUNT_IDS", "").split(",") 
    if aid.strip()
]

# API バージョン
META_API_VERSION = os.getenv("META_API_VERSION", "v21.0")

# =============================================================================
# Claude API 設定
# =============================================================================
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# =============================================================================
# Slack 設定
# =============================================================================
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# =============================================================================
# 自動化設定
# =============================================================================

# 入札最適化設定
BID_OPTIMIZATION = {
    # 目標CPA（円）- アカウントごとに上書き可能
    "default_target_cpa": float(os.getenv("DEFAULT_TARGET_CPA", "3000")),
    # 目標ROAS（倍率）
    "default_target_roas": float(os.getenv("DEFAULT_TARGET_ROAS", "3.0")),
    # 入札調整の最大変更率（%）
    "max_bid_change_percent": 20,
    # 最小データ期間（日）
    "min_data_days": 3,
    # 最小コンバージョン数
    "min_conversions": 5,
}

# クリエイティブ自動OFF設定
CREATIVE_AUTO_OFF = {
    # CTR閾値（%）- これ以下で警告
    "ctr_threshold": 0.5,
    # CVR閾値（%）- これ以下で警告
    "cvr_threshold": 1.0,
    # 連続低パフォーマンス日数
    "consecutive_days": 3,
    # 最小インプレッション数（判定に必要）
    "min_impressions": 1000,
    # 最小クリック数（CVR判定に必要）
    "min_clicks": 50,
}

# =============================================================================
# ストレージ設定
# =============================================================================
STORAGE_DIR = BASE_DIR / "storage"
PERFORMANCE_LOG_FILE = STORAGE_DIR / "performance_log.json"
OPERATION_LOG_FILE = STORAGE_DIR / "operation_log.json"

# =============================================================================
# ログ設定
# =============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


