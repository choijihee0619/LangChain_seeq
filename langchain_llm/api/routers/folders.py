"""
폴더 관리 API 라우터
정규화된 폴더 시스템 - folders 컬렉션 중심 관리
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from database.connection import get_database
from database.operations import DatabaseOperations
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

class FolderCreateRequest(BaseModel):
    """폴더 생성 요청 모델"""
    title: str
    folder_type: str = "library"
    cover_image_url: Optional[str] = None

class FolderUpdateRequest(BaseModel):
    """폴더 업데이트 요청 모델"""
    title: Optional[str] = None
    folder_type: Optional[str] = None
    cover_image_url: Optional[str] = None

class FolderResponse(BaseModel):
    """폴더 응답 모델"""
    folder_id: str  # ObjectId를 문자열로 변환
    title: str
    folder_type: str
    created_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    cover_image_url: Optional[str] = None
    document_count: int = 0
    file_count: int = 0

class FolderListResponse(BaseModel):
    """폴더 목록 응답 모델"""
    folders: List[FolderResponse]
    total_count: int

@router.post("/", response_model=FolderResponse)
async def create_folder(request: FolderCreateRequest):
    """폴더 생성 엔드포인트"""
    try:
        # 입력 검증
        if not request.title or len(request.title.strip()) == 0:
            raise HTTPException(status_code=400, detail="폴더명은 필수입니다.")
        
        if len(request.title) > 100:
            raise HTTPException(status_code=400, detail="폴더명은 100자를 초과할 수 없습니다.")
        
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 중복 폴더명 확인
        existing_folder = await db_ops.find_one("folders", {"title": request.title.strip()})
        if existing_folder:
            raise HTTPException(status_code=400, detail="이미 존재하는 폴더명입니다.")
        
        # 폴더 생성
        folder_id = await db_ops.create_folder(
            title=request.title.strip(),
            folder_type=request.folder_type,
            cover_image_url=request.cover_image_url
        )
        
        # 생성된 폴더 정보 반환
        folder_doc = await db_ops.find_one("folders", {"_id": ObjectId(folder_id)})
        
        return FolderResponse(
            folder_id=str(folder_doc["_id"]),
            title=folder_doc["title"],
            folder_type=folder_doc["folder_type"],
            created_at=folder_doc["created_at"],
            last_accessed_at=folder_doc["last_accessed_at"],
            cover_image_url=folder_doc.get("cover_image_url"),
            document_count=0,
            file_count=0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"폴더 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=FolderListResponse)
async def list_folders(limit: int = 50, skip: int = 0):
    """폴더 목록 조회 엔드포인트"""
    try:
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 폴더 목록 조회 (최근 접근 순)
        folders = await db_ops.find_many(
            "folders", 
            {}, 
            limit=limit, 
            skip=skip
        )
        
        # 각 폴더의 문서 및 파일 수 계산
        folder_responses = []
        for folder in sorted(folders, key=lambda x: x.get('last_accessed_at', x.get('created_at', datetime.utcnow())), reverse=True):
            folder_id_str = str(folder["_id"])
            
            # 문서 수 (documents 컬렉션에서)
            doc_count = await db.documents.count_documents({"folder_id": folder_id_str})
            
            # 고유 파일 수 계산
            pipeline = [
                {"$match": {"folder_id": folder_id_str}},
                {"$group": {"_id": "$file_metadata.file_id"}},
                {"$count": "unique_files"}
            ]
            file_count_result = await db.documents.aggregate(pipeline).to_list(1)
            file_count = file_count_result[0]["unique_files"] if file_count_result else 0
            
            folder_responses.append(FolderResponse(
                folder_id=folder_id_str,
                title=folder["title"],
                folder_type=folder["folder_type"],
                created_at=folder.get("created_at"),
                last_accessed_at=folder.get("last_accessed_at"),
                cover_image_url=folder.get("cover_image_url"),
                document_count=doc_count,
                file_count=file_count
            ))
        
        return FolderListResponse(
            folders=folder_responses,
            total_count=len(folder_responses)
        )
        
    except Exception as e:
        logger.error(f"폴더 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(folder_id: str):
    """특정 폴더 조회 엔드포인트"""
    try:
        if not ObjectId.is_valid(folder_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 폴더 ID입니다.")
        
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 폴더 존재 확인
        folder = await db_ops.find_one("folders", {"_id": ObjectId(folder_id)})
        if not folder:
            raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
        
        # 폴더 접근 시간 업데이트
        await db_ops.update_folder_access(folder_id)
        
        # 문서 및 파일 수 계산
        doc_count = await db.documents.count_documents({"folder_id": folder_id})
        
        pipeline = [
            {"$match": {"folder_id": folder_id}},
            {"$group": {"_id": "$file_metadata.file_id"}},
            {"$count": "unique_files"}
        ]
        file_count_result = await db.documents.aggregate(pipeline).to_list(1)
        file_count = file_count_result[0]["unique_files"] if file_count_result else 0
        
        return FolderResponse(
            folder_id=str(folder["_id"]),
            title=folder["title"],
            folder_type=folder["folder_type"],
            created_at=folder.get("created_at"),
            last_accessed_at=folder.get("last_accessed_at"),
            cover_image_url=folder.get("cover_image_url"),
            document_count=doc_count,
            file_count=file_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"폴더 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(folder_id: str, request: FolderUpdateRequest):
    """폴더 정보 업데이트 엔드포인트"""
    try:
        if not ObjectId.is_valid(folder_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 폴더 ID입니다.")
        
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 폴더 존재 확인
        folder = await db_ops.find_one("folders", {"_id": ObjectId(folder_id)})
        if not folder:
            raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
        
        # 업데이트할 필드 준비
        update_fields = {}
        if request.title is not None and request.title.strip():
            if len(request.title) > 100:
                raise HTTPException(status_code=400, detail="폴더명은 100자를 초과할 수 없습니다.")
            
            # 중복 폴더명 확인 (자기 자신 제외)
            existing_folder = await db_ops.find_one("folders", {
                "title": request.title.strip(),
                "_id": {"$ne": ObjectId(folder_id)}
            })
            if existing_folder:
                raise HTTPException(status_code=400, detail="이미 존재하는 폴더명입니다.")
            
            update_fields["title"] = request.title.strip()
        
        if request.folder_type is not None:
            update_fields["folder_type"] = request.folder_type
        
        if request.cover_image_url is not None:
            update_fields["cover_image_url"] = request.cover_image_url
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="업데이트할 내용이 없습니다.")
        
        # 폴더 업데이트
        success = await db_ops.update_one(
            "folders",
            {"_id": ObjectId(folder_id)},
            {"$set": update_fields}
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="폴더 업데이트에 실패했습니다.")
        
        # 업데이트된 폴더 정보 반환
        updated_folder = await db_ops.find_one("folders", {"_id": ObjectId(folder_id)})
        
        # 문서 및 파일 수 계산
        doc_count = await db.documents.count_documents({"folder_id": folder_id})
        
        pipeline = [
            {"$match": {"folder_id": folder_id}},
            {"$group": {"_id": "$file_metadata.file_id"}},
            {"$count": "unique_files"}
        ]
        file_count_result = await db.documents.aggregate(pipeline).to_list(1)
        file_count = file_count_result[0]["unique_files"] if file_count_result else 0
        
        return FolderResponse(
            folder_id=str(updated_folder["_id"]),
            title=updated_folder["title"],
            folder_type=updated_folder["folder_type"],
            created_at=updated_folder.get("created_at"),
            last_accessed_at=updated_folder.get("last_accessed_at"),
            cover_image_url=updated_folder.get("cover_image_url"),
            document_count=doc_count,
            file_count=file_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"폴더 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{folder_id}")
async def delete_folder(folder_id: str, force: bool = False):
    """폴더 삭제 엔드포인트"""
    try:
        if not ObjectId.is_valid(folder_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 폴더 ID입니다.")
        
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 폴더 존재 확인
        folder = await db_ops.find_one("folders", {"_id": ObjectId(folder_id)})
        if not folder:
            raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
        
        # 폴더 내 문서 확인
        doc_count = await db.documents.count_documents({"folder_id": folder_id})
        
        if doc_count > 0 and not force:
            raise HTTPException(
                status_code=400, 
                detail=f"폴더에 {doc_count}개의 문서가 있습니다. force=true로 강제 삭제하거나 문서를 먼저 삭제해주세요."
            )
        
        # 폴더 내 모든 데이터 삭제 (cascade delete)
        if force and doc_count > 0:
            logger.info(f"폴더 강제 삭제: {folder_id}, 문서 {doc_count}개 함께 삭제")
            
            # 관련 데이터 모두 삭제
            await db.documents.delete_many({"folder_id": folder_id})
            await db.chunks.delete_many({"folder_id": folder_id})
            await db.summaries.delete_many({"folder_id": folder_id})
            await db.qapairs.delete_many({"folder_id": folder_id})
            await db.recommendations.delete_many({"folder_id": folder_id})
            await db.labels.delete_many({"folder_id": folder_id})
            await db.memos.delete_many({"folder_id": folder_id})
            await db.highlights.delete_many({"folder_id": folder_id})
        
        # 폴더 삭제
        success = await db_ops.delete_one("folders", {"_id": ObjectId(folder_id)})
        
        if not success:
            raise HTTPException(status_code=500, detail="폴더 삭제에 실패했습니다.")
        
        return {
            "success": True,
            "message": f"폴더 '{folder['title']}'가 삭제되었습니다.",
            "deleted_documents": doc_count if force else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"폴더 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 