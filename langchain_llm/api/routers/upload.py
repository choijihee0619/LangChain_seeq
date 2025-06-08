"""
파일 업로드 API 라우터
MODIFIED 2024-01-20: 파일 raw text 조회 및 편집 기능 추가
ENHANCED 2024-01-21: 파일 미리보기 기능 추가
REFACTORED 2024-01-21: 중복 검색 API 제거 및 코드 정리
FIXED 2024-01-21: import 경로 수정 (file_processing -> data_processing)
FIXED 2025-06-03: DocumentProcessor 초기화 및 메서드 호출 오류 수정
"""
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database.connection import get_database
from data_processing.document_processor import DocumentProcessor
from retrieval.vector_search import VectorSearch
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

class UploadResponse(BaseModel):
    """업로드 응답 모델"""
    success: bool
    message: str
    file_id: str
    original_filename: str
    processed_chunks: int
    storage_path: Optional[str] = None

class FileStatus(BaseModel):
    """파일 상태 모델"""
    file_id: str
    original_filename: str
    file_type: str
    file_size: int
    status: str  # 'uploading', 'processing', 'completed', 'failed'
    processed_chunks: int
    upload_time: datetime
    folder_id: Optional[str] = None

class FileSearchRequest(BaseModel):
    """파일 검색 요청 모델"""
    query: str
    search_type: str = "both"  # filename, content, both
    folder_id: Optional[str] = None
    limit: int = 20
    skip: int = 0

class FileSearchResult(BaseModel):
    """파일 검색 결과 모델"""
    file_id: str
    original_filename: str
    file_type: str
    file_size: int
    processed_chunks: int
    upload_time: datetime
    folder_id: Optional[str] = None
    description: Optional[str] = None
    match_type: str  # filename, content, both
    relevance_score: float
    matched_content: Optional[str] = None  # 검색어와 매칭된 내용 미리보기

class FileSearchResponse(BaseModel):
    """파일 검색 응답 모델"""
    files: List[FileSearchResult]
    total_found: int
    query: str
    search_type: str
    execution_time: float

class FileUpdateRequest(BaseModel):
    """파일 정보 업데이트 요청 모델"""
    filename: Optional[str] = None
    description: Optional[str] = None
    folder_id: Optional[str] = None
    folder_title: Optional[str] = None

class FilePreviewResponse(BaseModel):
    """파일 미리보기 응답 모델"""
    file_id: str
    original_filename: str
    file_type: str
    preview_text: str
    preview_length: int
    total_length: int
    has_more: bool
    preview_type: str  # "text", "pdf_extract", "document_extract"

