"""
질의응답 API 라우터
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from api.chains.query_chain import QueryChain
from database.connection import get_database
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

class QueryRequest(BaseModel):
    """질의 요청 모델"""
    query: str
    folder_id: Optional[str] = None
    top_k: int = 5
    include_sources: bool = True

class QueryResponse(BaseModel):
    """질의 응답 모델"""
    answer: str
    sources: Optional[List[dict]] = None
    confidence: float

@router.post("/", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """질의 처리 엔드포인트"""
    try:
        db = await get_database()
        query_chain = QueryChain(db)
        
        # 질의 처리
        result = await query_chain.process(
            query=request.query,
            folder_id=request.folder_id,
            top_k=request.top_k
        )
        
        # 응답 생성
        response = QueryResponse(
            answer=result["answer"],
            sources=result.get("sources") if request.include_sources else None,
            confidence=result.get("confidence", 0.9)
        )
        
        return response
        
    except Exception as e:
        logger.error(f"질의 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
