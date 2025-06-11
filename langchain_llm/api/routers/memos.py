"""
메모 관리 API 라우터
폴더별 메모 작성, 조회, 수정, 삭제 기능
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

class MemoCreateRequest(BaseModel):
    """메모 생성 요청 모델"""
    folder_id: str
    content: str
    title: Optional[str] = None  # None이면 자동 생성
    color: Optional[str] = "#ffffff"  # 기본 흰색
    tags: Optional[List[str]] = []

class MemoUpdateRequest(BaseModel):
    """메모 업데이트 요청 모델"""
    title: Optional[str] = None
    content: Optional[str] = None
    color: Optional[str] = None
    tags: Optional[List[str]] = None

class MemoResponse(BaseModel):
    """메모 응답 모델"""
    memo_id: str
    folder_id: str
    title: str
    content: str
    color: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    folder_title: Optional[str] = None  # 폴더명 포함

class MemoListResponse(BaseModel):
    """메모 목록 응답 모델"""
    memos: List[MemoResponse]
    total_count: int
    folder_title: Optional[str] = None

@router.post("/", response_model=MemoResponse)
async def create_memo(request: MemoCreateRequest):
    """메모 생성 엔드포인트"""
    try:
        # 폴더 존재 확인
        if not ObjectId.is_valid(request.folder_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 폴더 ID입니다.")
        
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        folder = await db_ops.find_one("folders", {"_id": ObjectId(request.folder_id)})
        if not folder:
            raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
        
        # 제목 결정 (사용자 입력 또는 자동 생성)
        if request.title and request.title.strip():
            final_title = request.title.strip()
        else:
            # 자동 제목 생성: "폴더명 번호"
            memo_count = await db.memos.count_documents({"folder_id": request.folder_id})
            final_title = f"{folder['title']} {memo_count + 1}"
        
        # 제목 길이 제한
        if len(final_title) > 100:
            final_title = final_title[:97] + "..."
        
        # 메모 생성
        memo_doc = {
            "folder_id": request.folder_id,
            "title": final_title,
            "content": request.content,
            "color": request.color,
            "tags": request.tags or [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        memo_id = await db_ops.insert_one("memos", memo_doc)
        
        # 생성된 메모 정보 반환
        return MemoResponse(
            memo_id=memo_id,
            folder_id=request.folder_id,
            title=final_title,
            content=request.content,
            color=request.color,
            tags=request.tags or [],
            created_at=memo_doc["created_at"],
            updated_at=memo_doc["updated_at"],
            folder_title=folder["title"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"메모 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/folder/{folder_id}", response_model=MemoListResponse)
async def get_folder_memos(folder_id: str, limit: int = 50, skip: int = 0):
    """폴더별 메모 목록 조회 엔드포인트"""
    try:
        if not ObjectId.is_valid(folder_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 폴더 ID입니다.")
        
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 폴더 존재 확인
        folder = await db_ops.find_one("folders", {"_id": ObjectId(folder_id)})
        if not folder:
            raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
        
        # 메모 목록 조회 (최신순)
        memos = await db.memos.find(
            {"folder_id": folder_id}
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(None)
        
        # 응답 형식으로 변환
        memo_responses = []
        for memo in memos:
            memo_responses.append(MemoResponse(
                memo_id=str(memo["_id"]),
                folder_id=memo["folder_id"],
                title=memo["title"],
                content=memo["content"],
                color=memo.get("color", "#ffffff"),
                tags=memo.get("tags", []),
                created_at=memo["created_at"],
                updated_at=memo["updated_at"],
                folder_title=folder["title"]
            ))
        
        return MemoListResponse(
            memos=memo_responses,
            total_count=len(memo_responses),
            folder_title=folder["title"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"폴더 메모 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{memo_id}", response_model=MemoResponse)
async def get_memo(memo_id: str):
    """특정 메모 조회 엔드포인트"""
    try:
        if not ObjectId.is_valid(memo_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 메모 ID입니다.")
        
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 메모 조회
        memo = await db_ops.find_one("memos", {"_id": ObjectId(memo_id)})
        if not memo:
            raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다.")
        
        # 폴더 정보 조회
        folder = await db_ops.find_one("folders", {"_id": ObjectId(memo["folder_id"])})
        folder_title = folder["title"] if folder else None
        
        return MemoResponse(
            memo_id=str(memo["_id"]),
            folder_id=memo["folder_id"],
            title=memo["title"],
            content=memo["content"],
            color=memo.get("color", "#ffffff"),
            tags=memo.get("tags", []),
            created_at=memo["created_at"],
            updated_at=memo["updated_at"],
            folder_title=folder_title
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"메모 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{memo_id}", response_model=MemoResponse)
async def update_memo(memo_id: str, request: MemoUpdateRequest):
    """메모 수정 엔드포인트"""
    try:
        if not ObjectId.is_valid(memo_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 메모 ID입니다.")
        
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 메모 존재 확인
        memo = await db_ops.find_one("memos", {"_id": ObjectId(memo_id)})
        if not memo:
            raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다.")
        
        # 업데이트할 필드 준비
        update_fields = {"updated_at": datetime.utcnow()}
        
        if request.title is not None:
            title = request.title.strip()
            if len(title) > 100:
                title = title[:97] + "..."
            update_fields["title"] = title
        
        if request.content is not None:
            update_fields["content"] = request.content
        
        if request.color is not None:
            update_fields["color"] = request.color
        
        if request.tags is not None:
            update_fields["tags"] = request.tags
        
        if len(update_fields) == 1:  # updated_at만 있으면
            raise HTTPException(status_code=400, detail="업데이트할 내용이 없습니다.")
        
        # 메모 업데이트
        success = await db_ops.update_one(
            "memos",
            {"_id": ObjectId(memo_id)},
            {"$set": update_fields}
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="메모 업데이트에 실패했습니다.")
        
        # 업데이트된 메모 정보 반환
        updated_memo = await db_ops.find_one("memos", {"_id": ObjectId(memo_id)})
        
        # 폴더 정보 조회
        folder = await db_ops.find_one("folders", {"_id": ObjectId(updated_memo["folder_id"])})
        folder_title = folder["title"] if folder else None
        
        return MemoResponse(
            memo_id=str(updated_memo["_id"]),
            folder_id=updated_memo["folder_id"],
            title=updated_memo["title"],
            content=updated_memo["content"],
            color=updated_memo.get("color", "#ffffff"),
            tags=updated_memo.get("tags", []),
            created_at=updated_memo["created_at"],
            updated_at=updated_memo["updated_at"],
            folder_title=folder_title
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"메모 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{memo_id}")
async def delete_memo(memo_id: str):
    """메모 삭제 엔드포인트"""
    try:
        if not ObjectId.is_valid(memo_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 메모 ID입니다.")
        
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 메모 존재 확인
        memo = await db_ops.find_one("memos", {"_id": ObjectId(memo_id)})
        if not memo:
            raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다.")
        
        # 메모 삭제
        success = await db_ops.delete_one("memos", {"_id": ObjectId(memo_id)})
        
        if not success:
            raise HTTPException(status_code=500, detail="메모 삭제에 실패했습니다.")
        
        return {
            "success": True,
            "message": f"메모 '{memo['title']}'가 삭제되었습니다.",
            "deleted_memo_id": memo_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"메모 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 