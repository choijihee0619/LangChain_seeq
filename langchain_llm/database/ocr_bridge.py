"""
OCR 데이터베이스 브릿지
기존 OCR 데이터베이스(ocr_db.texts)와 RAG 시스템 간의 브릿지 역할
기존 데이터를 건드리지 않고 안전하게 통합 관리
CREATED 2024-12-20: OCR 데이터 안전 통합을 위한 브릿지 시스템
UPDATED 2025-06-04: 동기화 완료 후 불필요한 검색 메서드 제거, 핵심 동기화 기능만 유지
"""
from typing import Dict, List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
import os

from utils.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)

class OCRBridge:
    """OCR 데이터베이스 브릿지 클래스 - 동기화 전용"""
    
    def __init__(self, rag_db: AsyncIOMotorDatabase):
        self.rag_db = rag_db
        self.ocr_client = None
        self.ocr_db = None
        
    async def connect_ocr_db(self):
        """OCR 데이터베이스 연결"""
        try:
            # OCR 데이터베이스 연결 정보 (settings에서 가져오기)
            ocr_mongodb_uri = settings.OCR_MONGODB_URI or settings.MONGODB_URI
            ocr_db_name = settings.OCR_DB_NAME
            
            if not ocr_mongodb_uri:
                raise ValueError("OCR_MONGODB_URI 또는 MONGODB_URI가 설정되지 않음")
            
            self.ocr_client = AsyncIOMotorClient(ocr_mongodb_uri)
            self.ocr_db = self.ocr_client[ocr_db_name]
            
            # 연결 테스트
            await self.ocr_db.command("ping")
            logger.info(f"OCR 데이터베이스 연결 성공: {ocr_db_name}")
            
            # 텍스트 인덱스 확인 및 생성 시도
            await self.ensure_text_index()
            
        except Exception as e:
            logger.error(f"OCR 데이터베이스 연결 실패: {e}")
            # 연결에 실패해도 예외를 발생시키지 않고 None으로 설정
            self.ocr_client = None
            self.ocr_db = None
            # 대신 경고만 로그로 남김
            logger.warning("OCR 데이터베이스를 사용할 수 없습니다. OCR 기능이 제한됩니다.")
    
    async def ensure_text_index(self):
        """OCR 데이터베이스에 텍스트 인덱스가 있는지 확인하고 없으면 생성"""
        try:
            # 기존 인덱스 확인
            indexes = await self.ocr_db.texts.list_indexes().to_list(None)
            has_text_index = any("text" in str(index.get("key", {})) for index in indexes)
            
            if not has_text_index:
                logger.info("OCR 텍스트 인덱스가 없습니다. 생성을 시도합니다...")
                try:
                    # 텍스트 인덱스 생성 시도
                    await self.ocr_db.texts.create_index([("text", "text")])
                    logger.info("OCR 텍스트 인덱스 생성 완료")
                except Exception as index_error:
                    logger.warning(f"텍스트 인덱스 생성 실패 (권한 부족 가능): {index_error}")
                    logger.info("정규식 검색으로 대체됩니다.")
            else:
                logger.info("OCR 텍스트 인덱스가 이미 존재합니다.")
                
        except Exception as e:
            logger.warning(f"텍스트 인덱스 확인 실패: {e}")
            logger.info("정규식 검색으로 대체됩니다.")
    
    async def close_ocr_db(self):
        """OCR 데이터베이스 연결 종료"""
        if self.ocr_client:
            self.ocr_client.close()
            logger.info("OCR 데이터베이스 연결 종료")
    
    def convert_ocr_to_rag_format(self, ocr_doc: Dict, folder_id: str) -> Dict:
        """OCR 문서를 RAG 시스템 형식으로 변환"""
        try:
            # timestamp 처리
            if isinstance(ocr_doc.get("timestamp"), str):
                try:
                    timestamp_str = ocr_doc["timestamp"].replace('Z', '+00:00')
                    created_at = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    created_at = datetime.utcnow()
            else:
                created_at = ocr_doc.get("timestamp", datetime.utcnow())
            
            # ObjectId를 문자열로 변환
            doc_id = str(ocr_doc["_id"]) if ocr_doc.get("_id") else None
            
            return {
                "_id": doc_id,  # ObjectId를 문자열로 변환
                "folder_id": folder_id,
                "raw_text": ocr_doc["text"],
                "created_at": created_at,
                "file_metadata": {
                    "file_id": f"ocr_{doc_id}",
                    "original_filename": ocr_doc["image_path"],
                    "file_type": "ocr",
                    "file_size": None,
                    "description": "OCR로 추출된 텍스트"
                },
                "chunks_count": 0,
                "text_length": len(ocr_doc["text"]),
                "data_source": "ocr_bridge",  # 브릿지를 통한 데이터임을 표시
                "original_db": "ocr_db.texts"  # 원본 위치 정보
            }
            
        except Exception as e:
            logger.error(f"OCR 데이터 변환 실패: {e}")
            raise
    
    async def get_or_create_ocr_folder(self) -> str:
        """OCR 전용 폴더 조회 또는 생성"""
        try:
            # 기존 OCR 폴더 찾기
            ocr_folder = await self.rag_db.folders.find_one({"title": "OCR 텍스트"})
            
            if ocr_folder:
                return str(ocr_folder["_id"])
            
            # OCR 폴더 새로 생성
            folder_data = {
                "title": "OCR 텍스트",
                "folder_type": "ocr",
                "created_at": datetime.utcnow(),
                "last_accessed_at": datetime.utcnow(),
                "cover_image_url": None,
                "document_count": 0,
                "file_count": 0,
                "description": "OCR로 추출된 텍스트 문서들"
            }
            
            result = await self.rag_db.folders.insert_one(folder_data)
            folder_id = str(result.inserted_id)
            logger.info(f"OCR 폴더 생성: {folder_id}")
            return folder_id
            
        except Exception as e:
            logger.error(f"OCR 폴더 조회/생성 실패: {e}")
            raise
    
    async def get_ocr_stats(self) -> Dict:
        """OCR 데이터베이스 통계"""
        try:
            if self.ocr_db is None:
                await self.connect_ocr_db()
            
            total_count = await self.ocr_db.texts.count_documents({})
            
            # 최근 문서
            recent_doc = await self.ocr_db.texts.find_one(
                {}, 
                sort=[("timestamp", -1)]
            )
            
            # 텍스트 길이 통계 (안전한 방식으로 수정)
            pipeline = [
                {
                    "$match": {
                        "text": {"$exists": True, "$type": "string", "$ne": ""}
                    }
                },
                {
                    "$project": {
                        "text_length": {
                            "$cond": {
                                "if": {"$and": [
                                    {"$ne": ["$text", None]},
                                    {"$eq": [{"$type": "$text"}, "string"]}
                                ]},
                                "then": {"$strLenCP": "$text"},
                                "else": 0
                            }
                        },
                        "timestamp": 1
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "avg_length": {"$avg": "$text_length"},
                        "max_length": {"$max": "$text_length"},
                        "min_length": {"$min": "$text_length"}
                    }
                }
            ]
            
            stats_result = await self.ocr_db.texts.aggregate(pipeline).to_list(1)
            text_stats = stats_result[0] if stats_result else {}
            
            # last_updated를 문자열로 변환
            last_updated_str = None
            if recent_doc and recent_doc.get("timestamp"):
                timestamp = recent_doc["timestamp"]
                if isinstance(timestamp, datetime):
                    last_updated_str = timestamp.isoformat()
                elif isinstance(timestamp, str):
                    last_updated_str = timestamp
                else:
                    last_updated_str = str(timestamp)
            
            return {
                "total_documents": total_count,
                "last_updated": last_updated_str,
                "text_stats": {
                    "average_length": int(text_stats.get("avg_length", 0)),
                    "max_length": text_stats.get("max_length", 0),
                    "min_length": text_stats.get("min_length", 0)
                },
                "database_info": {
                    "source_db": "ocr_db.texts",
                    "integration_type": "bridge",
                    "data_preservation": "원본 데이터 보존됨",
                    "sync_status": "동기화 완료 - 일반 RAG 검색 사용 권장"
                }
            }
            
        except Exception as e:
            logger.error(f"OCR 통계 조회 실패: {e}")
            return {"error": str(e)}
    
    async def sync_new_ocr_data(self, since_timestamp: Optional[datetime] = None) -> Dict:
        """새로운 OCR 데이터만 RAG 시스템으로 동기화"""
        try:
            if self.ocr_db is None:
                await self.connect_ocr_db()
            
            # 동기화 시점 결정
            if not since_timestamp:
                # 마지막 동기화 시점 조회
                last_sync = await self.rag_db.system_sync.find_one(
                    {"sync_type": "ocr_bridge"}
                )
                since_timestamp = last_sync.get("last_sync_time") if last_sync and last_sync.get("last_sync_time") else datetime(2024, 1, 1)
            
            # 새로운 OCR 데이터 조회
            new_ocr_docs = await self.ocr_db.texts.find({
                "timestamp": {"$gt": since_timestamp}
            }).to_list(None)
            
            # 현재 시간 기록
            current_time = datetime.utcnow()
            
            if not new_ocr_docs:
                return {
                    "synced_count": 0, 
                    "total_new_data": 0,
                    "last_sync_time": current_time,
                    "message": "새로운 데이터 없음"
                }
            
            # RAG 시스템에 동기화
            folder_id = await self.get_or_create_ocr_folder()
            synced_count = 0
            
            for ocr_doc in new_ocr_docs:
                try:
                    # 이미 동기화된 문서인지 확인
                    existing = await self.rag_db.documents.find_one(
                        {"file_metadata.file_id": f"ocr_{ocr_doc['_id']}"}
                    )
                    
                    if not existing:
                        # RAG 형식으로 변환하여 저장
                        rag_doc = self.convert_ocr_to_rag_format(ocr_doc, folder_id)
                        await self.rag_db.documents.insert_one(rag_doc)
                        synced_count += 1
                        
                except Exception as e:
                    logger.warning(f"문서 동기화 실패 {ocr_doc['_id']}: {e}")
            
            # 동기화 시점 기록
            sync_record = {
                "sync_type": "ocr_bridge",
                "last_sync_time": current_time,
                "synced_count": synced_count,
                "total_ocr_count": len(new_ocr_docs)
            }
            
            # upsert 기능을 위해 직접 MongoDB 컬렉션 사용
            await self.rag_db.system_sync.update_one(
                {"sync_type": "ocr_bridge"},
                {"$set": sync_record},
                upsert=True
            )
            
            logger.info(f"OCR 데이터 동기화 완료: {synced_count}개")
            return {
                "synced_count": synced_count,
                "total_new_data": len(new_ocr_docs),
                "last_sync_time": current_time
            }
            
        except Exception as e:
            logger.error(f"OCR 데이터 동기화 실패: {e}")
            raise 