#!/usr/bin/env python3
"""
知識ベースセットアップスクリプト
Meta広告の知識をベクトルDBに格納
"""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("🧠 知識ベース セットアップ")
    logger.info("=" * 60)
    
    from knowledge_engine import KnowledgeBase
    
    kb = KnowledgeBase()
    
    # 知識ベースを初期化
    logger.info("\n📚 知識を収集・ベクトル化中...")
    results = kb.initialize_knowledge()
    
    logger.info("\n✅ 完了！")
    logger.info("\n📊 収集結果:")
    for collection, count in results.items():
        logger.info(f"  - {collection}: {count}件")
    
    # 統計を表示
    stats = kb.get_stats()
    logger.info("\n📈 知識ベース統計:")
    for collection, count in stats.items():
        logger.info(f"  - {collection}: {count}件")
    
    # テスト検索
    logger.info("\n🔍 テスト検索: 「予算を増やしたい」")
    results = kb.search_knowledge("予算を増やしたい", n_results=3)
    
    for i, r in enumerate(results, 1):
        title = r.get("metadata", {}).get("title", "無題")
        logger.info(f"  {i}. {title}")
    
    logger.info("\n" + "=" * 60)
    logger.info("🎉 セットアップ完了！")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()


