"""
ベクトルストア - ChromaDBラッパー
"""
import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDBを使用したベクトルストア"""

    def __init__(self, persist_directory: str = None):
        """
        初期化
        
        Args:
            persist_directory: データ永続化ディレクトリ
        """
        if persist_directory is None:
            persist_directory = str(Path(__file__).parent.parent / "storage" / "chromadb")
        
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        
        # コレクションを初期化
        self.collections = {}
        self._init_collections()
        
        logger.info(f"VectorStore初期化完了: {persist_directory}")

    def _init_collections(self):
        """コレクションを初期化"""
        collection_names = [
            "meta_official_docs",      # Meta公式ドキュメント
            "industry_knowledge",      # 業界知見（note, Reddit等）
            "operation_tips",          # 運用Tips
            "performance_patterns",    # パフォーマンスパターン
            "case_studies",            # 成功/失敗事例
        ]
        
        for name in collection_names:
            self.collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"description": f"{name} collection"},
            )

    def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        metadatas: list[dict] = None,
        ids: list[str] = None,
    ) -> bool:
        """
        ドキュメントを追加
        
        Args:
            collection_name: コレクション名
            documents: ドキュメントテキストのリスト
            metadatas: メタデータのリスト
            ids: ドキュメントIDのリスト
        
        Returns:
            bool: 成功したかどうか
        """
        if collection_name not in self.collections:
            logger.error(f"コレクション {collection_name} が存在しません")
            return False
        
        collection = self.collections[collection_name]
        
        # IDが指定されていない場合は自動生成
        if ids is None:
            import hashlib
            ids = [hashlib.md5(doc.encode()).hexdigest()[:16] for doc in documents]
        
        # メタデータがない場合は空のdictを使用
        if metadatas is None:
            metadatas = [{} for _ in documents]
        
        try:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            logger.info(f"{len(documents)}件のドキュメントを {collection_name} に追加")
            return True
        except Exception as e:
            logger.error(f"ドキュメント追加エラー: {e}")
            return False

    def search(
        self,
        collection_name: str,
        query: str,
        n_results: int = 5,
        where: dict = None,
    ) -> list[dict[str, Any]]:
        """
        類似ドキュメントを検索
        
        Args:
            collection_name: コレクション名
            query: 検索クエリ
            n_results: 取得件数
            where: フィルタ条件
        
        Returns:
            list[dict]: 検索結果
        """
        if collection_name not in self.collections:
            logger.error(f"コレクション {collection_name} が存在しません")
            return []
        
        collection = self.collections[collection_name]
        
        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
            )
            
            # 結果を整形
            formatted = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    formatted.append({
                        "document": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "id": results["ids"][0][i] if results["ids"] else None,
                        "distance": results["distances"][0][i] if results.get("distances") else None,
                    })
            
            return formatted
        except Exception as e:
            logger.error(f"検索エラー: {e}")
            return []

    def search_all(
        self,
        query: str,
        n_results_per_collection: int = 3,
    ) -> dict[str, list[dict]]:
        """
        全コレクションから検索
        
        Args:
            query: 検索クエリ
            n_results_per_collection: コレクションあたりの取得件数
        
        Returns:
            dict: コレクション名をキーとした検索結果
        """
        results = {}
        for name in self.collections:
            results[name] = self.search(name, query, n_results_per_collection)
        return results

    def add_document(
        self,
        collection_name: str,
        document: str,
        metadata: dict = None,
        doc_id: str = None,
    ) -> bool:
        """
        単一ドキュメントを追加
        
        Args:
            collection_name: コレクション名
            document: ドキュメントテキスト
            metadata: メタデータ
            doc_id: ドキュメントID
        
        Returns:
            bool: 成功したかどうか
        """
        if doc_id is None:
            import hashlib
            doc_id = hashlib.md5(document.encode()).hexdigest()[:16]
        
        return self.add_documents(
            collection_name,
            [document],
            [metadata] if metadata else None,
            [doc_id],
        )

    def get_all(
        self,
        collection_name: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        コレクションの全ドキュメントを取得
        
        Args:
            collection_name: コレクション名
            limit: 最大取得件数
        
        Returns:
            list[dict]: ドキュメントリスト
        """
        if collection_name not in self.collections:
            logger.error(f"コレクション {collection_name} が存在しません")
            return []
        
        collection = self.collections[collection_name]
        
        try:
            results = collection.get(limit=limit)
            
            formatted = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"]):
                    formatted.append({
                        "document": doc,
                        "metadata": results["metadatas"][i] if results.get("metadatas") else {},
                        "id": results["ids"][i] if results.get("ids") else None,
                    })
            
            return formatted
        except Exception as e:
            logger.error(f"取得エラー: {e}")
            return []

    def get_collection_stats(self) -> dict[str, int]:
        """各コレクションのドキュメント数を取得"""
        stats = {}
        for name, collection in self.collections.items():
            stats[name] = collection.count()
        return stats

    def delete_collection(self, collection_name: str) -> bool:
        """コレクションを削除"""
        try:
            self.client.delete_collection(collection_name)
            if collection_name in self.collections:
                del self.collections[collection_name]
            logger.info(f"コレクション {collection_name} を削除しました")
            return True
        except Exception as e:
            logger.error(f"コレクション削除エラー: {e}")
            return False


