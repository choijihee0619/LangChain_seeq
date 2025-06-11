"""
하이라이트 관리 API 라우터
문서별 텍스트 하이라이트 생성, 조회, 삭제 기능
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from database.connection import get_database
from database.operations import DatabaseOperations
from utils.logger import get_logger
import re

logger = get_logger(__name__)
router = APIRouter()

class HighlightCreateRequest(BaseModel):
    """하이라이트 생성 요청 모델"""
    file_id: str
    highlight_text: str
    start_offset: int
    end_offset: int
    color: str = "#ffff00"  # 기본 노란색
    note: Optional[str] = None

class HighlightUpdateRequest(BaseModel):
    """하이라이트 메모 업데이트 요청 모델"""
    note: Optional[str] = None
    color: Optional[str] = None

class HighlightResponse(BaseModel):
    """하이라이트 응답 모델"""
    highlight_id: str
    file_id: str
    folder_id: Optional[str] = None
    highlight_text: str
    start_offset: int
    end_offset: int
    color: str
    note: Optional[str] = None
    created_at: datetime
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    filename: Optional[str] = None

class HighlightListResponse(BaseModel):
    """하이라이트 목록 응답 모델"""
    highlights: List[HighlightResponse]
    total_count: int
    filename: Optional[str] = None

def validate_hex_color(color: str) -> bool:
    """hex 색상 코드 유효성 검증"""
    pattern = r'^#[0-9A-Fa-f]{6}$'
    return bool(re.match(pattern, color))

def extract_context(text: str, start: int, end: int, context_length: int = 50) -> tuple:
    """하이라이트 앞뒤 컨텍스트 추출"""
    context_start = max(0, start - context_length)
    context_end = min(len(text), end + context_length)
    
    context_before = text[context_start:start] if start > 0 else ""
    context_after = text[end:context_end] if end < len(text) else ""
    
    return context_before, context_after

@router.post("/", response_model=HighlightResponse)
async def create_highlight(request: HighlightCreateRequest):
    """하이라이트 생성 엔드포인트"""
    try:
        # 색상 코드 검증
        if not validate_hex_color(request.color):
            raise HTTPException(status_code=400, detail="유효하지 않은 색상 코드입니다. (#RRGGBB 형식 사용)")
        
        # offset 검증
        if request.start_offset < 0 or request.end_offset <= request.start_offset:
            raise HTTPException(status_code=400, detail="유효하지 않은 텍스트 위치입니다.")
        
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 문서 존재 확인 및 raw_text 조회
        document = await db_ops.find_one("documents", {"file_metadata.file_id": request.file_id})
        if not document:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
        
        raw_text = document.get("raw_text", "")
        folder_id = document.get("folder_id")
        filename = document.get("file_metadata", {}).get("original_filename")
        
        # offset 범위 검증
        if request.end_offset > len(raw_text):
            raise HTTPException(status_code=400, detail="텍스트 범위가 문서 길이를 초과합니다.")
        
        # 실제 하이라이트 텍스트 추출
        actual_highlight_text = raw_text[request.start_offset:request.end_offset]
        
        # 요청한 텍스트와 실제 텍스트 일치 확인 (공백 정규화)
        normalized_request = re.sub(r'\s+', ' ', request.highlight_text.strip())
        normalized_actual = re.sub(r'\s+', ' ', actual_highlight_text.strip())
        
        if normalized_request != normalized_actual:
            logger.warning(f"하이라이트 텍스트 불일치: 요청='{normalized_request}', 실제='{normalized_actual}'")
            # 경고는 하되 실제 텍스트로 저장 진행
        
        # 컨텍스트 추출
        context_before, context_after = extract_context(raw_text, request.start_offset, request.end_offset)
        
        # 중복 하이라이트 확인
        existing_highlight = await db_ops.find_one("highlights", {
            "file_id": request.file_id,
            "start_offset": request.start_offset,
            "end_offset": request.end_offset
        })
        
        if existing_highlight:
            raise HTTPException(status_code=409, detail="동일한 위치에 이미 하이라이트가 존재합니다.")
        
        # 하이라이트 생성
        highlight_doc = {
            "file_id": request.file_id,
            "folder_id": folder_id,
            "highlight_text": actual_highlight_text,  # 실제 텍스트 저장
            "start_offset": request.start_offset,
            "end_offset": request.end_offset,
            "color": request.color,
            "note": request.note,
            "context_before": context_before,
            "context_after": context_after,
            "created_at": datetime.utcnow()
        }
        
        highlight_id = await db_ops.insert_one("highlights", highlight_doc)
        
        return HighlightResponse(
            highlight_id=highlight_id,
            file_id=request.file_id,
            folder_id=folder_id,
            highlight_text=actual_highlight_text,
            start_offset=request.start_offset,
            end_offset=request.end_offset,
            color=request.color,
            note=request.note,
            created_at=highlight_doc["created_at"],
            context_before=context_before,
            context_after=context_after,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"하이라이트 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/file/{file_id}", response_model=HighlightListResponse)
async def get_file_highlights(file_id: str):
    """파일별 하이라이트 목록 조회 엔드포인트"""
    try:
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 파일 존재 확인
        document = await db_ops.find_one("documents", {"file_metadata.file_id": file_id})
        if not document:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
        
        filename = document.get("file_metadata", {}).get("original_filename")
        
        # 하이라이트 목록 조회 (offset 순)
        highlights = await db.highlights.find(
            {"file_id": file_id}
        ).sort("start_offset", 1).to_list(None)
        
        # 응답 형식으로 변환
        highlight_responses = []
        for highlight in highlights:
            highlight_responses.append(HighlightResponse(
                highlight_id=str(highlight["_id"]),
                file_id=highlight["file_id"],
                folder_id=highlight.get("folder_id"),
                highlight_text=highlight["highlight_text"],
                start_offset=highlight["start_offset"],
                end_offset=highlight["end_offset"],
                color=highlight["color"],
                note=highlight.get("note"),
                created_at=highlight["created_at"],
                context_before=highlight.get("context_before"),
                context_after=highlight.get("context_after"),
                filename=filename
            ))
        
        return HighlightListResponse(
            highlights=highlight_responses,
            total_count=len(highlight_responses),
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 하이라이트 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/folder/{folder_id}", response_model=HighlightListResponse)
async def get_folder_highlights(folder_id: str, limit: int = 100, skip: int = 0):
    """폴더별 하이라이트 목록 조회 엔드포인트"""
    try:
        if not ObjectId.is_valid(folder_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 폴더 ID입니다.")
        
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 폴더 존재 확인
        folder = await db_ops.find_one("folders", {"_id": ObjectId(folder_id)})
        if not folder:
            raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
        
        # 하이라이트 목록 조회 (최신순)
        highlights = await db.highlights.find(
            {"folder_id": folder_id}
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(None)
        
        # 응답 형식으로 변환 (파일명 정보 포함)
        highlight_responses = []
        for highlight in highlights:
            # 각 하이라이트의 파일명 조회
            document = await db_ops.find_one("documents", {"file_metadata.file_id": highlight["file_id"]})
            filename = document.get("file_metadata", {}).get("original_filename") if document else None
            
            highlight_responses.append(HighlightResponse(
                highlight_id=str(highlight["_id"]),
                file_id=highlight["file_id"],
                folder_id=highlight.get("folder_id"),
                highlight_text=highlight["highlight_text"],
                start_offset=highlight["start_offset"],
                end_offset=highlight["end_offset"],
                color=highlight["color"],
                note=highlight.get("note"),
                created_at=highlight["created_at"],
                context_before=highlight.get("context_before"),
                context_after=highlight.get("context_after"),
                filename=filename
            ))
        
        return HighlightListResponse(
            highlights=highlight_responses,
            total_count=len(highlight_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"폴더 하이라이트 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{highlight_id}", response_model=HighlightResponse)
async def update_highlight(highlight_id: str, request: HighlightUpdateRequest):
    """하이라이트 메모/색상 수정 엔드포인트"""
    try:
        if not ObjectId.is_valid(highlight_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 하이라이트 ID입니다.")
        
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 하이라이트 존재 확인
        highlight = await db_ops.find_one("highlights", {"_id": ObjectId(highlight_id)})
        if not highlight:
            raise HTTPException(status_code=404, detail="하이라이트를 찾을 수 없습니다.")
        
        # 업데이트할 필드 준비
        update_fields = {}
        
        if request.note is not None:
            update_fields["note"] = request.note
        
        if request.color is not None:
            if not validate_hex_color(request.color):
                raise HTTPException(status_code=400, detail="유효하지 않은 색상 코드입니다. (#RRGGBB 형식 사용)")
            update_fields["color"] = request.color
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="업데이트할 내용이 없습니다.")
        
        # 하이라이트 업데이트
        success = await db_ops.update_one(
            "highlights",
            {"_id": ObjectId(highlight_id)},
            {"$set": update_fields}
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="하이라이트 업데이트에 실패했습니다.")
        
        # 업데이트된 하이라이트 정보 반환
        updated_highlight = await db_ops.find_one("highlights", {"_id": ObjectId(highlight_id)})
        
        # 파일명 조회
        document = await db_ops.find_one("documents", {"file_metadata.file_id": updated_highlight["file_id"]})
        filename = document.get("file_metadata", {}).get("original_filename") if document else None
        
        return HighlightResponse(
            highlight_id=str(updated_highlight["_id"]),
            file_id=updated_highlight["file_id"],
            folder_id=updated_highlight.get("folder_id"),
            highlight_text=updated_highlight["highlight_text"],
            start_offset=updated_highlight["start_offset"],
            end_offset=updated_highlight["end_offset"],
            color=updated_highlight["color"],
            note=updated_highlight.get("note"),
            created_at=updated_highlight["created_at"],
            context_before=updated_highlight.get("context_before"),
            context_after=updated_highlight.get("context_after"),
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"하이라이트 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{highlight_id}")
async def delete_highlight(highlight_id: str):
    """하이라이트 삭제 엔드포인트"""
    try:
        if not ObjectId.is_valid(highlight_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 하이라이트 ID입니다.")
        
        db = await get_database()
        db_ops = DatabaseOperations(db)
        
        # 하이라이트 존재 확인
        highlight = await db_ops.find_one("highlights", {"_id": ObjectId(highlight_id)})
        if not highlight:
            raise HTTPException(status_code=404, detail="하이라이트를 찾을 수 없습니다.")
        
        # 하이라이트 삭제
        success = await db_ops.delete_one("highlights", {"_id": ObjectId(highlight_id)})
        
        if not success:
            raise HTTPException(status_code=500, detail="하이라이트 삭제에 실패했습니다.")
        
        return {
            "success": True,
            "message": f"하이라이트가 삭제되었습니다.",
            "deleted_highlight_id": highlight_id,
            "highlight_text": highlight["highlight_text"][:50] + "..." if len(highlight["highlight_text"]) > 50 else highlight["highlight_text"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"하이라이트 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 