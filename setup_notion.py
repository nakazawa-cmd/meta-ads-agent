#!/usr/bin/env python3
"""
Notion データベース セットアップスクリプト

ページの下にデータベースを新規作成します。
"""
import sys
import logging
import json

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Notion API設定
NOTION_TOKEN = "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"

# 親ページID（データベースを作成する場所）
# ユーザーが共有したページのうち1つを親にする
PARENT_PAGE_ID = "2c8370a6-006f-80ae-af15-c9f25104e520"

# 作成されたデータベースIDを保存
created_db_ids = {}


def normalize_id(id_str: str) -> str:
    """NotionのIDをUUID形式に変換"""
    if "-" in id_str:
        return id_str
    return f"{id_str[:8]}-{id_str[8:12]}-{id_str[12:16]}-{id_str[16:20]}-{id_str[20:]}"


def create_database(headers, parent_page_id: str, title: str, properties: dict) -> str | None:
    """データベースを新規作成"""
    import requests
    
    response = requests.post(
        "https://api.notion.com/v1/databases",
        headers=headers,
        json={
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties,
        },
    )
    
    if response.status_code == 200:
        db_id = response.json().get("id")
        logger.info(f"✅ {title}: 作成完了 (ID: {db_id})")
        return db_id
    else:
        logger.error(f"❌ {title}: エラー - {response.text}")
        return None


def setup_databases():
    """データベースを新規作成"""
    import requests
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    
    parent_id = normalize_id(PARENT_PAGE_ID)
    
    # =========================================================================
    # 1. 案件管理DB
    # =========================================================================
    logger.info("\n📊 案件管理DBを作成中...")
    
    projects_properties = {
        "案件名": {"title": {}},
        "広告アカウントID": {"rich_text": {}},
        "目標CPA": {"number": {"format": "yen"}},
        "目標ROAS": {"number": {"format": "number"}},
        "記事URL": {"url": {}},
        "LP_URL": {"url": {}},
        "オファー内容": {"rich_text": {}},
        "ステータス": {
            "select": {
                "options": [
                    {"name": "配信中", "color": "green"},
                    {"name": "停止中", "color": "red"},
                    {"name": "テスト中", "color": "yellow"},
                ]
            }
        },
        "メモ": {"rich_text": {}},
    }
    
    db_id = create_database(headers, parent_id, "📊 案件管理", projects_properties)
    if not db_id:
        return False
    created_db_ids["projects"] = db_id

    # =========================================================================
    # 2. 運用ナレッジDB
    # =========================================================================
    logger.info("\n📚 運用ナレッジDBを作成中...")
    
    knowledge_properties = {
        "タイトル": {"title": {}},
        "カテゴリ": {
            "select": {
                "options": [
                    {"name": "予算", "color": "blue"},
                    {"name": "入札", "color": "green"},
                    {"name": "クリエイティブ", "color": "purple"},
                    {"name": "ターゲティング", "color": "orange"},
                    {"name": "アルゴリズム", "color": "pink"},
                    {"name": "その他", "color": "gray"},
                ]
            }
        },
        "ソース": {
            "select": {
                "options": [
                    {"name": "公式", "color": "blue"},
                    {"name": "通説", "color": "yellow"},
                    {"name": "自社検証", "color": "green"},
                ]
            }
        },
        "重要度": {
            "select": {
                "options": [
                    {"name": "高", "color": "red"},
                    {"name": "中", "color": "yellow"},
                    {"name": "低", "color": "gray"},
                ]
            }
        },
        "参照URL": {"url": {}},
    }
    
    db_id = create_database(headers, parent_id, "📚 運用ナレッジ", knowledge_properties)
    if not db_id:
        return False
    created_db_ids["knowledge"] = db_id

    # =========================================================================
    # 3. 運用ログDB
    # =========================================================================
    logger.info("\n📝 運用ログDBを作成中...")
    
    logs_properties = {
        "タイトル": {"title": {}},
        "日付": {"date": {}},
        "アクション": {
            "select": {
                "options": [
                    {"name": "予算変更", "color": "blue"},
                    {"name": "停止", "color": "red"},
                    {"name": "再開", "color": "green"},
                    {"name": "入札調整", "color": "purple"},
                    {"name": "クリエイティブ追加", "color": "orange"},
                    {"name": "その他", "color": "gray"},
                ]
            }
        },
        "理由": {"rich_text": {}},
        "結果": {"rich_text": {}},
    }
    
    db_id = create_database(headers, parent_id, "📝 運用ログ", logs_properties)
    if not db_id:
        return False
    created_db_ids["logs"] = db_id

    return True