@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(None),
    folder_title: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """파일 업로드 및 처리"""
    try:
        # 디버깅: 받은 폼 데이터 로그 출력
        logger.info(f"업로드 폼 데이터 - 파일명: {file.filename}, folder_id: '{folder_id}', folder_title: '{folder_title}', description: '{description}'")
        
        # folder_id와 folder_title 동시 입력 방지
        if (folder_id and folder_id.strip() and folder_id not in ["string", "null"]) and \
           (folder_title and folder_title.strip() and folder_title not in ["string", "null"]):
            raise HTTPException(
                status_code=400, 
                detail="folder_id와 folder_title은 동시에 입력할 수 없습니다. 둘 중 하나만 선택해주세요."
            )
        
        # 파일 정보 검증
        if not file.filename:
            raise HTTPException(status_code=400, detail="파일명이 없습니다.")
        
        # 파일 타입 확인
        allowed_types = ['.txt', '.pdf', '.docx', '.doc', '.md']
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(allowed_types)}"
            )
        
        # 파일 크기 확인 (10MB 제한)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="파일 크기는 10MB를 초과할 수 없습니다.")
        
        # 파일을 다시 처음으로 되돌리기
        await file.seek(0)
        
        # 데이터베이스 연결
        db = await get_database()
        
        # 파일 ID 생성
        file_id = str(uuid.uuid4())
        
        # 임시 파일로 저장
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        temp_filename = f"{file_id}_{file.filename}"
        temp_file_path = upload_dir / temp_filename
        
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(file_content)
        
        # Form 데이터 정리 및 폴더 ID 결정
        clean_folder_id = None
        clean_description = None
        
        # 1. folder_id 직접 입력 처리
        if folder_id and folder_id.strip() and folder_id not in ["string", "null"]:
            clean_folder_id = folder_id.strip()
            logger.info(f"folder_id로 폴더 지정: {clean_folder_id}")
            
            # folder_id 유효성 검증
            from bson import ObjectId
            try:
                if not ObjectId.is_valid(clean_folder_id):
                    raise HTTPException(status_code=400, detail="유효하지 않은 folder_id 형식입니다.")
                
                # 폴더 존재 확인
                folder_exists = await db.folders.find_one({"_id": ObjectId(clean_folder_id)})
                if not folder_exists:
                    raise HTTPException(status_code=404, detail=f"folder_id '{clean_folder_id}'에 해당하는 폴더를 찾을 수 없습니다.")
                    
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise
                raise HTTPException(status_code=400, detail=f"folder_id 검증 실패: {str(e)}")
        
        # 2. folder_title로 폴더 검색 처리
        elif folder_title and folder_title.strip() and folder_title not in ["string", "null"]:
            clean_folder_title = folder_title.strip()
            logger.info(f"folder_title로 폴더 검색: {clean_folder_title}")
            
            # 폴더 title로 검색
            folder_by_title = await db.folders.find_one({"title": clean_folder_title})
            if not folder_by_title:
                raise HTTPException(
                    status_code=404, 
                    detail=f"'{clean_folder_title}' 제목의 폴더를 찾을 수 없습니다. 먼저 폴더를 생성해주세요."
                )
            
            clean_folder_id = str(folder_by_title["_id"])
            logger.info(f"폴더 title '{clean_folder_title}' -> folder_id: {clean_folder_id}")
        
        # 3. description 처리
        if description and description.strip() and description not in ["string", "null"]:
            clean_description = description.strip()
        
        logger.info(f"최종 정리된 데이터 - clean_folder_id: '{clean_folder_id}', clean_description: '{clean_description}'")
        
        # 파일 메타데이터 준비
        file_metadata = {
            "file_id": file_id,
            "original_filename": file.filename,
            "file_type": file_ext[1:],  # 점 제거
            "file_size": len(file_content),
            "upload_time": datetime.utcnow(),
            "folder_id": clean_folder_id,
            "description": clean_description
        }
        
        # 문서 처리기로 파일 처리
        processor = DocumentProcessor(db)
        result = await processor.process_and_store(
            file_path=temp_file_path,
            file_metadata=file_metadata
        )
        
        # 임시 파일 삭제
        try:
            temp_file_path.unlink()
        except Exception as e:
            logger.warning(f"임시 파일 삭제 실패: {e}")
        
        # 성공 메시지 생성
        success_message = "파일 업로드가 완료되었습니다."
        if clean_folder_id:
            # 폴더 정보 조회해서 메시지에 포함
            try:
                folder_info = await db.folders.find_one({"_id": ObjectId(clean_folder_id)})
                if folder_info:
                    success_message += f" (폴더: {folder_info['title']})"
            except:
                pass
        
        logger.info(f"파일 업로드 완료: {file.filename} -> {file_id} (폴더: {clean_folder_id})")
        
        return UploadResponse(
            success=True,
            message=success_message,
            file_id=file_id,
            original_filename=file.filename,
            processed_chunks=result["chunks_count"],
            storage_path=str(temp_file_path)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}")

