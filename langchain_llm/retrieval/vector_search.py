"""
벡터 검색 모듈
MongoDB 벡터 검색 기능 - 청크 기반 검색
MODIFIED 2024-12-19: 청크 기반 검색으로 업데이트
"""
from typing import List, Dict, Optional
import numpy as np
from motor.motor_asyncio import AsyncIOMotorDatabase
from data_processing.embedder import TextEmbedder
from utils.logger import get_logger

logger = get_logger(__name__)

class VectorSearch:
    """벡터 검색 클래스"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.embedder = TextEmbedder()
        self.chunks_collection = db.chunks
        self.documents_collection = db.documents
    
    async def create_vector_index(self):
        """벡터 검색 인덱스 생성"""
        try:
            # MongoDB Atlas Search 인덱스 생성
            # 실제 환경에서는 Atlas UI 또는 별도 스크립트로 생성
            await self.chunks_collection.create_index([("text_embedding", "2dsphere")])
            await self.chunks_collection.create_index([("file_id", 1)])
            await self.chunks_collection.create_index([("document_id", 1)])
            logger.info("벡터 인덱스 생성 완료")
        except Exception as e:
            logger.error(f"벡터 인덱스 생성 실패: {e}")
    
    async def search_similar(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """유사도 기반 청크 검색"""
        try:
            # 쿼리 임베딩
            query_embedding = await self.embedder.embed_text(query)
            
            # MongoDB 집계 파이프라인으로 필터링된 청크 조회
            pipeline = []
            
            # 필터 적용 (file_id 또는 folder_id 기반)
            match_stage = {}
            if filter_dict:
                if "folder_id" in filter_dict:
                    # folder_id로 필터링하는 경우 documents 컬렉션과 조인 필요 (새로운 구조에 맞게 수정)
                    pipeline.extend([
                        {
                            "$lookup": {
                                "from": "documents",
                                "localField": "file_id",
                                "foreignField": "file_metadata.file_id",
                                "as": "document_info"
                            }
                        },
                        {
                            "$match": {
                                "document_info.folder_id": filter_dict["folder_id"]
                            }
                        }
                    ])
                else:
                    match_stage.update(filter_dict)
            
            if match_stage:
                pipeline.insert(0, {"$match": match_stage})
            
            # 청크 조회
            chunks = []
            if pipeline:
                cursor = self.chunks_collection.aggregate(pipeline)
                async for chunk in cursor:
                    chunks.append(chunk)
            else:
                cursor = self.chunks_collection.find({})
                async for chunk in cursor:
                    chunks.append(chunk)
            
            # 각 청크에 대해 유사도 계산
            scored_chunks = []
            for chunk in chunks:
                if "text_embedding" in chunk:
                    similarity = self._cosine_similarity(
                        query_embedding,
                        chunk["text_embedding"]
                    )
                    scored_chunks.append({
                        "chunk": chunk,
                        "score": similarity,
                        "document_id": chunk.get("document_id"),
                        "file_id": chunk.get("file_id")
                    })
            
            # 유사도 순으로 정렬
            scored_chunks.sort(key=lambda x: x["score"], reverse=True)
            
            # 상위 k개 반환
            top_chunks = scored_chunks[:k]
            
            # 결과 포맷팅 - 문서 정보 추가
            results = []
            for item in top_chunks:
                chunk = item["chunk"]
                
                # 문서 정보 조회 (새로운 구조에 맞게 수정)
                document = await self.documents_collection.find_one(
                    {"file_metadata.file_id": chunk["file_id"]}
                )
                
                # document가 없으면 기본값 설정
                if not document:
                    document = {
                        "file_metadata": {
                            "original_filename": "알 수 없는 파일",
                            "file_type": "unknown",
                            "file_size": 0
                        }
                    }
                
                # 새로운 구조에 맞게 document 정보 정리
                document_info = document.get("file_metadata", {}) if document else {}
                
                results.append({
                    "chunk": chunk,
                    "document": {
                        "original_filename": document_info.get("original_filename", "알 수 없는 파일"),
                        "file_type": document_info.get("file_type", "unknown"),
                        "file_size": document_info.get("file_size", 0),
                        "description": document_info.get("description"),
                        "upload_time": document.get("created_at") if document else None,
                        "folder_id": document.get("folder_id") if document else None
                    },
                    "score": item["score"],
                    "chunk_id": chunk.get("chunk_id"),
                    "sequence": chunk.get("sequence", 0)
                })
            
            logger.info(f"벡터 검색 완료: {len(results)}개 청크 반환")
            return results
            
        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}")
            raise
    
    async def search_by_file(
        self,
        query: str,
        file_id: str,
        k: int = 5
    ) -> List[Dict]:
        """특정 파일 내에서만 검색"""
        filter_dict = {"file_id": file_id}
        return await self.search_similar(query, k, filter_dict)
    
    async def get_similar_chunks(
        self,
        chunk_id: str,
        k: int = 5,
        same_document_only: bool = False
    ) -> List[Dict]:
        """특정 청크와 유사한 청크들 검색"""
        try:
            # 기준 청크 조회
            base_chunk = await self.chunks_collection.find_one({"chunk_id": chunk_id})
            if not base_chunk or "text_embedding" not in base_chunk:
                return []
            
            # 필터 조건
            filter_dict = {}
            if same_document_only:
                filter_dict["file_id"] = base_chunk["file_id"]
            
            # 기준 청크 제외
            filter_dict["chunk_id"] = {"$ne": chunk_id}
            
            # 모든 후보 청크 조회
            chunks = []
            cursor = self.chunks_collection.find(filter_dict)
            async for chunk in cursor:
                if "text_embedding" in chunk:
                    similarity = self._cosine_similarity(
                        base_chunk["text_embedding"],
                        chunk["text_embedding"]
                    )
                    chunks.append({
                        "chunk": chunk,
                        "score": similarity
                    })
            
            # 유사도 순 정렬 및 상위 k개 반환
            chunks.sort(key=lambda x: x["score"], reverse=True)
            return chunks[:k]
            
        except Exception as e:
            logger.error(f"유사 청크 검색 실패: {e}")
            raise
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
            
        except Exception as e:
            logger.error(f"코사인 유사도 계산 실패: {e}")
            return 0.0
