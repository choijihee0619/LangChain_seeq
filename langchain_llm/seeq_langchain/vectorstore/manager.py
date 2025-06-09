"""
MongoDB VectorStore 관리자
기존 chunks 컬렉션을 LangChain VectorStore로 활용
"""
from typing import List, Dict, Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class VectorStoreManager:
    """MongoDB VectorStore 관리자"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        self._vectorstore = None
        self._retriever = None
    
    @property
    def vectorstore(self) -> MongoDBAtlasVectorSearch:
        """VectorStore 인스턴스 반환"""
        if self._vectorstore is None:
            self._vectorstore = MongoDBAtlasVectorSearch(
                collection=self.db.chunks,
                embedding=self.embeddings,
                index_name="vector_index",
                text_key="text",
                embedding_key="text_embedding"
            )
        return self._vectorstore
    
    @property 
    def retriever(self) -> VectorStoreRetriever:
        """Retriever 인스턴스 반환"""
        if self._retriever is None:
            self._retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": settings.DEFAULT_TOP_K}
            )
        return self._retriever
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """유사도 검색"""
        try:
            logger.info(f"벡터 검색 시작: '{query}', k={k}")
            
            # 필터 조건 설정
            search_kwargs = {"k": k}
            if filter_dict:
                # folder_id 필터 지원
                if "folder_id" in filter_dict:
                    search_kwargs["filter"] = {"metadata.folder_id": filter_dict["folder_id"]}
                else:
                    search_kwargs["filter"] = filter_dict
            
            # LangChain VectorStore 검색
            documents = await self.vectorstore.asimilarity_search(
                query, **search_kwargs
            )
            
            logger.info(f"벡터 검색 완료: {len(documents)}개 문서 반환")
            return documents
            
        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}")
            # fallback: 기존 방식 사용
            return await self._fallback_search(query, k, filter_dict)
    
    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[tuple[Document, float]]:
        """점수와 함께 유사도 검색"""
        try:
            search_kwargs = {"k": k}
            if filter_dict:
                if "folder_id" in filter_dict:
                    search_kwargs["filter"] = {"metadata.folder_id": filter_dict["folder_id"]}
                else:
                    search_kwargs["filter"] = filter_dict
            
            results = await self.vectorstore.asimilarity_search_with_score(
                query, **search_kwargs
            )
            
            logger.info(f"점수 포함 벡터 검색 완료: {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"점수 포함 벡터 검색 실패: {e}")
            # fallback: 점수 없이 문서만 반환
            documents = await self.similarity_search(query, k, filter_dict)
            return [(doc, 0.8) for doc in documents]  # 기본 점수 0.8
    
    async def get_retriever_with_filter(
        self,
        folder_id: Optional[str] = None,
        file_id: Optional[str] = None,
        k: int = 5
    ) -> VectorStoreRetriever:
        """필터가 적용된 Retriever 반환"""
        search_kwargs = {"k": k}
        
        if folder_id:
            search_kwargs["filter"] = {"metadata.folder_id": folder_id}
        elif file_id:
            search_kwargs["filter"] = {"file_id": file_id}
        
        return self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs=search_kwargs
        )
    
    async def add_documents(
        self,
        documents: List[Document],
        **kwargs
    ) -> List[str]:
        """문서 추가"""
        try:
            ids = await self.vectorstore.aadd_documents(documents, **kwargs)
            logger.info(f"벡터스토어에 {len(documents)}개 문서 추가 완료")
            return ids
        except Exception as e:
            logger.error(f"문서 추가 실패: {e}")
            raise
    
    async def delete_documents(self, ids: List[str]) -> bool:
        """문서 삭제"""
        try:
            result = await self.vectorstore.adelete(ids)
            logger.info(f"벡터스토어에서 {len(ids)}개 문서 삭제 완료")
            return result
        except Exception as e:
            logger.error(f"문서 삭제 실패: {e}")
            return False
    
    async def _fallback_search(
        self,
        query: str,
        k: int,
        filter_dict: Optional[Dict]
    ) -> List[Document]:
        """기존 검색 방식으로 fallback"""
        try:
            # 기존 vector_search 모듈 사용
            from retrieval.vector_search import VectorSearch
            
            legacy_search = VectorSearch(self.db)
            results = await legacy_search.search_similar(query, k, filter_dict)
            
            # LangChain Document 형식으로 변환
            documents = []
            for result in results:
                chunk = result.get("chunk", {})
                document = result.get("document", {})
                
                doc = Document(
                    page_content=chunk.get("text", ""),
                    metadata={
                        "chunk_id": chunk.get("chunk_id"),
                        "file_id": chunk.get("file_id"),
                        "folder_id": chunk.get("metadata", {}).get("folder_id"),
                        "sequence": chunk.get("sequence", 0),
                        "score": result.get("score", 0.0),
                        "source": document.get("original_filename", ""),
                        "file_type": document.get("file_type", "")
                    }
                )
                documents.append(doc)
            
            logger.info(f"Fallback 검색 완료: {len(documents)}개 문서")
            return documents
            
        except Exception as e:
            logger.error(f"Fallback 검색도 실패: {e}")
            return []
    
    async def create_vector_index(self):
        """벡터 인덱스 생성 (Atlas Search)"""
        try:
            # MongoDB Atlas Search 인덱스 정의
            index_definition = {
                "fields": [
                    {
                        "numDimensions": 1536,  # text-embedding-3-large
                        "path": "text_embedding",
                        "similarity": "cosine",
                        "type": "vector"
                    },
                    {
                        "path": "metadata.folder_id",
                        "type": "filter"
                    },
                    {
                        "path": "file_id", 
                        "type": "filter"
                    }
                ]
            }
            
            logger.info("벡터 인덱스 생성 필요 - Atlas UI에서 수동 생성 권장")
            logger.info(f"인덱스 정의: {index_definition}")
            
        except Exception as e:
            logger.error(f"벡터 인덱스 생성 실패: {e}")
    
    def get_embedding_dimension(self) -> int:
        """임베딩 차원 수 반환"""
        if settings.OPENAI_EMBEDDING_MODEL == "text-embedding-3-large":
            return 1536
        elif settings.OPENAI_EMBEDDING_MODEL == "text-embedding-3-small":
            return 1536
        else:
            return 1536  # 기본값 