@router.get("/status/{file_id}", response_model=FileStatus)
async def get_file_status(file_id: str):
    """파일 처리 상태 조회"""
    try:
        db = await get_database()
        
        # 1. file_info 컬렉션에서 파일 정보 조회 (처리 상태 포함)
        file_info = await db.file_info.find_one({"file_id": file_id})
        
        if file_info:
            # file_info에 기록이 있으면 해당 상태 반환
            chunks_count = await db.chunks.count_documents({"file_id": file_id})
            
            return FileStatus(
                file_id=file_id,
                original_filename=file_info["original_filename"],
                file_type=file_info["file_type"],
                file_size=file_info["file_size"],
                status=file_info["processing_status"],  # "processing", "completed", "failed"
                processed_chunks=chunks_count,
                upload_time=file_info["upload_time"],
                folder_id=file_info.get("folder_id")
            )
        
        # 2. documents 컬렉션에서 파일 정보 조회 (새로운 구조)
        document = await db.documents.find_one({"file_metadata.file_id": file_id})
        
        if document:
            # documents에 있으면 성공적으로 처리된 것
            chunks_count = await db.chunks.count_documents({"file_id": file_id})
            file_metadata = document["file_metadata"]
            
            return FileStatus(
                file_id=file_id,
                original_filename=file_metadata["original_filename"],
                file_type=file_metadata["file_type"],
                file_size=file_metadata["file_size"],
                status="completed",  # documents에 있으면 처리 완료
                processed_chunks=chunks_count,
                upload_time=document["created_at"],
                folder_id=document.get("folder_id")
            )
        
        # 3. chunks 컬렉션에서 직접 조회 (레거시 호환성)
        chunk = await db.chunks.find_one({"file_id": file_id})
        
        if chunk:
            # chunks에만 있는 경우 (레거시 데이터)
            chunks_count = await db.chunks.count_documents({"file_id": file_id})
            metadata = chunk.get("metadata", {})
            
            return FileStatus(
                file_id=file_id,
                original_filename=metadata.get("source", "알 수 없는 파일"),
                file_type=metadata.get("file_type", "unknown"),
                file_size=0,  # chunks에서는 파일 크기 정보가 없음
                status="completed",  # chunks에 있으면 처리 완료로 간주
                processed_chunks=chunks_count,
                upload_time=chunk.get("created_at", datetime.utcnow()),
                folder_id=chunk.get("folder_id")
            )
        
        # 4. 어디에도 없으면 404 에러
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=FileSearchResponse)
async def search_files(request: FileSearchRequest):
    """📍 자연어 파일 검색 - 파일명과 내용으로 검색 가능"""
    try:
        start_time = time.time()
        db = await get_database()
        
        # 1. 기본 필터 조건 설정 (folder_id가 실제 값일 때만 적용)
        base_filter = {}
        if request.folder_id and request.folder_id.strip() and request.folder_id != "string":
            base_filter["folder_id"] = request.folder_id
        
        found_files = []
        
        # 2. 파일명 검색 (filename 또는 both)
        if request.search_type in ["filename", "both"]:
            filename_filter = base_filter.copy()
            # 새로운 구조: file_metadata.original_filename에서 검색
            filename_filter["file_metadata.original_filename"] = {"$regex": request.query, "$options": "i"}
            
            filename_docs = await db.documents.find(filename_filter).to_list(None)
            
            for doc in filename_docs:
                file_metadata = doc.get("file_metadata", {})
                file_id = file_metadata.get("file_id")
                
                if not file_id:
                    continue
                    
                chunks_count = doc.get("chunks_count", 0)  # 저장된 통계 사용
                
                found_files.append({
                    "file_id": file_id,
                    "original_filename": file_metadata.get("original_filename", "알 수 없는 파일"),
                    "file_type": file_metadata.get("file_type", "unknown"),
                    "file_size": file_metadata.get("file_size", 0),
                    "processed_chunks": chunks_count,
                    "upload_time": doc.get("created_at", datetime.utcnow()),
                    "folder_id": doc.get("folder_id"),
                    "description": file_metadata.get("description"),
                    "match_type": "filename",
                    "relevance_score": 1.0,  # 파일명 매치는 높은 점수
                    "matched_content": f"파일명 매치: {file_metadata.get('original_filename')}"
                })
        
        # 3. 내용 검색 (content 또는 both) - 새로운 구조에 맞게 수정
        if request.search_type in ["content", "both"]:
            content_filter = base_filter.copy()
            content_filter["raw_text"] = {"$regex": request.query, "$options": "i"}
            
            content_docs = await db.documents.find(content_filter).to_list(None)
            
            for doc in content_docs:
                file_metadata = doc.get("file_metadata", {})
                file_id = file_metadata.get("file_id")
                
                if not file_id:
                    continue
                
                # 이미 파일명으로 찾은 경우 스킵 (중복 방지)
                if any(f["file_id"] == file_id for f in found_files):
                    continue
                
                chunks_count = doc.get("chunks_count", 0)
                raw_text = doc.get("raw_text", "")
                
                # 매칭된 텍스트 추출 (간단한 하이라이트)
                query_lower = request.query.lower()
                text_lower = raw_text.lower()
                
                # 검색어 주변 텍스트 추출
                match_index = text_lower.find(query_lower)
                if match_index != -1:
                    start = max(0, match_index - 50)
                    end = min(len(raw_text), match_index + len(request.query) + 50)
                    matched_content = "..." + raw_text[start:end] + "..."
                else:
                    matched_content = raw_text[:100] + "..."
                
                found_files.append({
                    "file_id": file_id,
                    "original_filename": file_metadata.get("original_filename", "알 수 없는 파일"),
                    "file_type": file_metadata.get("file_type", "unknown"),
                    "file_size": file_metadata.get("file_size", 0),
                    "processed_chunks": chunks_count,
                    "upload_time": doc.get("created_at", datetime.utcnow()),
                    "folder_id": doc.get("folder_id"),
                    "description": file_metadata.get("description"),
                    "match_type": "content",
                    "relevance_score": 0.8,  # 내용 매치는 중간 점수
                    "matched_content": matched_content
                })
        
        # 4. 관련성 점수 순으로 정렬
        sorted_files = sorted(found_files, key=lambda x: x["relevance_score"], reverse=True)
        total_found = len(sorted_files)
        
        # 페이지네이션 적용
        paginated_files = sorted_files[request.skip:request.skip + request.limit]
        
        # 5. 응답 모델에 맞게 변환
        search_results = []
        for file_data in paginated_files:
            search_results.append(FileSearchResult(**file_data))
        
        execution_time = time.time() - start_time
        
        # 디버그 정보 로깅
        logger.info(f"검색 완료 - 쿼리: '{request.query}', 타입: {request.search_type}, 폴더: {request.folder_id}, 결과: {total_found}개")
        
        return FileSearchResponse(
            files=search_results,
            total_found=total_found,
            query=request.query,
            search_type=request.search_type,
            execution_time=round(execution_time, 3)
        )
        
    except Exception as e:
        logger.error(f"파일 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 검색 중 오류가 발생했습니다: {str(e)}")

