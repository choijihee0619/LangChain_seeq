"""
문서 처리 파이프라인
텍스트 추출 → 청킹 → 벡터화 → DB 저장
MODIFIED 2024-12-19: 새로운 통합 문서 처리 파이프라인 구현
ENHANCED 2024-12-20: 새로운 데이터베이스 구조 및 자동 라벨링 통합
"""
from typing import Dict, List
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId

from .loader import DocumentLoader
from .chunker import TextChunker
from .embedder import TextEmbedder
from .preprocessor import TextPreprocessor
from database.operations import DatabaseOperations
from ai_processing.auto_labeler import AutoLabeler
from utils.logger import get_logger

logger = get_logger(__name__)

class DocumentProcessor:
    """문서 처리 파이프라인 클래스"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.db_ops = DatabaseOperations(db)
        self.loader = DocumentLoader()
        self.chunker = TextChunker()
        self.embedder = TextEmbedder()
        self.preprocessor = TextPreprocessor()
        self.auto_labeler = AutoLabeler()
    
    async def process_and_store(self, file_path: Path, file_metadata: Dict, preserve_formatting: bool = True) -> Dict:
        """전체 문서 처리 및 저장 파이프라인"""
        try:
            logger.info(f"문서 처리 시작: {file_path} (포맷팅 보존: {preserve_formatting})")
            
            # 1. 문서 로드 및 텍스트 추출
            document_data = await self.loader.load_document(file_path)
            raw_text = document_data["text"]
            
            logger.info(f"텍스트 추출 완료: {len(raw_text)} 문자")
            
            # 2. 텍스트 전처리 (줄바꿈 보존 옵션)
            if preserve_formatting:
                processed_text = await self.preprocessor.preprocess_minimal(raw_text)  # 줄바꿈 최대 보존
            else:
                processed_text = await self.preprocessor.preprocess(raw_text)  # 기본 전처리
            
            # 3. 정규화된 폴더 처리
            folder_id = file_metadata.get("folder_id")
            validated_folder_id = await self._validate_and_get_folder_id(folder_id)
            
            # 4. 자동 라벨링 실행
            labels = await self.auto_labeler.analyze_document(
                processed_text, 
                file_metadata.get("original_filename", "")
            )
            
            # 메타데이터에 검증된 folder_id 업데이트
            file_metadata["folder_id"] = validated_folder_id
            
            # 5. 텍스트 청킹
            chunk_metadata = {
                "file_id": file_metadata["file_id"],
                "source": str(file_path),
                "file_type": file_metadata["file_type"],
                "folder_id": validated_folder_id  # 검증된 ObjectId 사용
            }
            
            chunks = self.chunker.chunk_text(processed_text, chunk_metadata)
            logger.info(f"청킹 완료: {len(chunks)}개 청크")
            
            # 6. 청크 임베딩 생성
            embedded_chunks = await self.embedder.embed_documents(chunks)
            
            # 7. documents 컬렉션에 저장 (파일당 하나의 레코드)
            document_record = {
                "folder_id": validated_folder_id,  # ObjectId 문자열
                "raw_text": processed_text,  # 전체 처리된 텍스트
                "created_at": datetime.utcnow(),
                # 메타데이터 추가
                "file_metadata": {
                    "file_id": file_metadata["file_id"],
                    "original_filename": file_metadata["original_filename"],
                    "file_type": file_metadata["file_type"],
                    "file_size": file_metadata["file_size"],
                    "description": file_metadata.get("description")
                },
                # 청크 통계 정보
                "chunks_count": len(embedded_chunks),
                "text_length": len(processed_text)
            }
            
            # documents 컬렉션에 단일 문서 저장
            document_id = await self.db_ops.insert_one("documents", document_record)
            logger.info(f"documents 컬렉션에 파일 단위 문서 저장 완료: {document_id}")
            
            # 8. chunks 컬렉션에 청크별 저장 (기존 호환성 유지)
            chunk_records = []
            for i, chunk in enumerate(embedded_chunks):
                chunk_record = {
                    "file_id": file_metadata["file_id"],
                    "chunk_id": f"{file_metadata['file_id']}_chunk_{i}",
                    "sequence": i,
                    "text": chunk["text"],
                    "text_embedding": chunk["text_embedding"],
                    "folder_id": validated_folder_id,  # 추가: 폴더 필터링용
                    "metadata": {
                        "source": file_metadata["original_filename"],
                        "file_type": file_metadata["file_type"],
                        "folder_id": validated_folder_id,  # ObjectId 문자열
                        "chunk_method": "sliding_window",
                        "chunk_size": chunk.get("metadata", {}).get("chunk_size", self.chunker.chunk_size),
                        "chunk_overlap": chunk.get("metadata", {}).get("chunk_overlap", self.chunker.chunk_overlap)
                    }
                }
                chunk_records.append(chunk_record)
            
            # chunks 컬렉션에 배치 저장
            chunk_ids = await self.db_ops.insert_many("chunks", chunk_records)
            logger.info(f"chunks 컬렉션에 {len(chunk_ids)}개 청크 저장 완료")
            
            # 9. 자동 라벨링 결과 저장
            if labels:
                try:
                    label_id = await self.db_ops.save_document_labels(
                        document_id=file_metadata["file_id"],
                        folder_id=validated_folder_id,
                        labels=labels
                    )
                    logger.info(f"자동 라벨링 저장 완료: {label_id}")
                except Exception as e:
                    logger.warning(f"자동 라벨링 저장 실패: {e}")
            
            # 10. 폴더 접근 시간 업데이트
            if validated_folder_id:
                await self.db_ops.update_folder_access(validated_folder_id)
            
            return {
                "success": True,
                "file_id": file_metadata["file_id"],
                "folder_id": validated_folder_id,
                "original_filename": file_metadata["original_filename"],
                "text_length": len(raw_text),
                "processed_text_length": len(processed_text),
                "chunks_count": len(embedded_chunks),
                "document_id": document_id,
                "chunk_ids": chunk_ids,
                "labels": labels,
                "processing_time": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"문서 처리 실패: {e}")
            
            # 실패 시 상태 기록
            try:
                error_record = {
                    **file_metadata,
                    "processing_status": "failed",
                    "error_message": str(e),
                    "failed_at": datetime.utcnow()
                }
                await self.db_ops.insert_one("file_info", error_record)
            except Exception as save_error:
                logger.error(f"오류 기록 저장 실패: {save_error}")
            
            raise
    
    async def reprocess_document(self, file_id: str) -> Dict:
        """문서 재처리 (기존 유지, 새로운 구조 적용)"""
        try:
            # 기존 파일 정보 조회
            file_info = await self.db_ops.find_one("file_info", {"file_id": file_id})
            if not file_info:
                raise ValueError(f"파일 정보를 찾을 수 없습니다: {file_id}")
            
            # 기존 데이터 삭제
            await self.db.documents.delete_many({"file_metadata.file_id": file_id})
            await self.db.chunks.delete_many({"file_id": file_id})
            await self.db.labels.delete_many({"document_id": str(file_info["_id"])})
            
            # 재처리를 위한 메타데이터 준비
            file_metadata = {
                "file_id": file_id,
                "original_filename": file_info["original_filename"],
                "file_type": file_info["file_type"],
                "file_size": file_info["file_size"],
                "folder_id": file_info.get("folder_id"),
                "description": file_info.get("description")
            }
            
            # 기존 텍스트로 재처리
            processed_text = file_info.get("processed_text", file_info.get("raw_text", ""))
            
            # 새로운 구조로 재처리
            result = await self._reprocess_with_new_structure(file_metadata, processed_text)
            
            # 파일 정보 업데이트
            await self.db_ops.update_one(
                "file_info",
                {"file_id": file_id},
                {
                    "$set": {
                        "processing_status": "completed",
                        "chunks_count": result["chunks_count"],
                        "labels": result["labels"],
                        "document_id": result["document_id"],
                        "reprocessed_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"문서 재처리 완료: {file_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"문서 재처리 실패: {e}")
            raise
    
    async def _reprocess_with_new_structure(self, file_metadata: Dict, processed_text: str) -> Dict:
        """새로운 구조로 재처리"""
        try:
            # 자동 라벨링
            labels = await self.auto_labeler.analyze_document(
                processed_text, 
                file_metadata.get("original_filename", "")
            )
            
            # 폴더 ID 검증
            folder_id = file_metadata.get("folder_id")
            validated_folder_id = await self._validate_and_get_folder_id(folder_id)
            file_metadata["folder_id"] = validated_folder_id
            
            # 청킹
            chunk_metadata = {
                "file_id": file_metadata["file_id"],
                "source": "reprocessed",
                "file_type": file_metadata["file_type"],
                "folder_id": validated_folder_id
            }
            
            chunks = self.chunker.chunk_text(processed_text, chunk_metadata)
            embedded_chunks = await self.embedder.embed_documents(chunks)
            
            # 7. documents 컬렉션에 저장 (파일당 하나의 레코드)
            document_record = {
                "folder_id": validated_folder_id,  # ObjectId 문자열
                "raw_text": processed_text,  # 전체 처리된 텍스트
                "created_at": datetime.utcnow(),
                # 메타데이터 추가
                "file_metadata": {
                    "file_id": file_metadata["file_id"],
                    "original_filename": file_metadata["original_filename"],
                    "file_type": file_metadata["file_type"],
                    "file_size": file_metadata["file_size"],
                    "description": file_metadata.get("description")
                },
                # 청크 통계 정보
                "chunks_count": len(embedded_chunks),
                "text_length": len(processed_text)
            }
            
            # documents 컬렉션에 단일 문서 저장
            document_id = await self.db_ops.insert_one("documents", document_record)
            logger.info(f"documents 컬렉션에 파일 단위 문서 저장 완료: {document_id}")
            
            # 8. chunks 컬렉션에 청크별 저장 (기존 호환성 유지)
            chunk_records = []
            for i, chunk in enumerate(embedded_chunks):
                chunk_record = {
                    "file_id": file_metadata["file_id"],
                    "chunk_id": f"{file_metadata['file_id']}_chunk_{i}",
                    "sequence": i,
                    "text": chunk["text"],
                    "text_embedding": chunk["text_embedding"],
                    "folder_id": validated_folder_id,  # 추가: 폴더 필터링용
                    "metadata": {
                        "source": file_metadata["original_filename"],
                        "file_type": file_metadata["file_type"],
                        "folder_id": validated_folder_id,  # ObjectId 문자열
                        "chunk_method": "sliding_window",
                        "chunk_size": chunk.get("metadata", {}).get("chunk_size", self.chunker.chunk_size),
                        "chunk_overlap": chunk.get("metadata", {}).get("chunk_overlap", self.chunker.chunk_overlap)
                    }
                }
                chunk_records.append(chunk_record)
            
            # chunks 컬렉션에 배치 저장
            chunk_ids = await self.db_ops.insert_many("chunks", chunk_records)
            logger.info(f"chunks 컬렉션에 {len(chunk_ids)}개 청크 저장 완료")
            
            # 9. 자동 라벨링 결과 저장
            if labels:
                try:
                    label_id = await self.db_ops.save_document_labels(
                        document_id=file_metadata["file_id"],
                        folder_id=validated_folder_id,
                        labels=labels
                    )
                    logger.info(f"자동 라벨링 저장 완료: {label_id}")
                except Exception as e:
                    logger.warning(f"자동 라벨링 저장 실패: {e}")
            
            return {
                "chunks_count": len(chunks),
                "labels": labels,
                "document_id": document_id,
                "text_length": len(processed_text),
                "folder_id": validated_folder_id
            }
            
        except Exception as e:
            logger.error(f"새로운 구조 재처리 실패: {e}")
            raise
    
    async def get_document_stats(self, file_id: str) -> Dict:
        """문서 통계 조회"""
        try:
            file_info = await self.db_ops.find_one("file_info", {"file_id": file_id})
            if not file_info:
                return {"error": "파일을 찾을 수 없습니다"}
            
            # 청크 통계
            chunks = await self.db_ops.find_many("chunks", {"file_id": file_id})
            
            # 라벨 정보
            labels = await self.db_ops.find_one("labels", {"document_id": str(file_info["_id"])})
            
            return {
                "file_id": file_id,
                "filename": file_info["original_filename"],
                "file_size": file_info["file_size"],
                "text_length": file_info.get("text_length", 0),
                "chunks_count": len(chunks),
                "processing_status": file_info.get("processing_status", "unknown"),
                "labels": labels,
                "created_at": file_info.get("created_at"),
                "folder_id": file_info.get("folder_id")
            }
            
        except Exception as e:
            logger.error(f"문서 통계 조회 실패: {e}")
            return {"error": str(e)}
    
    async def _validate_and_get_folder_id(self, folder_input: str) -> str:
        """
        폴더 입력을 검증하고 유효한 ObjectId를 반환
        
        Args:
            folder_input: 사용자 입력 (ObjectId 문자열 또는 폴더명)
            
        Returns:
            유효한 ObjectId 문자열
        """
        try:
            # 1. 입력이 없으면 기본 폴더 생성
            if not folder_input or folder_input.strip() in ["", "string", "null"]:
                logger.info("폴더 입력이 없어 기본 폴더를 생성합니다")
                return await self._create_default_folder()
            
            folder_input = folder_input.strip()
            
            # 2. ObjectId 형식인지 확인
            if ObjectId.is_valid(folder_input):
                # ObjectId 형식이면 존재 여부 확인
                folder = await self.db_ops.find_one("folders", {"_id": ObjectId(folder_input)})
                if folder:
                    logger.info(f"기존 폴더 사용: {folder['title']} ({folder_input})")
                    return folder_input
                else:
                    logger.warning(f"ObjectId {folder_input}에 해당하는 폴더가 없어 기본 폴더를 생성합니다")
                    return await self._create_default_folder()
            
            # 3. 폴더명으로 검색
            folder = await self.db_ops.find_one("folders", {"title": folder_input})
            if folder:
                folder_id = str(folder["_id"])
                logger.info(f"폴더명으로 기존 폴더 찾음: {folder_input} -> {folder_id}")
                return folder_id
            
            # 4. 새 폴더 생성
            logger.info(f"새 폴더 생성: {folder_input}")
            folder_id = await self.db_ops.create_folder(
                title=folder_input,
                folder_type="library"
            )
            return folder_id
            
        except Exception as e:
            logger.error(f"폴더 검증 실패: {e}")
            return await self._create_default_folder()
    
    async def _create_default_folder(self) -> str:
        """기본 폴더 생성"""
        try:
            # 기본 폴더가 이미 있는지 확인
            default_folder = await self.db_ops.find_one("folders", {"title": "기본 폴더"})
            if default_folder:
                return str(default_folder["_id"])
            
            # 새 기본 폴더 생성
            folder_id = await self.db_ops.create_folder(
                title="기본 폴더",
                folder_type="library"
            )
            logger.info(f"기본 폴더 생성 완료: {folder_id}")
            return folder_id
            
        except Exception as e:
            logger.error(f"기본 폴더 생성 실패: {e}")
            raise
    
    async def reprocess_document_with_formatting(self, file_id: str, preserve_formatting: bool = True) -> Dict:
        """
        기존 문서를 줄바꿈 보존 방식으로 재처리
        원본 파일이 있어야 함
        """
        try:
            # 기존 파일 정보 조회
            file_info = await self.db_ops.find_one("file_info", {"file_id": file_id})
            if not file_info:
                raise ValueError(f"파일 정보를 찾을 수 없습니다: {file_id}")
            
            # 원본 파일 경로 확인
            original_path = file_info.get("original_path")
            if not original_path or not Path(original_path).exists():
                raise ValueError(f"원본 파일을 찾을 수 없습니다: {original_path}")
            
            logger.info(f"문서 재처리 시작 (포맷팅 보존: {preserve_formatting}): {file_id}")
            
            # 기존 데이터 삭제
            await self.db.documents.delete_many({"file_metadata.file_id": file_id})
            await self.db.chunks.delete_many({"file_id": file_id})
            await self.db.labels.delete_many({"document_id": file_id})
            
            # 재처리를 위한 메타데이터 준비
            file_metadata = {
                "file_id": file_id,
                "original_filename": file_info["original_filename"],
                "file_type": file_info["file_type"],
                "file_size": file_info["file_size"],
                "folder_id": file_info.get("folder_id"),
                "description": file_info.get("description")
            }
            
            # 원본 파일에서 다시 처리
            result = await self.process_and_store(
                file_path=Path(original_path),
                file_metadata=file_metadata,
                preserve_formatting=preserve_formatting
            )
            
            # 파일 정보 업데이트
            await self.db_ops.update_one(
                "file_info",
                {"file_id": file_id},
                {
                    "$set": {
                        "processing_status": "reprocessed",
                        "preserve_formatting": preserve_formatting,
                        "reprocessed_at": datetime.utcnow(),
                        "chunks_count": result["chunks_count"]
                    }
                }
            )
            
            logger.info(f"문서 재처리 완료: {file_id}")
            return result
            
        except Exception as e:
            logger.error(f"문서 재처리 실패: {e}")
            raise
    
    async def batch_reprocess_folder(self, folder_id: str, preserve_formatting: bool = True) -> Dict:
        """
        폴더 내 모든 파일을 일괄 재처리
        """
        try:
            logger.info(f"폴더 일괄 재처리 시작: {folder_id} (포맷팅 보존: {preserve_formatting})")
            
            # 폴더 내 파일 목록 조회
            files = await self.db_ops.find_many("file_info", {"folder_id": folder_id})
            
            results = {
                "total_files": len(files),
                "success_count": 0,
                "failed_count": 0,
                "failed_files": [],
                "processing_details": []
            }
            
            for file_info in files:
                file_id = file_info["file_id"]
                try:
                    result = await self.reprocess_document_with_formatting(
                        file_id=file_id,
                        preserve_formatting=preserve_formatting
                    )
                    
                    results["success_count"] += 1
                    results["processing_details"].append({
                        "file_id": file_id,
                        "filename": file_info["original_filename"],
                        "status": "success",
                        "chunks_count": result["chunks_count"]
                    })
                    
                except Exception as e:
                    results["failed_count"] += 1
                    results["failed_files"].append({
                        "file_id": file_id,
                        "filename": file_info["original_filename"],
                        "error": str(e)
                    })
                    
                    results["processing_details"].append({
                        "file_id": file_id,
                        "filename": file_info["original_filename"],
                        "status": "failed",
                        "error": str(e)
                    })
                    
                    logger.warning(f"파일 재처리 실패: {file_id} - {e}")
            
            logger.info(f"폴더 일괄 재처리 완료: 성공 {results['success_count']}, 실패 {results['failed_count']}")
            return results
            
        except Exception as e:
            logger.error(f"폴더 일괄 재처리 실패: {e}")
            raise
    
    async def reprocess_from_raw_text(self, file_id: str, preserve_formatting: bool = True) -> Dict:
        """
        저장된 raw_text에서 재처리 (원본 파일 없어도 됨)
        하지만 이미 전처리된 텍스트이므로 줄바꿈 복원에는 한계가 있음
        """
        try:
            logger.info(f"raw_text 기반 재처리 시작: {file_id}")
            
            # 기존 documents에서 raw_text 조회
            doc = await self.db_ops.find_one("documents", {"file_metadata.file_id": file_id})
            if not doc:
                raise ValueError(f"저장된 문서를 찾을 수 없습니다: {file_id}")
            
            raw_text = doc.get("raw_text", "")
            if not raw_text:
                raise ValueError(f"저장된 텍스트가 없습니다: {file_id}")
            
            # 기존 데이터 삭제
            await self.db.documents.delete_many({"file_metadata.file_id": file_id})
            await self.db.chunks.delete_many({"file_id": file_id})
            await self.db.labels.delete_many({"document_id": file_id})
            
            # 파일 메타데이터 가져오기
            file_metadata = doc.get("file_metadata", {})
            
            # 텍스트 재전처리
            if preserve_formatting:
                # 최소 전처리로 줄바꿈 최대 보존 시도
                processed_text = await self.preprocessor.preprocess_minimal(raw_text)
            else:
                processed_text = await self.preprocessor.preprocess(raw_text)
            
            # 재처리 및 저장
            result = await self._reprocess_with_new_structure(file_metadata, processed_text)
            
            logger.info(f"raw_text 기반 재처리 완료: {file_id}")
            return result
            
        except Exception as e:
            logger.error(f"raw_text 기반 재처리 실패: {e}")
            raise 