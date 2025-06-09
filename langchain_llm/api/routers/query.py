"""
질의응답 API 라우터 (AgentHub 통합 - 대화형 메모리 지원)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database.connection import get_database
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# 전역 AgentHub 인스턴스
_agent_hub = None

async def get_agent_hub():
    """AgentHub 싱글톤 인스턴스 반환"""
    global _agent_hub
    if _agent_hub is None:
        try:
            from seeq_langchain.agents import AgentHub
            db = await get_database()
            _agent_hub = AgentHub(db)
            await _agent_hub.initialize()
            logger.info("AgentHub 초기화 완료")
        except Exception as e:
            logger.error(f"AgentHub 초기화 실패: {e}")
            # Fallback: 기존 QueryChain 사용
            return None
    return _agent_hub

class QueryRequest(BaseModel):
    """질의 요청 모델"""
    query: str
    folder_id: Optional[str] = None
    top_k: int = 5
    include_sources: bool = True
    session_id: Optional[str] = None  # 세션 관리용

class QueryResponse(BaseModel):
    """질의 응답 모델"""
    answer: str
    sources: Optional[List[dict]] = None
    confidence: float
    agent_type: Optional[str] = None  # 사용된 에이전트 타입
    session_id: Optional[str] = None  # 세션 ID
    strategy: Optional[str] = None  # 응답 전략
    session_context: Optional[dict] = None  # 세션 컨텍스트

class SessionInfo(BaseModel):
    """세션 정보 모델"""
    session_id: str
    created_at: Optional[str] = None
    last_activity: Optional[str] = None
    message_count: int = 0
    has_history: bool = False

@router.post("/", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """질의 처리 엔드포인트 (향상된 AgentHub 활용)"""
    try:
        # AgentHub 사용 시도
        agent_hub = await get_agent_hub()
        
        if agent_hub:
            # AgentHub를 통한 처리
            logger.info(f"향상된 AgentHub로 질의 처리: '{request.query}'")
            
            # 컨텍스트 설정
            context = {}
            if request.folder_id and request.folder_id.strip() and request.folder_id not in ["string", "null"]:
                context["folder_id"] = request.folder_id.strip()
            if request.top_k:
                context["k"] = request.top_k
            
            # AgentHub를 통한 처리
            result = await agent_hub.process_query(
                query=request.query,
                session_id=request.session_id,
                agent_type="hybrid",
                context=context
            )
            
            if result.get("status") == "success":
                # 성공적인 AgentHub 결과 처리
                sources = result.get("sources", [])
                if not request.include_sources:
                    sources = None
                
                response = QueryResponse(
                    answer=result.get("answer", ""),
                    sources=sources,
                    confidence=result.get("confidence", 0.8),
                    agent_type=result.get("agent_type", "hybrid"),
                    session_id=result.get("session_id"),
                    strategy=result.get("strategy"),
                    session_context=result.get("session_context")
                )
                
                logger.info(f"향상된 AgentHub 처리 완료 ({result.get('strategy')} 전략)")
                return response
            else:
                # AgentHub 실패 시 Fallback
                logger.warning(f"AgentHub 처리 실패, Fallback 사용: {result.get('error')}")
                return await _fallback_query_processing(request)
        
        else:
            # AgentHub 초기화 실패 시 Fallback
            logger.warning("AgentHub 사용 불가, Fallback 사용")
            return await _fallback_query_processing(request)
            
    except Exception as e:
        logger.error(f"질의 처리 실패: {e}")
        # 최종 Fallback
        try:
            return await _fallback_query_processing(request)
        except:
            raise HTTPException(status_code=500, detail=str(e))

async def _fallback_query_processing(request: QueryRequest) -> QueryResponse:
    """Fallback: 기존 QueryChain 사용"""
    try:
        from api.chains.query_chain import QueryChain
        
        db = await get_database()
        query_chain = QueryChain(db)
        
        # 기존 방식으로 처리
        result = await query_chain.process(
            query=request.query,
            folder_id=request.folder_id,
            top_k=request.top_k
        )
        
        # 응답 생성
        response = QueryResponse(
            answer=result["answer"],
            sources=result.get("sources") if request.include_sources else None,
            confidence=result.get("confidence", 0.8),
            agent_type="legacy_chain",  # 기존 방식 표시
            session_id=request.session_id,
            strategy="legacy"
        )
        
        logger.info("Fallback QueryChain 처리 완료")
        return response
        
    except Exception as e:
        logger.error(f"Fallback 처리도 실패: {e}")
        raise HTTPException(status_code=500, detail=f"모든 처리 방식 실패: {str(e)}")

@router.get("/agent-info")
async def get_agent_info():
    """에이전트 정보 조회 엔드포인트"""
    try:
        agent_hub = await get_agent_hub()
        
        if agent_hub:
            capabilities = await agent_hub.get_agent_capabilities()
            return {
                "status": "available",
                "capabilities": capabilities
            }
        else:
            return {
                "status": "fallback_mode",
                "message": "AgentHub 사용 불가, 기존 QueryChain 사용 중"
            }
            
    except Exception as e:
        logger.error(f"에이전트 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def get_all_sessions():
    """모든 세션 조회 엔드포인트"""
    try:
        agent_hub = await get_agent_hub()
        
        if not agent_hub:
            raise HTTPException(status_code=503, detail="AgentHub 사용 불가")
        
        result = await agent_hub.get_all_sessions()
        return result
        
    except Exception as e:
        logger.error(f"세션 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """특정 세션 정보 조회 엔드포인트"""
    try:
        agent_hub = await get_agent_hub()
        
        if not agent_hub:
            raise HTTPException(status_code=503, detail="AgentHub 사용 불가")
        
        result = await agent_hub.get_session_info(session_id)
        return result
        
    except Exception as e:
        logger.error(f"세션 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """세션 삭제 엔드포인트"""
    try:
        agent_hub = await get_agent_hub()
        
        if not agent_hub:
            raise HTTPException(status_code=503, detail="AgentHub 사용 불가")
        
        result = await agent_hub.clear_session(session_id)
        return result
        
    except Exception as e:
        logger.error(f"세션 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/direct-tool")
async def run_direct_tool(tool_name: str, **kwargs):
    """도구 직접 실행 엔드포인트"""
    try:
        agent_hub = await get_agent_hub()
        
        if not agent_hub:
            raise HTTPException(status_code=503, detail="AgentHub 사용 불가")
        
        result = await agent_hub.run_tool_directly(tool_name, **kwargs)
        return result
        
    except Exception as e:
        logger.error(f"도구 직접 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/direct-chain")
async def run_direct_chain(chain_name: str, **kwargs):
    """체인 직접 실행 엔드포인트"""
    try:
        agent_hub = await get_agent_hub()
        
        if not agent_hub:
            raise HTTPException(status_code=503, detail="AgentHub 사용 불가")
        
        result = await agent_hub.run_chain_directly(chain_name, **kwargs)
        return result
        
    except Exception as e:
        logger.error(f"체인 직접 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