@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """파일 완전 삭제 - 모든 구조를 지원하는 통합 삭제"""
    try:
        db = await get_database()
        
        deleted_items = {
            "documents": 0,
            "chunks": 0,
            "file_info": 0,
            "labels": 0
        }
        
        logger.info(f"파일 삭제 시작: {file_id}")
        
        # 1. documents 컬렉션에서 삭제 (새 구조 + 기존 구조 모두 지원)
        # 새로운 구조 (file_metadata.file_id)
        doc_result_new = await db.documents.delete_many({"file_metadata.file_id": file_id})
        deleted_items["documents"] += doc_result_new.deleted_count
        
        # 기존 구조 (file_id 직접)
        doc_result_old = await db.documents.delete_many({"file_id": file_id})
        deleted_items["documents"] += doc_result_old.deleted_count
        
        # 2. chunks 컬렉션에서 삭제
        chunks_result = await db.chunks.delete_many({"file_id": file_id})
        deleted_items["chunks"] = chunks_result.deleted_count
        
        # 3. file_info 컬렉션에서 삭제
        file_info_result = await db.file_info.delete_many({"file_id": file_id})
        deleted_items["file_info"] = file_info_result.deleted_count
        
        # 4. labels 컬렉션에서 삭제
        labels_result = await db.labels.delete_many({"document_id": file_id})
        deleted_items["labels"] = labels_result.deleted_count
        
        # 5. 기타 컬렉션들 정리 (에러가 나도 계속 진행)
        try:
            # summaries, qapairs, recommendations에서 혹시 file_id 참조 제거
            await db.summaries.delete_many({"file_id": file_id})
            await db.qapairs.delete_many({
                "$or": [
                    {"file_id": file_id},
                    {"source": file_id}
                ]
            })
            await db.recommendations.delete_many({"file_id": file_id})
        except Exception as e:
            logger.warning(f"기타 컬렉션 정리 중 오류 (무시): {e}")
        
        # 6. 임시 파일 삭제
        try:
            upload_dir = Path("uploads")
            deleted_files = []
            for temp_file in upload_dir.glob(f"{file_id}_*"):
                temp_file.unlink()
                deleted_files.append(str(temp_file))
            if deleted_files:
                logger.info(f"임시 파일 삭제: {deleted_files}")
        except Exception as e:
            logger.warning(f"임시 파일 삭제 실패 (무시): {e}")
        
        # 7. 결과 검증 및 응답
        total_deleted = sum(deleted_items.values())
        
        logger.info(f"파일 삭제 완료: {file_id}")
        logger.info(f"삭제된 항목들: {deleted_items}")
        
        if total_deleted == 0:
            # 삭제할 데이터가 없으면 404
            raise HTTPException(status_code=404, detail="삭제할 파일을 찾을 수 없습니다.")
        
        return {
            "success": True,
            "message": f"파일이 완전히 삭제되었습니다. (총 {total_deleted}개 항목)",
            "file_id": file_id,
            "deleted_counts": deleted_items,
            "total_deleted": total_deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 삭제 중 오류가 발생했습니다: {str(e)}")

@router.get("/list")
async def list_files(folder_id: Optional[str] = None, limit: int = 50, skip: int = 0):
    """업로드된 파일 목록 조회"""
    try:
        db = await get_database()
        
        # 필터 조건
        filter_dict = {}
        if folder_id:
            filter_dict["folder_id"] = folder_id
        
        # 문서 목록 조회 (새로운 구조에 맞는 정렬)
        cursor = db.documents.find(filter_dict).sort("created_at", -1).skip(skip).limit(limit)
        documents = await cursor.to_list(None)
        
        # 각 문서의 청크 개수 조회
        result = []
        for doc in documents:
            file_metadata = doc.get("file_metadata", {})
            file_id = file_metadata.get("file_id")
            
            if not file_id:
                continue
                
            chunks_count = await db.chunks.count_documents({"file_id": file_id})
            
            result.append({
                "file_id": file_id,
                "original_filename": file_metadata.get("original_filename", "알 수 없는 파일"),
                "file_type": file_metadata.get("file_type", "unknown"),
                "file_size": file_metadata.get("file_size", 0),
                "processed_chunks": chunks_count,
                "upload_time": doc.get("created_at", datetime.utcnow()),
                "folder_id": doc.get("folder_id"),
                "description": file_metadata.get("description")
            })
        
        return {
            "files": result,
            "total": len(result),
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"파일 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/semantic-search")
async def semantic_search_files(
    q: str,  # 검색어
    k: int = 5,  # 결과 개수
    folder_id: Optional[str] = None
):
    """AI 기반 의미 검색 - 벡터 유사도로 파일 찾기"""
    try:
        # 검색어 유효성 검사
        if not q or not q.strip():
            raise HTTPException(status_code=400, detail="검색어가 필요합니다.")
        
        # 검색어 정리
        query = q.strip()
        logger.info(f"시맨틱 검색 시작 - 쿼리: '{query}', k: {k}, folder_id: {folder_id}")
        
        db = await get_database()
        vector_search = VectorSearch(db)
        
        # 필터 조건 설정
        filter_dict = {}
        if folder_id and folder_id.strip():  # None이거나 빈 문자열이 아닐 때만
            filter_dict["folder_id"] = folder_id
        
        # 벡터 검색 실행
        search_results = await vector_search.search_similar(
            query=query,
            k=k * 3,  # 더 많이 찾아서 파일별로 그룹화
            filter_dict=filter_dict
        )
        
        # 파일별로 그룹화하고 최고 점수만 남기기
        file_groups = {}
        for result in search_results:
            chunk = result.get("chunk", {})
            document = result.get("document", {})
            score = result.get("score", 0.0)
            file_id = chunk.get("file_id")
            
            if file_id and (file_id not in file_groups or score > file_groups[file_id]["relevance_score"]):
                # chunks 개수 조회
                chunks_count = await db.chunks.count_documents({"file_id": file_id})
                
                file_groups[file_id] = {
                    "file_id": file_id,
                    "original_filename": document.get("original_filename", "알 수 없는 파일"),
                    "file_type": document.get("file_type", "unknown"),
                    "file_size": document.get("file_size", 0),
                    "processed_chunks": chunks_count,
                    "upload_time": document.get("upload_time"),
                    "folder_id": document.get("folder_id"),
                    "description": document.get("description"),
                    "match_type": "semantic",
                    "relevance_score": score,
                    "matched_content": chunk.get("text", "")[:200] + "..."
                }
        
        # 점수 순으로 정렬하고 상위 k개만 반환
        sorted_files = sorted(file_groups.values(), key=lambda x: x["relevance_score"], reverse=True)
        top_files = sorted_files[:k]
        
        # 응답 생성
        search_results = [FileSearchResult(**file_data) for file_data in top_files]
        
        logger.info(f"시맨틱 검색 완료 - {len(search_results)}개 결과")
        
        return FileSearchResponse(
            files=search_results,
            total_found=len(search_results),
            query=query,
            search_type="semantic",
            execution_time=0.0  # 실제 시간 측정은 생략
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"의미 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"의미 검색 중 오류가 발생했습니다: {str(e)}")

@router.get("/content/{file_id}")
async def get_file_content(file_id: str):
    """파일의 원본 텍스트 내용 조회 (토글 표시용)"""
    try:
        db = await get_database()
        
        # documents 컬렉션에서 파일 정보 및 텍스트 조회 (새로운 구조)
        document = await db.documents.find_one(
            {"file_metadata.file_id": file_id},
            {"file_metadata": 1, "raw_text": 1, "created_at": 1}
        )
        
        if not document:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        file_metadata = document.get("file_metadata", {})
        
        return {
            "file_id": file_id,
            "original_filename": file_metadata.get("original_filename", "알 수 없는 파일"),
            "file_type": file_metadata.get("file_type", "unknown"),
            "upload_time": document.get("created_at", datetime.utcnow()),
            "raw_text": document.get("raw_text", ""),
            "processed_text": document.get("raw_text", ""),  # 새 구조에서는 동일
            "text_length": len(document.get("raw_text", ""))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 내용 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{file_id}")
async def update_file_info(file_id: str, request: FileUpdateRequest):
    """파일 정보 업데이트 (파일명, 설명, 폴더 등)"""
    try:
        db = await get_database()
        from bson import ObjectId
        
        # folder_id와 folder_title 동시 사용 방지
        if request.folder_id and request.folder_title:
            raise HTTPException(
                status_code=400, 
                detail="folder_id와 folder_title은 동시에 입력할 수 없습니다. 둘 중 하나만 선택해주세요."
            )
        
        # 업데이트할 필드 준비
        update_fields = {}
        file_metadata_updates = {}
        
        if request.filename is not None and request.filename.strip():
            file_metadata_updates["file_metadata.original_filename"] = request.filename.strip()
        
        if request.description is not None:
            description_value = request.description.strip() if request.description.strip() else None
            file_metadata_updates["file_metadata.description"] = description_value
        
        # 폴더 처리
        final_folder_id = None
        
        # folder_id 직접 입력
        if request.folder_id is not None:
            folder_id_input = request.folder_id.strip() if request.folder_id.strip() else None
            
            if folder_id_input and folder_id_input not in ["string", "null"]:
                # ObjectId 유효성 검증
                if not ObjectId.is_valid(folder_id_input):
                    raise HTTPException(status_code=400, detail="유효하지 않은 folder_id 형식입니다.")
                
                # 폴더 존재 확인
                folder_exists = await db.folders.find_one({"_id": ObjectId(folder_id_input)})
                if not folder_exists:
                    raise HTTPException(status_code=404, detail=f"folder_id '{folder_id_input}'에 해당하는 폴더를 찾을 수 없습니다.")
                
                final_folder_id = folder_id_input
            else:
                final_folder_id = None  # 폴더 해제
            
            update_fields["folder_id"] = final_folder_id
        
        # folder_title로 폴더 검색
        elif request.folder_title is not None:
            folder_title_input = request.folder_title.strip() if request.folder_title.strip() else None
            
            if folder_title_input and folder_title_input not in ["string", "null"]:
                # 폴더 title로 검색
                folder_by_title = await db.folders.find_one({"title": folder_title_input})
                if not folder_by_title:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"'{folder_title_input}' 제목의 폴더를 찾을 수 없습니다."
                    )
                
                final_folder_id = str(folder_by_title["_id"])
                update_fields["folder_id"] = final_folder_id
                logger.info(f"폴더 title '{folder_title_input}' -> folder_id: {final_folder_id}")
            else:
                final_folder_id = None  # 폴더 해제
                update_fields["folder_id"] = final_folder_id
        
        # 업데이트할 내용이 있는지 확인
        all_updates = {**update_fields, **file_metadata_updates}
        if not all_updates:
            raise HTTPException(status_code=400, detail="업데이트할 내용이 없습니다.")
        
        # 파일 존재 확인 (새로운 구조에 맞게 수정)
        document = await db.documents.find_one({"file_metadata.file_id": file_id})
        if not document:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        # 문서 업데이트 (새로운 구조에 맞게 쿼리 수정)
        result = await db.documents.update_one(
            {"file_metadata.file_id": file_id},
            {"$set": all_updates}
        )
        
        if result.modified_count == 0:
            logger.warning(f"파일 정보 업데이트 결과 없음: {file_id}")
        
        # 폴더 변경시 chunks의 metadata도 업데이트
        if "folder_id" in update_fields:
            await db.chunks.update_many(
                {"file_id": file_id},
                {"$set": {"metadata.folder_id": update_fields["folder_id"]}}
            )
        
        # 성공 메시지 생성
        updated_info = []
        if request.filename:
            updated_info.append(f"파일명: {request.filename}")
        if request.description is not None:
            updated_info.append(f"설명: {request.description or '(제거)'}")
        if final_folder_id:
            try:
                folder_info = await db.folders.find_one({"_id": ObjectId(final_folder_id)})
                folder_name = folder_info["title"] if folder_info else final_folder_id
                updated_info.append(f"폴더: {folder_name}")
            except:
                updated_info.append(f"폴더: {final_folder_id}")
        elif "folder_id" in update_fields and not final_folder_id:
            updated_info.append("폴더: (해제)")
        
        success_message = "파일 정보가 업데이트되었습니다."
        if updated_info:
            success_message += f" ({', '.join(updated_info)})"
        
        logger.info(f"파일 정보 업데이트 완료: {file_id} - {all_updates}")
        
        return {
            "success": True,
            "message": success_message,
            "updated_fields": all_updates,
            "file_id": file_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 정보 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview/{file_id}")
async def get_file_preview(file_id: str, max_length: int = 500):
    """파일 미리보기 - 처음 몇 줄의 텍스트를 반환"""
    try:
        db = await get_database()
        
        # documents 컬렉션에서 파일 정보 조회 (새로운 구조에 맞게 수정)
        document = await db.documents.find_one(
            {"file_metadata.file_id": file_id},
            {"file_metadata": 1, "raw_text": 1}
        )
        
        if not document:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        file_metadata = document.get("file_metadata", {})
        raw_text = document.get("raw_text", "")
        file_type = file_metadata.get("file_type", "unknown")
        total_length = len(raw_text)
        
        # 미리보기 텍스트 생성
        preview_text = ""
        preview_type = "text"
        
        if raw_text:
            # 텍스트를 줄 단위로 분할하여 자연스러운 미리보기 생성
            lines = raw_text.split('\n')
            current_length = 0
            preview_lines = []
            
            # 첫 번째 줄이 너무 길면 단순히 잘라서 사용
            if lines and len(lines[0]) > max_length:
                preview_text = raw_text[:max_length] + "..."
            else:
                # 줄 단위로 추가
                for line in lines:
                    if current_length + len(line) + 1 > max_length:  # +1 for newline
                        break
                    preview_lines.append(line)
                    current_length += len(line) + 1
                
                preview_text = '\n'.join(preview_lines)
                
                # 만약 preview_text가 여전히 비어있다면 강제로 일부 텍스트 추가
                if not preview_text and raw_text:
                    preview_text = raw_text[:max_length] + ("..." if len(raw_text) > max_length else "")
            
            # 파일 타입에 따른 미리보기 타입 결정
            if file_type == "pdf":
                preview_type = "pdf_extract"
            elif file_type in ["docx", "doc"]:
                preview_type = "document_extract"
            else:
                preview_type = "text"
        else:
            preview_text = "텍스트를 추출할 수 없습니다."
        
        preview_length = len(preview_text)
        has_more = total_length > preview_length
        
        return FilePreviewResponse(
            file_id=file_id,
            original_filename=file_metadata.get("original_filename", "알 수 없는 파일"),
            file_type=file_type,
            preview_text=preview_text,
            preview_length=preview_length,
            total_length=total_length,
            has_more=has_more,
            preview_type=preview_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 미리보기 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview/chunks/{file_id}")
async def get_file_preview_with_chunks(file_id: str, chunk_count: int = 3):
    """청크 기반 파일 미리보기 - 처음 몇 개 청크의 내용"""
    try:
        db = await get_database()
        
        # 파일 기본 정보 조회 (새로운 구조에 맞게 수정)
        document = await db.documents.find_one(
            {"file_metadata.file_id": file_id},
            {"file_metadata": 1}
        )
        
        if not document:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        file_metadata = document.get("file_metadata", {})
        
        # 처음 몇 개 청크 조회
        chunks_cursor = db.chunks.find(
            {"file_id": file_id}
        ).sort("sequence", 1).limit(chunk_count)
        
        chunks = await chunks_cursor.to_list(None)
        
        if not chunks:
            raise HTTPException(status_code=404, detail="파일의 청크를 찾을 수 없습니다.")
        
        # 청크들의 텍스트를 합쳐서 미리보기 생성
        preview_texts = [chunk["text"] for chunk in chunks]
        preview_text = "\n\n--- 다음 섹션 ---\n\n".join(preview_texts)
        
        # 전체 청크 수 조회
        total_chunks = await db.chunks.count_documents({"file_id": file_id})
        
        return {
            "file_id": file_id,
            "original_filename": file_metadata.get("original_filename", "알 수 없는 파일"),
            "file_type": file_metadata.get("file_type", "unknown"),
            "preview_text": preview_text,
            "preview_chunks": len(chunks),
            "total_chunks": total_chunks,
            "has_more": total_chunks > len(chunks),
            "preview_type": "chunks"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"청크 기반 미리보기 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 