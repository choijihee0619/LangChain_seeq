"""
요약 API 라우터
MODIFIED 2024-12-20: 요약 캐시 관리 기능 추가
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from api.chains.summary_chain import SummaryChain
from database.connection import get_database
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

class SummaryRequest(BaseModel):
    """요약 요청 모델"""
    document_ids: Optional[List[str]] = None
    folder_id: Optional[str] = None
    summary_type: str = "brief"  # brief, detailed, bullets

class SummaryResponse(BaseModel):
    """요약 응답 모델"""
    summary: str
    document_count: int
    summary_type: str
    from_cache: Optional[bool] = False
    cache_created_at: Optional[str] = None

class CachedSummaryItem(BaseModel):
    """캐시된 요약 항목 모델"""
    cache_id: str
    summary_type: str
    summary_preview: str
    document_count: int
    created_at: str
    last_accessed_at: str

class CachedSummariesResponse(BaseModel):
    """캐시된 요약 목록 응답 모델"""
    cached_summaries: List[CachedSummaryItem]
    total_count: int

@router.post("/", response_model=SummaryResponse)
async def create_summary(request: SummaryRequest):
    """요약 생성 엔드포인트"""
    try:
        db = await get_database()
        summary_chain = SummaryChain(db)
        
        # 요약 생성
        result = await summary_chain.process(
            document_ids=request.document_ids,
            folder_id=request.folder_id,
            summary_type=request.summary_type
        )
        
        return SummaryResponse(
            summary=result["summary"],
            document_count=result["document_count"],
            summary_type=request.summary_type,
            from_cache=result.get("from_cache", False),
            cache_created_at=str(result.get("cache_created_at", ""))
        )
        
    except Exception as e:
        logger.error(f"요약 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cached", response_model=CachedSummariesResponse)
async def get_cached_summaries(folder_id: Optional[str] = None, limit: int = 10):
    """캐시된 요약 목록 조회 엔드포인트"""
    try:
        db = await get_database()
        summary_chain = SummaryChain(db)
        
        cached_summaries = await summary_chain.get_cached_summaries(folder_id, limit)
        
        return CachedSummariesResponse(
            cached_summaries=[
                CachedSummaryItem(
                    cache_id=item["cache_id"],
                    summary_type=item["summary_type"],
                    summary_preview=item["summary_preview"],
                    document_count=item["document_count"],
                    created_at=str(item["created_at"]),
                    last_accessed_at=str(item["last_accessed_at"])
                )
                for item in cached_summaries
            ],
            total_count=len(cached_summaries)
        )
        
    except Exception as e:
        logger.error(f"캐시된 요약 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cached/{cache_id}")
async def delete_summary_cache(cache_id: str):
    """요약 캐시 삭제 엔드포인트"""
    try:
        db = await get_database()
        summary_chain = SummaryChain(db)
        
        success = await summary_chain.delete_summary_cache(cache_id)
        
        if success:
            return {"success": True, "message": "요약 캐시가 삭제되었습니다."}
        else:
            raise HTTPException(status_code=404, detail="요약 캐시를 찾을 수 없습니다.")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"요약 캐시 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
