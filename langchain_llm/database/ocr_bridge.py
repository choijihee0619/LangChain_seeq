"""
OCR 데이터베이스 브릿지
기존 OCR 데이터베이스(ocr_db.texts)와 RAG 시스템 간의 브릿지 역할
기존 데이터를 건드리지 않고 안전하게 통합 관리
CREATED 2024-12-20: OCR 데이터 안전 통합을 위한 브릿지 시스템
UPDATED 2025-06-04: 동기화 완료 후 불필요한 검색 메서드 제거, 핵심 동기화 기능만 유지
ENHANCED 2025-06-10: title별 폴더 자동 생성 및 페이지 구조화 처리
"""
from typing import Dict, List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
import os

from utils.logger import get_logger
from config.settings import settings

# 청킹과 임베딩을 위한 추가 import
from data_processing.chunker import TextChunker
from data_processing.embedder import TextEmbedder
from data_processing.preprocessor import TextPreprocessor
from ai_processing.auto_labeler import AutoLabeler

logger = get_logger(__name__)

class OCRBridge:
    """OCR 데이터베이스 브릿지 클래스 - 동기화 전용"""
    
    def __init__(self, rag_db: AsyncIOMotorDatabase):
        self.rag_db = rag_db
        self.ocr_client = None
        self.ocr_db = None
        
        # 문서 처리 컴포넌트 추가
        self.chunker = TextChunker()
        self.embedder = TextEmbedder()
        self.preprocessor = TextPreprocessor()
        self.auto_labeler = AutoLabeler()
        
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
            # 텍스트 추출 시도 (우선순위 순서)
            raw_text = ""
            
            # 1. pages 필드 처리
            pages_data = ocr_doc.get("pages", [])
            if pages_data:
                if isinstance(pages_data, list):
                    if len(pages_data) > 0:
                        # 배열의 각 요소 처리
                        for i, page in enumerate(pages_data):
                            if isinstance(page, str):
                                # 문자열인 경우 그대로 사용
                                raw_text += f"[페이지 {i+1}]\n{page}\n\n"
                            elif isinstance(page, dict):
                                # 딕셔너리인 경우 text 필드 또는 다른 필드 찾기
                                page_text = ""
                                if "text" in page:
                                    page_text = str(page["text"])
                                elif "content" in page:
                                    page_text = str(page["content"])
                                elif "data" in page:
                                    page_text = str(page["data"])
                                else:
                                    # 딕셔너리의 모든 문자열 값 결합
                                    page_values = []
                                    for key, value in page.items():
                                        if isinstance(value, str) and value.strip():
                                            page_values.append(value)
                                    page_text = " ".join(page_values)
                                
                                if page_text.strip():
                                    raw_text += f"[페이지 {i+1}]\n{page_text}\n\n"
                            elif page is not None:
                                # 기타 유형은 문자열로 변환
                                page_text = str(page).strip()
                                if page_text:
                                    raw_text += f"[페이지 {i+1}]\n{page_text}\n\n"
                elif isinstance(pages_data, str):
                    # pages가 문자열인 경우
                    raw_text = f"[페이지 1]\n{pages_data}\n\n"
                elif isinstance(pages_data, dict):
                    # pages가 딕셔너리인 경우
                    if "text" in pages_data:
                        raw_text = f"[페이지 1]\n{pages_data['text']}\n\n"
                    else:
                        # 딕셔너리의 모든 문자열 값 결합
                        page_values = []
                        for key, value in pages_data.items():
                            if isinstance(value, str) and value.strip():
                                page_values.append(value)
                        if page_values:
                            raw_text = f"[페이지 1]\n{' '.join(page_values)}\n\n"
            
            # 2. content 필드 처리 (pages가 없거나 비어있을 때)
            if not raw_text.strip():
                content_field = ocr_doc.get("content", "")
                if isinstance(content_field, str) and content_field.strip():
                    raw_text = f"[페이지 1]\n{content_field}\n\n"
                elif isinstance(content_field, dict):
                    # content가 딕셔너리인 경우
                    content_values = []
                    for key, value in content_field.items():
                        if isinstance(value, str) and value.strip():
                            content_values.append(value)
                    if content_values:
                        raw_text = f"[페이지 1]\n{' '.join(content_values)}\n\n"
            
            # 3. text 필드 직접 확인
            if not raw_text.strip():
                text_field = ocr_doc.get("text", "")
                if isinstance(text_field, str) and text_field.strip():
                    raw_text = f"[페이지 1]\n{text_field}\n\n"
            
            # 4. description 필드 확인
            if not raw_text.strip():
                description_field = ocr_doc.get("description", "")
                if isinstance(description_field, str) and description_field.strip():
                    raw_text = f"[설명]\n{description_field}\n\n"
            
            # 5. 기타 텍스트 필드들 검색
            if not raw_text.strip():
                text_fields = ["data", "message", "body", "details"]
                for field_name in text_fields:
                    field_value = ocr_doc.get(field_name, "")
                    if isinstance(field_value, str) and field_value.strip():
                        raw_text = f"[{field_name}]\n{field_value}\n\n"
                        break
            
            # 6. 이미지만 있는 경우 처리
            if not raw_text.strip():
                if "image_base64" in ocr_doc:
                    # 이미지만 있는 문서인 경우
                    raw_text = f"[이미지 문서]\n제목: {ocr_doc.get('title', '제목없음')}\n설명: 이 문서는 이미지만 포함하고 있습니다.\n"
                    logger.info(f"이미지만 있는 OCR 문서 처리: {ocr_doc.get('_id', 'unknown')}")
                else:
                    # 마지막 시도: 모든 문자열 필드 결합
                    all_texts = []
                    for key, value in ocr_doc.items():
                        if key not in ["_id", "timestamp", "image_base64"] and isinstance(value, str) and value.strip():
                            all_texts.append(f"{key}: {value}")
                    
                    if all_texts:
                        raw_text = f"[문서 정보]\n{chr(10).join(all_texts)}\n\n"
                    else:
                        logger.warning(f"OCR 문서 {ocr_doc.get('_id', 'unknown')}: 추출 가능한 텍스트가 없음")
                        # 빈 문서로라도 저장 (메타데이터는 유지)
                        raw_text = f"[빈 문서]\n제목: {ocr_doc.get('title', '제목없음')}\n설명: 이 문서에서는 텍스트를 추출할 수 없습니다.\n"
            
            # 타임스탬프 안전하게 처리
            created_at = datetime.utcnow()  # 기본값
            
            timestamp = ocr_doc.get("timestamp")
            if timestamp:
                if isinstance(timestamp, datetime):
                    created_at = timestamp
                elif isinstance(timestamp, str):
                    try:
                        # 다양한 형식 시도
                        if len(timestamp) == 19 and ' ' in timestamp:
                            # "2025-06-10 13:47:01" 형식
                            created_at = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                        elif 'T' in timestamp:
                            # ISO 형식
                            created_at = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            # 기타 형식 시도
                            try:
                                from dateutil import parser
                                created_at = parser.parse(timestamp)
                            except ImportError:
                                logger.warning(f"dateutil 없음, 기본 타임스탬프 사용: {ocr_doc['_id']}")
                    except (ValueError, ImportError) as ve:
                        logger.warning(f"타임스탬프 변환 실패 {ocr_doc['_id']}: {timestamp}, 오류: {ve}")
                        # 기본값 사용
            else:
                    logger.warning(f"알 수 없는 타임스탬프 형식 {ocr_doc['_id']}: {type(timestamp)}")
            
            # ObjectId를 문자열로 변환
            doc_id = str(ocr_doc["_id"])
            
            # 제목 안전하게 가져오기
            title = ocr_doc.get("title", "제목없음").strip()
            if not title:
                title = "제목없음"
            
            # 페이지 수 계산
            pages_count = 1
            if isinstance(pages_data, list):
                pages_count = len(pages_data) if pages_data else 1
            
            # RAG 시스템 형식으로 변환
            return {
                "folder_id": folder_id,
                "raw_text": raw_text,
                "created_at": created_at,
                "file_metadata": {
                    "file_id": f"ocr_{doc_id}",
                    "original_filename": f"{title}.ocr",
                    "file_type": "ocr",
                    "file_size": len(raw_text.encode('utf-8')),
                    "description": "OCR로 추출된 텍스트"
                },
                "chunks_count": 0,  # 청킹은 나중에 자동으로 처리됨
                "text_length": len(raw_text),
                "data_source": "ocr_bridge",
                "original_db": "ocr_db.texts",
                "original_ocr_id": doc_id,
                "ocr_title": title,
                "pages_count": pages_count,
                "processing_status": "converted",
                "has_image": "image_base64" in ocr_doc,
                "source_fields": list(ocr_doc.keys())
            }
            
        except Exception as e:
            logger.error(f"OCR 데이터 변환 실패 {ocr_doc.get('_id', 'unknown')}: {e}")
            # 디버깅을 위해 OCR 문서 구조 로깅
            logger.debug(f"OCR 문서 구조: {list(ocr_doc.keys()) if isinstance(ocr_doc, dict) else type(ocr_doc)}")
            raise
    
    async def get_or_create_folder_by_title(self, title: str, timestamp: datetime = None) -> str:
        """title별로 폴더 조회 또는 생성"""
        try:
            # 제목 정리
            clean_title = title.strip() if title else "제목없음"
            if not clean_title:
                clean_title = "제목없음"
            
            # 기존 폴더 찾기 (같은 title, folder_type 상관없이)
            existing_folder = await self.rag_db.folders.find_one({"title": clean_title})
            
            if existing_folder:
                # 기존 폴더의 last_accessed_at 업데이트
                await self.rag_db.folders.update_one(
                    {"_id": existing_folder["_id"]},
                    {"$set": {"last_accessed_at": datetime.utcnow()}}
                )
                return str(existing_folder["_id"])
            
            # 새 폴더 생성
            folder_created_at = timestamp or datetime.utcnow()
            folder_data = {
                "title": clean_title,
                "folder_type": "library",
                "created_at": folder_created_at,
                "last_accessed_at": datetime.utcnow(),
                "cover_image_url": None,
                "document_count": 0,
                "file_count": 0,
                "description": f"OCR 추출 문서: {clean_title}",
                "updated_at": datetime.utcnow()
            }
            
            result = await self.rag_db.folders.insert_one(folder_data)
            folder_id = str(result.inserted_id)
            logger.info(f"OCR 폴더 생성: {folder_id} (제목: {clean_title}, folder_type: library)")
            return folder_id
            
        except Exception as e:
            logger.error(f"OCR 폴더 조회/생성 실패 (제목: {title}): {e}")
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
    
    async def _process_document_complete(self, rag_doc: Dict) -> Dict:
        """문서를 documents에 저장한 후 청킹/임베딩까지 완전 처리"""
        try:
            # 1. documents 컬렉션에 저장
            document_result = await self.rag_db.documents.insert_one(rag_doc)
            document_id = document_result.inserted_id
            
            # 2. 청킹 및 임베딩 처리
            file_id = rag_doc["file_metadata"]["file_id"]
            raw_text = rag_doc.get("raw_text", "")
            
            if not raw_text.strip():
                logger.warning(f"빈 텍스트로 청킹 건너뜀: {file_id}")
                return {
                    "document_id": document_id,
                    "chunks_count": 0,
                    "processed": False
                }
            
            # 텍스트 전처리
            processed_text = await self.preprocessor.preprocess(raw_text)
            
            # 청킹
            chunk_metadata = {
                "file_id": file_id,
                "source": rag_doc["file_metadata"]["original_filename"],
                "file_type": rag_doc["file_metadata"]["file_type"],
                "folder_id": rag_doc["folder_id"]
            }
            
            chunks = self.chunker.chunk_text(processed_text, chunk_metadata)
            
            if not chunks:
                logger.warning(f"청킹 결과 없음: {file_id}")
                return {
                    "document_id": document_id,
                    "chunks_count": 0,
                    "processed": False
                }
            
            # 임베딩 생성
            embedded_chunks = await self.embedder.embed_documents(chunks)
            
            # chunks 컬렉션에 저장
            chunk_records = []
            for i, chunk in enumerate(embedded_chunks):
                chunk_record = {
                    "file_id": file_id,
                    "chunk_id": f"{file_id}_chunk_{i}",
                    "sequence": i,
                    "text": chunk["text"],
                    "text_embedding": chunk["text_embedding"],
                    "folder_id": rag_doc["folder_id"],
                    "metadata": {
                        "source": rag_doc["file_metadata"]["original_filename"],
                        "file_type": rag_doc["file_metadata"]["file_type"],
                        "folder_id": rag_doc["folder_id"],
                        "chunk_method": "sliding_window",
                        "chunk_size": chunk.get("metadata", {}).get("chunk_size", self.chunker.chunk_size),
                        "chunk_overlap": chunk.get("metadata", {}).get("chunk_overlap", self.chunker.chunk_overlap)
                    },
                    "created_at": datetime.utcnow()
                }
                chunk_records.append(chunk_record)
            
            # 배치 저장
            await self.rag_db.chunks.insert_many(chunk_records)
            
            # documents 컬렉션 업데이트 (청킹 완료 표시)
            await self.rag_db.documents.update_one(
                {"_id": document_id},
                {
                    "$set": {
                        "chunks_count": len(chunk_records),
                        "processed_text": processed_text,
                        "chunking_completed_at": datetime.utcnow(),
                        "processing_status": "completed"
                    }
                }
            )
            
            # 자동 라벨링 실행
            try:
                labels = await self.auto_labeler.analyze_document(
                    processed_text, 
                    rag_doc["file_metadata"]["original_filename"]
                )
                
                if labels:
                    label_record = {
                        "document_id": file_id,
                        "folder_id": rag_doc["folder_id"],
                        "labels": labels,
                        "created_at": datetime.utcnow(),
                        "source": "ocr_bridge_auto"
                    }
                    await self.rag_db.labels.insert_one(label_record)
                    
                    # documents에 라벨 정보 추가
                    await self.rag_db.documents.update_one(
                        {"_id": document_id},
                        {"$set": {"labels": labels}}
                    )
            except Exception as e:
                logger.warning(f"자동 라벨링 실패 {file_id}: {e}")
            
            logger.info(f"OCR 문서 완전 처리 완료: {file_id} ({len(chunk_records)}개 청크)")
            
            return {
                "document_id": document_id,
                "chunks_count": len(chunk_records),
                "processed": True
            }
            
        except Exception as e:
            logger.error(f"OCR 문서 완전 처리 실패: {e}")
            raise
    
    async def sync_new_ocr_data(self, since_timestamp: Optional[datetime] = None) -> Dict:
        """새로운 OCR 데이터만 RAG 시스템으로 동기화 (청킹/임베딩 포함)"""
        try:
            if self.ocr_db is None:
                await self.connect_ocr_db()
            
            # 동기화 시점 결정 (사용자 제공 날짜 우선)
            if since_timestamp is None:
                # 마지막 동기화 시점 조회 (사용자가 날짜를 지정하지 않은 경우에만)
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
            
            # RAG 시스템에 동기화 (청킹/임베딩 포함)
            synced_count = 0
            processed_count = 0
            
            for ocr_doc in new_ocr_docs:
                try:
                    # 각 문서별로 폴더 확인/생성
                    doc_title = ocr_doc.get("title", "제목없음")
                    doc_timestamp = ocr_doc.get("timestamp")
                    if isinstance(doc_timestamp, str):
                        try:
                            if len(doc_timestamp) == 19:
                                doc_timestamp = doc_timestamp.replace(' ', 'T') + '+00:00'
                            doc_timestamp = datetime.fromisoformat(doc_timestamp)
                        except:
                            doc_timestamp = None
                    elif not isinstance(doc_timestamp, datetime):
                        doc_timestamp = None
                    
                    folder_id = await self.get_or_create_folder_by_title(doc_title, doc_timestamp)
                    
                    # 이미 동기화된 문서인지 확인
                    existing = await self.rag_db.documents.find_one(
                        {"file_metadata.file_id": f"ocr_{ocr_doc['_id']}"}
                    )
                    
                    if not existing:
                        # RAG 형식으로 변환하여 완전 처리 (청킹/임베딩 포함)
                        rag_doc = self.convert_ocr_to_rag_format(ocr_doc, folder_id)
                        process_result = await self._process_document_complete(rag_doc)
                        
                        synced_count += 1
                        if process_result["processed"]:
                            processed_count += 1
                        
                        # 폴더 카운트 업데이트
                        await self.rag_db.folders.update_one(
                            {"_id": ObjectId(folder_id)},
                            {"$inc": {"document_count": 1, "file_count": 1}}
                        )
                        
                except Exception as e:
                    logger.warning(f"문서 동기화 실패 {ocr_doc['_id']}: {e}")
            
            # 동기화 시점 기록 (실제로 동기화가 발생한 경우에만)
            if synced_count > 0:
                sync_record = {
                    "sync_type": "ocr_bridge",
                    "last_sync_time": current_time,
                    "synced_count": synced_count,
                    "processed_count": processed_count,
                    "total_ocr_count": len(new_ocr_docs)
                }
                
                # upsert 기능을 위해 직접 MongoDB 컬렉션 사용
                await self.rag_db.system_sync.update_one(
                    {"sync_type": "ocr_bridge"},
                    {"$set": sync_record},
                    upsert=True
                )
            
            logger.info(f"OCR 데이터 완전 동기화 완료: {synced_count}개 동기화, {processed_count}개 처리 완료")
            return {
                "synced_count": synced_count,
                "processed_count": processed_count,
                "total_new_data": len(new_ocr_docs),
                "last_sync_time": current_time,
                "message": f"{synced_count}개 동기화, {processed_count}개 청킹/임베딩 완료"
            }
            
        except Exception as e:
            logger.error(f"OCR 데이터 동기화 실패: {e}")
            raise
    
    async def force_sync_all_data(self) -> Dict:
        """타임스탬프 필터링 없이 모든 OCR 데이터 강제 동기화 (청킹/임베딩 포함)"""
        try:
            if self.ocr_db is None:
                await self.connect_ocr_db()
            
            # 타임스탬프 필터링 없이 모든 OCR 데이터 조회
            all_ocr_docs = await self.ocr_db.texts.find({}).to_list(None)
            
            # 현재 시간 기록
            current_time = datetime.utcnow()
            
            if not all_ocr_docs:
                return {
                    "synced_count": 0, 
                    "processed_count": 0,
                    "total_new_data": 0,
                    "last_sync_time": current_time,
                    "message": "OCR 데이터 없음"
                }
            
            # RAG 시스템에 동기화 (청킹/임베딩 포함)
            synced_count = 0
            processed_count = 0
            
            logger.info(f"전체 OCR 데이터 {len(all_ocr_docs)}개 완전 동기화 시작...")
            
            for ocr_doc in all_ocr_docs:
                try:
                    # 각 문서별로 폴더 확인/생성
                    doc_title = ocr_doc.get("title", "제목없음")
                    doc_timestamp = ocr_doc.get("timestamp")
                    if isinstance(doc_timestamp, str):
                        try:
                            if len(doc_timestamp) == 19:
                                doc_timestamp = doc_timestamp.replace(' ', 'T') + '+00:00'
                            doc_timestamp = datetime.fromisoformat(doc_timestamp)
                        except:
                            doc_timestamp = None
                    elif not isinstance(doc_timestamp, datetime):
                        doc_timestamp = None
                    
                    folder_id = await self.get_or_create_folder_by_title(doc_title, doc_timestamp)
                    
                    # 이미 동기화된 문서인지 확인
                    existing = await self.rag_db.documents.find_one(
                        {"file_metadata.file_id": f"ocr_{ocr_doc['_id']}"}
                    )
                    
                    if not existing:
                        # RAG 형식으로 변환하여 완전 처리 (청킹/임베딩 포함)
                        rag_doc = self.convert_ocr_to_rag_format(ocr_doc, folder_id)
                        process_result = await self._process_document_complete(rag_doc)
                        
                        synced_count += 1
                        if process_result["processed"]:
                            processed_count += 1
                            
                        logger.info(f"완전 동기화 완료: OCR ID {ocr_doc['_id']} -> 폴더: {doc_title} ({process_result['chunks_count']}개 청크)")
                        
                        # 폴더 카운트 업데이트
                        await self.rag_db.folders.update_one(
                            {"_id": ObjectId(folder_id)},
                            {"$inc": {"document_count": 1, "file_count": 1}}
                        )
                    else:
                        logger.debug(f"이미 동기화됨: OCR ID {ocr_doc['_id']}")
                        
                except Exception as e:
                    logger.warning(f"문서 동기화 실패 {ocr_doc['_id']}: {e}")
            
            # 동기화 시점 기록 (강제 동기화 후 항상 업데이트)
            sync_record = {
                "sync_type": "ocr_bridge",
                "last_sync_time": current_time,
                "synced_count": synced_count,
                "processed_count": processed_count,
                "total_ocr_count": len(all_ocr_docs),
                "sync_method": "force_all_complete"
            }
            
            await self.rag_db.system_sync.update_one(
                {"sync_type": "ocr_bridge"},
                {"$set": sync_record},
                upsert=True
            )
            
            logger.info(f"강제 전체 완전 동기화 완료: {synced_count}개 새로 동기화됨, {processed_count}개 처리 완료 (총 {len(all_ocr_docs)}개 확인)")
            return {
                "synced_count": synced_count,
                "processed_count": processed_count,
                "total_new_data": len(all_ocr_docs),
                "last_sync_time": current_time,
                "message": f"전체 {len(all_ocr_docs)}개 문서 확인, {synced_count}개 새로 동기화, {processed_count}개 완전 처리"
            }
            
        except Exception as e:
            logger.error(f"강제 전체 동기화 실패: {e}")
            raise
    
    async def clean_and_resync_all_data(self) -> Dict:
        """OCR 폴더 정리 후 전체 데이터 재동기화"""
        try:
            if self.ocr_db is None:
                await self.connect_ocr_db()
            
            # 기존 OCR 브릿지 데이터 모두 삭제
            delete_result = await self.rag_db.documents.delete_many({
                "data_source": "ocr_bridge"
            })
            logger.info(f"기존 OCR 브릿지 데이터 {delete_result.deleted_count}개 삭제")
            
            # 기존 OCR 폴더들의 카운트 초기화
            await self.rag_db.folders.update_many(
                {"folder_type": "ocr"},
                {"$set": {"document_count": 0, "file_count": 0}}
            )
            
            # 모든 OCR 데이터 조회
            all_ocr_docs = await self.ocr_db.texts.find({}).to_list(None)
            
            # 현재 시간 기록
            current_time = datetime.utcnow()
            
            if not all_ocr_docs:
                return {
                    "synced_count": 0, 
                    "total_new_data": 0,
                    "last_sync_time": current_time,
                    "message": "OCR 데이터 없음"
                }
            
            synced_count = 0
            folder_counts = {}  # 각 폴더별 문서 수 추적
            
            logger.info(f"전체 OCR 데이터 {len(all_ocr_docs)}개 재동기화 시작...")
            
            for ocr_doc in all_ocr_docs:
                try:
                    # 각 문서별로 폴더 확인/생성
                    doc_title = ocr_doc.get("title", "제목없음")
                    doc_timestamp = ocr_doc.get("timestamp")
                    if isinstance(doc_timestamp, str):
                        try:
                            if len(doc_timestamp) == 19:
                                doc_timestamp = doc_timestamp.replace(' ', 'T') + '+00:00'
                            doc_timestamp = datetime.fromisoformat(doc_timestamp)
                        except:
                            doc_timestamp = None
                    elif not isinstance(doc_timestamp, datetime):
                        doc_timestamp = None
                    
                    folder_id = await self.get_or_create_folder_by_title(doc_title, doc_timestamp)
                    
                    # 모든 데이터를 새로 동기화 (중복 체크 없음)
                    rag_doc = self.convert_ocr_to_rag_format(ocr_doc, folder_id)
                    await self.rag_db.documents.insert_one(rag_doc)
                    synced_count += 1
                    
                    # 폴더별 카운트 추적
                    if folder_id not in folder_counts:
                        folder_counts[folder_id] = 0
                    folder_counts[folder_id] += 1
                    
                    logger.info(f"재동기화 완료: OCR ID {ocr_doc['_id']} -> 폴더: {doc_title}")
                        
                except Exception as e:
                    logger.warning(f"문서 재동기화 실패 {ocr_doc['_id']}: {e}")
            
            # 각 폴더의 카운트 업데이트
            for folder_id, count in folder_counts.items():
                await self.rag_db.folders.update_one(
                    {"_id": ObjectId(folder_id)},
                    {
                        "$set": {
                            "document_count": count,
                            "file_count": count,
                            "last_accessed_at": current_time,
                            "updated_at": current_time
                        }
                    }
                )
            
            # 동기화 시점 기록
            sync_record = {
                "sync_type": "ocr_bridge",
                "last_sync_time": current_time,
                "synced_count": synced_count,
                "total_ocr_count": len(all_ocr_docs),
                "sync_method": "clean_resync",
                "folders_created": len(folder_counts)
            }
            
            await self.rag_db.system_sync.update_one(
                {"sync_type": "ocr_bridge"},
                {"$set": sync_record},
                upsert=True
            )
            
            logger.info(f"정리 후 재동기화 완료: {synced_count}개 동기화됨, {len(folder_counts)}개 폴더 생성/업데이트")
            return {
                "synced_count": synced_count,
                "total_new_data": len(all_ocr_docs),
                "last_sync_time": current_time,
                "message": f"정리 완료 후 전체 {len(all_ocr_docs)}개 문서 재동기화, {len(folder_counts)}개 폴더 처리"
            }
            
        except Exception as e:
            logger.error(f"정리 후 재동기화 실패: {e}")
            raise
    
    async def process_ocr_documents_for_search(self) -> Dict:
        """기존 documents 컬렉션의 OCR 데이터들을 청킹/임베딩 처리하여 검색 가능하게 만들기"""
        try:
            logger.info("OCR 문서 검색 처리 시작...")
            
            # documents 컬렉션에서 OCR 브릿지로 저장된 문서들 조회
            ocr_documents = await self.rag_db.documents.find({
                "data_source": "ocr_bridge"
            }).to_list(None)
            
            if not ocr_documents:
                return {
                    "processed_count": 0,
                    "total_documents": 0,
                    "message": "처리할 OCR 문서 없음"
                }
            
            processed_count = 0
            total_documents = len(ocr_documents)
            
            logger.info(f"총 {total_documents}개 OCR 문서 처리 시작")
            
            for doc in ocr_documents:
                try:
                    file_id = doc["file_metadata"]["file_id"]
                    
                    # 이미 청킹된 문서인지 확인
                    existing_chunks = await self.rag_db.chunks.count_documents({"file_id": file_id})
                    if existing_chunks > 0:
                        logger.debug(f"이미 청킹됨: {file_id} ({existing_chunks}개 청크)")
                        continue
                    
                    # 텍스트 전처리
                    raw_text = doc.get("raw_text", "")
                    if not raw_text.strip():
                        logger.warning(f"빈 텍스트: {file_id}")
                        continue
                    
                    processed_text = await self.preprocessor.preprocess(raw_text)
                    
                    # 청킹
                    chunk_metadata = {
                        "file_id": file_id,
                        "source": doc["file_metadata"]["original_filename"],
                        "file_type": doc["file_metadata"]["file_type"],
                        "folder_id": doc["folder_id"]
                    }
                    
                    chunks = self.chunker.chunk_text(processed_text, chunk_metadata)
                    
                    if not chunks:
                        logger.warning(f"청킹 결과 없음: {file_id}")
                        continue
                    
                    # 임베딩 생성
                    embedded_chunks = await self.embedder.embed_documents(chunks)
                    
                    # chunks 컬렉션에 저장
                    chunk_records = []
                    for i, chunk in enumerate(embedded_chunks):
                        chunk_record = {
                            "file_id": file_id,
                            "chunk_id": f"{file_id}_chunk_{i}",
                            "sequence": i,
                            "text": chunk["text"],
                            "text_embedding": chunk["text_embedding"],
                            "folder_id": doc["folder_id"],
                            "metadata": {
                                "source": doc["file_metadata"]["original_filename"],
                                "file_type": doc["file_metadata"]["file_type"],
                                "folder_id": doc["folder_id"],
                                "chunk_method": "sliding_window",
                                "chunk_size": chunk.get("metadata", {}).get("chunk_size", self.chunker.chunk_size),
                                "chunk_overlap": chunk.get("metadata", {}).get("chunk_overlap", self.chunker.chunk_overlap)
                            },
                            "created_at": datetime.utcnow()
                        }
                        chunk_records.append(chunk_record)
                    
                    # 배치 저장
                    await self.rag_db.chunks.insert_many(chunk_records)
                    
                    # documents 컬렉션 업데이트 (청킹 완료 표시)
                    await self.rag_db.documents.update_one(
                        {"_id": doc["_id"]},
                        {
                            "$set": {
                                "chunks_count": len(chunk_records),
                                "processed_text": processed_text,
                                "chunking_completed_at": datetime.utcnow(),
                                "processing_status": "completed"
                            }
                        }
                    )
                    
                    # 자동 라벨링 실행
                    try:
                        labels = await self.auto_labeler.analyze_document(
                            processed_text, 
                            doc["file_metadata"]["original_filename"]
                        )
                        
                        if labels:
                            label_record = {
                                "document_id": file_id,
                                "folder_id": doc["folder_id"],
                                "labels": labels,
                                "created_at": datetime.utcnow(),
                                "source": "ocr_bridge_processing"
                            }
                            await self.rag_db.labels.insert_one(label_record)
                            
                            # documents에 라벨 정보 추가
                            await self.rag_db.documents.update_one(
                                {"_id": doc["_id"]},
                                {"$set": {"labels": labels}}
                            )
                    except Exception as e:
                        logger.warning(f"자동 라벨링 실패 {file_id}: {e}")
                    
                    processed_count += 1
                    logger.info(f"처리 완료: {file_id} ({len(chunk_records)}개 청크)")
                    
                except Exception as e:
                    logger.error(f"문서 처리 실패 {doc.get('file_metadata', {}).get('file_id', 'unknown')}: {e}")
            
            logger.info(f"OCR 문서 처리 완료: {processed_count}/{total_documents}개")
            
            return {
                "processed_count": processed_count,
                "total_documents": total_documents,
                "message": f"{processed_count}개 문서 청킹/임베딩 처리 완료",
                "completed_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"OCR 문서 처리 실패: {e}")
            raise 