def add_sample_knowledge():
    """サンプルのナレッジを追加"""
    import requests
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    
    knowledge_db_id = created_db_ids.get("knowledge")
    if not knowledge_db_id:
        logger.error("運用ナレッジDBが作成されていません")
        return
    
    logger.info("\n📝 サンプルナレッジを追加中...")
    
    sample_knowledge = [
        {
            "title": "20%ルール（予算変更）",
            "category": "予算",
            "source": "通説",
            "importance": "高",
            "url": "https://note.com/juchida/n/n46234a38e018",
            "content": "予算を大きく変更すると学習がリセットされる可能性がある。予算変更は20%以内に抑えるのが推奨。急激に予算を上げたい場合はキャンペーンの複製を検討。",
        },
        {
            "title": "学習期間中は触らない",
            "category": "アルゴリズム",
            "source": "公式",
            "importance": "高",
            "url": None,
            "content": "Meta広告の学習期間（約7日間、50CV程度）は設定変更を控える。学習期間中の変更は学習リセットを招く。",
        },
        {
            "title": "CPAからの逆算でCPC/CVRを評価",
            "category": "入札",
            "source": "自社検証",
            "importance": "高",
            "url": None,
            "content": "CPA = CPC / CVR で計算。目標CPA達成のために必要なCPC・CVRの組み合わせを逆算し、現在の数値と比較して継続/停止を判断。",
        },
        {
            "title": "クリエイティブの訴求軸を分ける",
            "category": "クリエイティブ",
            "source": "通説",
            "importance": "中",
            "url": "https://note.com/juchida/n/n46234a38e018",
            "content": "同じ訴求のクリエイティブを並べても配信先が被る。価格訴求、機能訴求、情緒訴求、クチコミ訴求など、異なる切り口で作成することで異なる層にリーチできる。",
        },
    ]
    
    for item in sample_knowledge:
        properties = {
            "タイトル": {"title": [{"text": {"content": item["title"]}}]},
            "カテゴリ": {"select": {"name": item["category"]}},
            "ソース": {"select": {"name": item["source"]}},
            "重要度": {"select": {"name": item["importance"]}},
        }
        if item["url"]:
            properties["参照URL"] = {"url": item["url"]}
        
        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": item["content"]}}]
                }
            }
        ]
        
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json={
                "parent": {"database_id": knowledge_db_id},
                "properties": properties,
                "children": children,
            },
        )
        
        if response.status_code == 200:
            logger.info(f"  ✅ {item['title']}")
        else:
            logger.error(f"  ❌ {item['title']}: {response.text}")
    
    logger.info("\n✅ サンプルナレッジの追加完了")


def save_config():
    """作成したデータベースIDを設定ファイルに保存"""
    config_content = f'''# Notion データベース設定（自動生成）
NOTION_TOKEN = "{NOTION_TOKEN}"
NOTION_PROJECTS_DB_ID = "{created_db_ids.get('projects', '')}"
NOTION_KNOWLEDGE_DB_ID = "{created_db_ids.get('knowledge', '')}"
NOTION_LOGS_DB_ID = "{created_db_ids.get('logs', '')}"
'''
    
    with open("notion_config.py", "w") as f:
        f.write(config_content)
    
    logger.info("\n📄 notion_config.py に設定を保存しました")


def main():
    logger.info("=" * 50)
    logger.info("🚀 Notion データベース セットアップ")
    logger.info("=" * 50)
    
    # データベースの新規作成
    if not setup_databases():
        logger.error("\n❌ セットアップに失敗しました")
        sys.exit(1)
    
    # 設定を保存
    save_config()
    
    # サンプルナレッジの追加
    add_sample = input("\n📝 サンプルの運用ナレッジを追加しますか？ (y/n): ").strip().lower()
    if add_sample == "y":
        add_sample_knowledge()
    
    logger.info("\n" + "=" * 50)
    logger.info("🎉 セットアップ完了！")
    logger.info("=" * 50)
    logger.info("\nNotionで親ページを開くと、3つのデータベースが作成されています：")
    logger.info(f"  📊 案件管理")
    logger.info(f"  📚 運用ナレッジ")
    logger.info(f"  📝 運用ログ")
    logger.info(f"\n親ページ: https://www.notion.so/{PARENT_PAGE_ID.replace('-', '')}")


if __name__ == "__main__":
    main()


