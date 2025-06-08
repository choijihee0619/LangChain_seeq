"""
데이터베이스 작업 모듈
공통 CRUD 작업
MODIFIED 2024-12-20: 새로운 컬렉션 구조에 맞는 특화 메서드 추가
"""
from typing import Dict, List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.logger import get_logger
from bson import ObjectId
import hashlib

logger = get_logger(__name__)

class DatabaseOperations:
    """데이터베이스 작업 클래스"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def insert_one(
        self,
        collection_name: str,
        document: Dict
    ) -> str:
        """단일 문서 삽입"""
        try:
            # 타임스탬프 추가
            if "created_at" not in document:
                document["created_at"] = datetime.utcnow()
            
            collection = self.db[collection_name]
            result = await collection.insert_one(document)
            
            logger.info(f"{collection_name}에 문서 삽입: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"문서 삽입 실패: {e}")
            raise
    
    async def insert_many(
        self,
        collection_name: str,
        documents: List[Dict]
    ) -> List[str]:
        """다중 문서 삽입"""
        try:
            # 타임스탬프 추가
            for doc in documents:
                if "created_at" not in doc:
                    doc["created_at"] = datetime.utcnow()
            
            collection = self.db[collection_name]
            result = await collection.insert_many(documents)
            
            logger.info(f"{collection_name}에 {len(result.inserted_ids)}개 문서 삽입")
            return [str(id) for id in result.inserted_ids]
            
        except Exception as e:
            logger.error(f"다중 문서 삽입 실패: {e}")
            raise
    
    async def find_one(
        self,
        collection_name: str,
        filter_dict: Dict
    ) -> Optional[Dict]:
        """단일 문서 조회"""
        try:
            collection = self.db[collection_name]
            document = await collection.find_one(filter_dict)
            return document
            
        except Exception as e:
            logger.error(f"문서 조회 실패: {e}")
            raise
    
    async def find_many(
        self,
        collection_name: str,
        filter_dict: Dict,
        limit: Optional[int] = None,
        skip: Optional[int] = None
    ) -> List[Dict]:
        """다중 문서 조회"""
        try:
            collection = self.db[collection_name]
            cursor = collection.find(filter_dict)
            
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            
            documents = await cursor.to_list(None)
            return documents
            
        except Exception as e:
            logger.error(f"다중 문서 조회 실패: {e}")
            raise
    
    async def update_one(
        self,
        collection_name: str,
        filter_dict: Dict,
        update_dict: Dict
    ) -> bool:
        """단일 문서 업데이트"""
        try:
            # 업데이트 타임스탬프 추가
            update_dict["$set"] = update_dict.get("$set", {})
            update_dict["$set"]["updated_at"] = datetime.utcnow()
            
            collection = self.db[collection_name]
            result = await collection.update_one(filter_dict, update_dict)
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"문서 업데이트 실패: {e}")
            raise
    
    async def delete_one(
        self,
        collection_name: str,
        filter_dict: Dict
    ) -> bool:
        """단일 문서 삭제"""
        try:
            collection = self.db[collection_name]
            result = await collection.delete_one(filter_dict)
            
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"문서 삭제 실패: {e}")
            raise
    
    # === 새로운 특화 메서드들 ===
    
    async def create_folder(self, title: str, folder_type: str = "general", cover_image_url: Optional[str] = None) -> str:
        """폴더 생성"""
        try:
            folder_doc = {
                "title": title,
                "folder_type": folder_type,
                "created_at": datetime.utcnow(),
                "last_accessed_at": datetime.utcnow(),
                "cover_image_url": cover_image_url
            }
            
            folder_id = await self.insert_one("folders", folder_doc)
            logger.info(f"폴더 생성 완료: {title} ({folder_id})")
            return folder_id
            
        except Exception as e:
            logger.error(f"폴더 생성 실패: {e}")
            raise
    
    async def update_folder_access(self, folder_id: str) -> bool:
        """폴더 마지막 접근 시간 업데이트"""
        try:
            # ObjectId 유효성 검증
            if not folder_id or folder_id == "string" or len(folder_id) != 24:
                logger.warning(f"유효하지 않은 folder_id: {folder_id}")
                return False
            
            # ObjectId 변환 가능한지 확인
            try:
                obj_id = ObjectId(folder_id)
            except Exception:
                logger.warning(f"ObjectId 변환 실패: {folder_id}")
                return False
            
            return await self.update_one(
                "folders",
                {"_id": obj_id},
                {"$set": {"last_accessed_at": datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"폴더 접근 시간 업데이트 실패: {e}")
            return False
    
    async def save_summary_cache(
        self,
        summary: str,
        folder_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        summary_type: str = "brief"
    ) -> str:
        """요약 결과 캐싱"""
        try:
            # 캐시 키 생성
            cache_data = f"{folder_id}_{document_ids}_{summary_type}"
            cache_key = hashlib.md5(cache_data.encode()).hexdigest()
            
            summary_doc = {
                "cache_key": cache_key,
                "summary": summary,
                "folder_id": folder_id,
                "document_ids": document_ids or [],
                "summary_type": summary_type,
                "created_at": datetime.utcnow(),
                "last_accessed_at": datetime.utcnow()
            }
            
            # 기존 캐시가 있으면 업데이트, 없으면 생성
            existing = await self.find_one("summaries", {"cache_key": cache_key})
            if existing:
                await self.update_one(
                    "summaries",
                    {"cache_key": cache_key},
                    {"$set": {"last_accessed_at": datetime.utcnow()}}
                )
                return str(existing["_id"])
            else:
                return await self.insert_one("summaries", summary_doc)
                
        except Exception as e:
            logger.error(f"요약 캐시 저장 실패: {e}")
            raise
    
    async def get_summary_cache(
        self,
        folder_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        summary_type: str = "brief"
    ) -> Optional[Dict]:
        """요약 캐시 조회"""
        try:
            cache_data = f"{folder_id}_{document_ids}_{summary_type}"
            cache_key = hashlib.md5(cache_data.encode()).hexdigest()
            
            return await self.find_one("summaries", {"cache_key": cache_key})
            
        except Exception as e:
            logger.error(f"요약 캐시 조회 실패: {e}")
            return None
    
    async def save_quiz_results(
        self,
        quizzes: List[Dict],
        folder_id: Optional[str] = None,
        topic: Optional[str] = None,
        source_document_id: Optional[str] = None
    ) -> List[str]:
        """퀴즈 결과 저장"""
        try:
            quiz_docs = []
            for quiz in quizzes:
                quiz_doc = {
                    "folder_id": folder_id,
                    "source_document_id": source_document_id,
                    "topic": topic,
                    "question": quiz["question"],
                    "quiz_type": quiz.get("quiz_type", "multiple_choice"),
                    "quiz_options": quiz.get("options", []),
                    "correct_option": quiz.get("correct_option"),
                    "correct_answer": quiz.get("correct_answer"),
                    "difficulty": quiz.get("difficulty", "medium"),
                    "answer": quiz.get("explanation", ""),
                    "created_at": datetime.utcnow()
                }
                quiz_docs.append(quiz_doc)
            
            quiz_ids = await self.insert_many("qapairs", quiz_docs)
            logger.info(f"퀴즈 {len(quiz_ids)}개 저장 완료")
            return quiz_ids
            
        except Exception as e:
            logger.error(f"퀴즈 저장 실패: {e}")
            raise
    
    async def save_recommendation_cache(
        self,
        recommendations: List[Dict],
        keywords: List[str],
        content_types: List[str],
        folder_id: Optional[str] = None
    ) -> str:
        """추천 결과 캐싱"""
        try:
            # 캐시 키 생성
            cache_data = f"{folder_id}_{sorted(keywords)}_{sorted(content_types)}"
            cache_key = hashlib.md5(cache_data.encode()).hexdigest()
            
            rec_doc = {
                "cache_key": cache_key,
                "folder_id": folder_id,
                "keywords": keywords,
                "content_types": content_types,
                "recommendations": recommendations,
                "created_at": datetime.utcnow(),
                "last_accessed_at": datetime.utcnow()
            }
            
            # 기존 캐시가 있으면 업데이트, 없으면 생성
            existing = await self.find_one("recommendations", {"cache_key": cache_key})
            if existing:
                await self.update_one(
                    "recommendations",
                    {"cache_key": cache_key},
                    {"$set": {
                        "recommendations": recommendations,
                        "last_accessed_at": datetime.utcnow()
                    }}
                )
                return str(existing["_id"])
            else:
                return await self.insert_one("recommendations", rec_doc)
                
        except Exception as e:
            logger.error(f"추천 캐시 저장 실패: {e}")
            raise
    
    async def get_recommendation_cache(
        self,
        keywords: List[str],
        content_types: List[str],
        folder_id: Optional[str] = None
    ) -> Optional[Dict]:
        """추천 캐시 조회"""
        try:
            cache_data = f"{folder_id}_{sorted(keywords)}_{sorted(content_types)}"
            cache_key = hashlib.md5(cache_data.encode()).hexdigest()
            
            return await self.find_one("recommendations", {"cache_key": cache_key})
            
        except Exception as e:
            logger.error(f"추천 캐시 조회 실패: {e}")
            return None
    
    async def save_document_labels(
        self,
        document_id: str,
        folder_id: Optional[str],
        labels: Dict
    ) -> str:
        """문서 자동 라벨링 결과 저장"""
        try:
            label_doc = {
                "document_id": document_id,
                "folder_id": folder_id,
                "tags": labels.get("tags", []),
                "category": labels.get("category", "기타"),
                "keywords": labels.get("keywords", []),
                "confidence_score": labels.get("confidence_score", 0.0),
                "created_at": datetime.utcnow()
            }
            
            label_id = await self.insert_one("labels", label_doc)
            logger.info(f"문서 라벨링 저장 완료: {document_id}")
            return label_id
            
        except Exception as e:
            logger.error(f"문서 라벨링 저장 실패: {e}")
            raise
