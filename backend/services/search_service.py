from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from pymilvus import connections, Collection, utility
import chromadb
from chromadb.config import Settings
from services.embedding_service import EmbeddingService
from utils.config import VectorDBProvider, MILVUS_CONFIG, CHROMA_CONFIG
import os
import json
from chromadb import PersistentClient

logger = logging.getLogger(__name__)

class SearchService:
    """
    搜索服务类，负责向量数据库的连接和向量搜索功能
    提供集合列表查询、向量相似度搜索和搜索结果保存等功能
    新增支持Chroma向量数据库，同时保持原有Milvus功能完整
    """
    def __init__(self):
        """
        初始化搜索服务
        创建嵌入服务实例，设置数据库连接URI，初始化搜索结果保存目录
        新增Chroma客户端初始化
        """
        self.embedding_service = EmbeddingService()
        self.milvus_uri = MILVUS_CONFIG["uri"]
        self.search_results_dir = "04-search-results"
        os.makedirs(self.search_results_dir, exist_ok=True)
        
        # 初始化 Chroma 客户端，使用 CHROMA_CONFIG 中的 uri
        try:
            self.chroma_client = PersistentClient(path=CHROMA_CONFIG["uri"])
            logger.info("Chroma client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chroma: {e}")
            self.chroma_client = None

    def get_providers(self) -> List[Dict[str, str]]:
        """
        获取支持的向量数据库列表
        新增Chroma支持，同时保持原有Milvus返回格式
        
        Returns:
            List[Dict[str, str]]: 支持的向量数据库提供商列表
            [{"id": "milvus", "name": "Milvus"}, {"id": "chroma", "name": "Chroma"}]
        """
        providers = [{"id": VectorDBProvider.MILVUS.value, "name": "Milvus"}]
        
        # 仅在 Chroma 可用时添加
        if self._check_chroma_available():
            providers.append({"id": VectorDBProvider.CHROMA.value, "name": "Chroma"})
        
        logger.info(f"Available providers: {[p['name'] for p in providers]}")
        return providers

    def _check_chroma_available(self) -> bool:
        """检查 Chroma 是否可用"""
        if not self.chroma_client:
            return False
        try:
            _ = self.chroma_client.list_collections()
            return True
        except Exception as e:
            logger.warning(f"Chroma health check failed: {str(e)}")
            return False

    def list_collections(self, provider: str = VectorDBProvider.MILVUS.value) -> List[Dict[str, Any]]:
        """
        获取指定向量数据库中的所有集合
        新增Chroma集合查询支持，同时保持原有Milvus查询逻辑和返回格式
        
        Args:
            provider (str): 向量数据库提供商，默认为Milvus
            
        Returns:
            List[Dict[str, Any]]: 集合信息列表，包含id、名称和实体数量
            [{"id": "collection1", "name": "collection1", "count": 1000}]
            
        Raises:
            Exception: 连接或查询集合时发生错误
        """
        try:
            logger.info(f"Listing collections for provider: {provider}")
            
            if provider == VectorDBProvider.MILVUS.value:
                # 保持原有Milvus查询逻辑
                logger.debug("Connecting to Milvus...")
                connections.connect(alias="default", uri=self.milvus_uri)
                
                collections = []
                collection_names = utility.list_collections()
                logger.debug(f"Found {len(collection_names)} collections in Milvus")
                
                for name in collection_names:
                    try:
                        logger.debug(f"Getting info for collection: {name}")
                        collection = Collection(name)
                        collections.append({
                            "id": name,
                            "name": name,
                            "count": collection.num_entities
                        })
                        logger.debug(f"Collection {name} has {collection.num_entities} entities")
                    except Exception as e:
                        logger.error(f"Error getting info for collection {name}: {str(e)}")
                        raise
                
                return collections
            
            elif provider == VectorDBProvider.CHROMA.value:
                # 新增Chroma集合查询（保持返回格式一致）
                logger.debug("Querying Chroma collections...")
                chroma_collections = self.chroma_client.list_collections()
                collections = []
                
                for col in chroma_collections:
                    try:
                        logger.debug(f"Processing Chroma collection: {col.name}")
                        collections.append({
                            "id": col.name,
                            "name": col.name,
                            "count": col.count()
                        })
                        logger.debug(f"Collection {col.name} has {col.count()} entities")
                    except Exception as e:
                        logger.error(f"Error processing Chroma collection {col.name}: {str(e)}")
                        raise
                
                return collections
            
            else:
                error_msg = f"Unsupported provider: {provider}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
        except Exception as e:
            logger.error(f"Error listing collections: {str(e)}")
            raise
        finally:
            if provider == VectorDBProvider.MILVUS.value:
                logger.debug("Disconnecting from Milvus")
                connections.disconnect("default")

    def save_search_results(self, query: str, collection_id: str, results: List[Dict[str, Any]]) -> str:
        """
        保存搜索结果到JSON文件
        
        Args:
            query (str): 搜索查询文本
            collection_id (str): 集合ID
            results (List[Dict[str, Any]]): 搜索结果列表
            
        Returns:
            str: 保存文件的路径
            
        Raises:
            Exception: 保存文件时发生错误
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            # 使用集合ID的基础名称（去掉路径相关字符）
            collection_base = os.path.basename(collection_id)
            filename = f"search_{collection_base}_{timestamp}.json"
            filepath = os.path.join(self.search_results_dir, filename)
            
            logger.info(f"Saving {len(results)} results to {filepath}")
            logger.debug(f"Sample result: {results[0] if results else 'Empty'}")
            
            search_data = {
                "query": query,
                "collection_id": collection_id,
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            
            logger.info(f"Saving search results to: {filepath}")
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(search_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Successfully saved search results to: {filepath}")
            logger.debug(f"File size: {os.path.getsize(filepath)/1024:.2f} KB")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving search results: {str(e)}")
            raise

    async def search(self, 
                    query: str, 
                    collection_id: str, 
                    provider: str = VectorDBProvider.MILVUS.value,
                    top_k: int = 3, 
                    threshold: float = 0.7,
                    word_count_threshold: int = 20,
                    save_results: bool = False) -> Dict[str, Any]:
        """
        执行向量搜索（保持原有Milvus逻辑，新增Chroma支持）
        
        Args:
            query (str): 搜索查询文本
            collection_id (str): 要搜索的集合ID
            provider (str): 向量数据库提供商，默认为Milvus
            top_k (int): 返回的最大结果数量，默认为3
            threshold (float): 相似度阈值，低于此值的结果将被过滤，默认为0.7
            word_count_threshold (int): 文本字数阈值，低于此值的结果将被过滤（仅Milvus有效），默认为20
            save_results (bool): 是否保存搜索结果，默认为False
            
        Returns:
            Dict[str, Any]: 包含搜索结果的字典，格式与原有Milvus返回一致
            {
                "results": [
                    {
                        "text": "结果文本",
                        "score": 相似度分数,
                        "metadata": {
                            "page": 页码,
                            "chunk": 块ID
                        }
                    }
                ],
                "saved_filepath": "保存路径" (如果save_results为True)
            }
            
        Raises:
            Exception: 搜索过程中发生错误
        """
        try:
            logger.info(f"Starting search with parameters - Provider: {provider}, Collection: {collection_id}, "
                       f"Query: {query}, Top K: {top_k}, Threshold: {threshold}")
            
            if provider == VectorDBProvider.MILVUS.value:
                # 保持原有Milvus搜索逻辑
                return await self._search_milvus(
                    query, collection_id, top_k, threshold, word_count_threshold, save_results
                )
            elif provider == VectorDBProvider.CHROMA.value:
                # 新增Chroma搜索逻辑（保持返回格式一致）
                return await self._search_chroma(
                    query, collection_id, top_k, threshold, save_results
                )
            else:
                error_msg = f"Unsupported provider: {provider}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise

    async def _search_milvus(self, 
                           query: str, 
                           collection_id: str, 
                           top_k: int, 
                           threshold: float,
                           word_count_threshold: int,
                           save_results: bool) -> Dict[str, Any]:
        """
        执行向量搜索（保持原有Milvus搜索逻辑不变）
        
        Args:
            query (str): 搜索查询文本
            collection_id (str): 要搜索的集合ID
            top_k (int): 返回的最大结果数量，默认为3
            threshold (float): 相似度阈值，低于此值的结果将被过滤，默认为0.7
            word_count_threshold (int): 文本字数阈值，低于此值的结果将被过滤，默认为20
            save_results (bool): 是否保存搜索结果，默认为False
            
        Returns:
            Dict[str, Any]: 包含搜索结果的字典，如果保存结果则包含保存路径
            
        Raises:
            Exception: 搜索过程中发生错误
        """
        try:
            # 添加参数日志
            logger.info(f"Search parameters:")
            logger.info(f"- Query: {query}")
            logger.info(f"- Collection ID: {collection_id}")
            logger.info(f"- Top K: {top_k}")
            logger.info(f"- Threshold: {threshold}")
            logger.info(f"- Word Count Threshold: {word_count_threshold}")
            logger.info(f"- Save Results: {save_results} (type: {type(save_results)})")

            logger.info(f"Starting search with parameters - Collection: {collection_id}, Query: {query}, Top K: {top_k}")
            
            # 连接Milvus
            logger.info(f"Connecting to Milvus at {self.milvus_uri}")
            connections.connect(
                alias="default",
                uri=self.milvus_uri
            )
            logger.debug("Milvus connection established")
            
            # 获取collection
            logger.info(f"Loading collection: {collection_id}")
            collection = Collection(collection_id)
            collection.load()

            # 记录collection的基本信息
            logger.info(f"Collection info - Entities: {collection.num_entities}")
            
            # 从collection中读取embedding配置
            logger.info("Querying sample entity for embedding configuration")
            sample_entity = collection.query(
                expr="id >= 0", 
                output_fields=["embedding_provider", "embedding_model"],
                limit=1
            )
            if not sample_entity:
                logger.error(f"Collection {collection_id} is empty")
                raise ValueError(f"Collection {collection_id} is empty")
            
            logger.info(f"Sample entity configuration: {sample_entity[0]}")
            
            # 使用collection中存储的配置创建查询向量
            logger.info("Creating query embedding")
            start_time = datetime.now()
            query_embedding = self.embedding_service.create_single_embedding(
                query,
                provider=sample_entity[0]["embedding_provider"],
                model=sample_entity[0]["embedding_model"]
            )
            logger.info(f"Embedding created in {(datetime.now()-start_time).total_seconds():.2f}s. Dimension: {len(query_embedding)}")

            # 准备搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            logger.info(f"Executing search with params: {search_params}")
            logger.info(f"Word count threshold filter: word_count >= {word_count_threshold}")

            # 执行搜索
            logger.info(f"Executing search with top_k={top_k}, threshold={threshold}")
            start_time = datetime.now()
            results = collection.search(
                data=[query_embedding],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=f"word_count >= {word_count_threshold}",
                output_fields=[
                    "content",
                    "document_name",
                    "chunk_id",
                    "total_chunks",
                    "word_count",
                    "page_number",
                    "page_range",
                    "embedding_provider",
                    "embedding_model",
                    "embedding_timestamp"
                ]
                # output_fields=["content", "page_number", "chunk_id"]
            )
            logger.info(f"Search completed in {(datetime.now()-start_time).total_seconds():.2f}s. Found {len(results[0])} raw results")

            # 处理结果
            processed_results = []
            logger.info(f"Raw search results count: {len(results[0])}")

            for hits in results:
                for hit in hits:
                    logger.info(f"Processing hit - Score: {hit.score}, Word Count: {hit.entity.get('word_count')}")
                    if hit.score >= threshold:
                        result = {
                            "text": hit.entity.content,
                            "score": float(hit.score),
                            "metadata": {
                                "source": hit.entity.document_name,
                                "page": hit.entity.page_number,
                                "chunk": hit.entity.chunk_id,
                                "total_chunks": hit.entity.total_chunks,
                                "page_range": hit.entity.page_range,
                                "embedding_provider": hit.entity.embedding_provider,
                                "embedding_model": hit.entity.embedding_model,
                                "embedding_timestamp": hit.entity.embedding_timestamp
                            }
                        }
                        processed_results.append(result)
                        logger.debug(f"Added result - Score: {hit.score:.4f}, Page: {hit.entity.page_number}")

            logger.info(f"Filtered results count: {len(processed_results)} (after threshold {threshold})")
            response_data = {"results": processed_results}

            # 添加详细的保存逻辑日志
            logger.info(f"Preparing to handle save_results (flag: {save_results})")
            logger.info(f"Processed results count: {len(processed_results)}")
            logger.info(f"Sample result: {processed_results[0] if processed_results else 'Empty'}")

            # 保存结果
            if save_results:
                logger.info("Save results is True, attempting to save...")
                if processed_results:
                    try:
                        filepath = self.save_search_results(query, collection_id, processed_results)
                        logger.info(f"Successfully saved results to: {filepath}")
                        response_data["saved_filepath"] = filepath
                    except Exception as e:
                        logger.error(f"Error saving results: {str(e)}")
                        response_data["save_error"] = str(e)
                        raise  # 添加这行来查看完整的错误堆栈
                else:
                    logger.info("No results to save")
            else:
                logger.info("Save results is False, skipping save")

            return response_data

        except Exception as e:
            logger.error(f"Error performing search: {str(e)}")
            raise
        finally:
            logger.debug("Disconnecting from Milvus")
            try:
                connections.disconnect("default")
            except Exception as e:
                logger.warning(f"Error disconnecting from Milvus: {str(e)}")

    async def _search_chroma(self, query: str, collection_id: str, top_k: int, threshold: float, save_results: bool) -> Dict[str, Any]:
        if not self.chroma_client:
            logger.error("Chroma client not initialized")
            raise ValueError("Chroma service unavailable")

        try:
            # 1. 获取集合
            collection = self.chroma_client.get_collection(collection_id)
            
            # 2. 从集合元数据中读取嵌入模型配置（假设索引时已存储）
            metadata = collection.metadata or {}
            
            # 强制从元数据读取配置（不设默认值，避免意外回退）
            embedding_provider = metadata["embedding_provider"]  # 必须存在
            embedding_model = metadata["embedding_model"]        # 必须存在

            query_embedding = self.embedding_service.create_single_embedding(
                query, 
                provider=embedding_provider,  # 使用集合配置的provider
                model=embedding_model
            )

            # 4. 执行搜索
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["metadatas", "documents", "distances"]
            )

            # 处理结果
            processed_results = []
            for i in range(len(results["ids"][0])):
                similarity = 1 - results["distances"][0][i]  # 距离转相似度
                if similarity >= threshold:
                    processed_results.append({
                        "text": results["metadatas"][0][i].get("content"),  # 从metadata提取内容
                        "score": float(similarity),
                        "metadata": {
                            "source": collection_id,
                            "page": results["metadatas"][0][i].get("page_number"),
                            "chunk": results["metadatas"][0][i].get("chunk_id")
                        }
                    })

            return {"results": processed_results}  # 移除多余嵌套层

        except Exception as e:
            logger.error(f"Chroma search error: {str(e)}")
            raise

    async def index_data(self, collection_name: str, embeddings: List[List[float]]):
        if not self.chroma_client:
            raise ValueError("Chroma client not initialized")

        try:
            collection = self.chroma_client.get_or_create_collection(collection_name)
            collection.add(
                embeddings=embeddings,
                ids=[str(i) for i in range(len(embeddings))]  # 确保每个嵌入有唯一ID
            )
            logger.info(f"Data indexed to collection '{collection_name}'")
            return {"status": "success", "collection": collection_name}
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            raise

    async def search_data(self, collection_name: str, query_embedding: List[float], top_k: int):
        if not self.chroma_client:
            raise ValueError("Chroma client not initialized")

        try:
            collection = self.chroma_client.get_collection(collection_name)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise 