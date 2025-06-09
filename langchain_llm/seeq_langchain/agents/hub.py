"""
Agent Hub
중앙 에이전트 관리자 - 대화형 메모리와 하이브리드 응답 지원
"""
from typing import Dict, Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_openai import ChatOpenAI

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class AgentHub:
    """에이전트 허브 - 중앙 관리자"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            temperature=0.1
        )
        self._memory_manager = None
        self._hybrid_responder = None
        self._initialized = False
    
    async def initialize(self):
        """에이전트 허브 초기화"""
        if self._initialized:
            return
        
        try:
            # 메모리 매니저 초기화
            from ..memory import MemoryManager
            self._memory_manager = MemoryManager(self.db)
            await self._memory_manager.initialize()
            
            # 하이브리드 응답기 초기화
            from .hybrid_responder import HybridResponder
            self._hybrid_responder = HybridResponder(self.db)
            await self._hybrid_responder.initialize()
            
            self._initialized = True
            logger.info("Agent Hub 초기화 완료 (대화형 메모리 + 하이브리드 응답 지원)")
            
        except Exception as e:
            logger.error(f"Agent Hub 초기화 실패: {e}")
            # 초기화 실패해도 계속 진행
            self._initialized = True
    
    async def process_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        agent_type: str = "hybrid",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """향상된 쿼리 처리 - 대화형 메모리와 하이브리드 응답"""
        try:
            if not self._initialized:
                raise RuntimeError("Agent Hub가 초기화되지 않았습니다.")
            
            logger.info(f"향상된 쿼리 처리 시작: '{query}' (session: {session_id})")
            
            # 세션 ID가 없으면 생성
            if not session_id:
                import uuid
                session_id = f"session_{uuid.uuid4().hex[:8]}"
            
            # 대화 기록 가져오기
            conversation_history = []
            if self._memory_manager and session_id:
                conversation_history = self._memory_manager.get_conversation_history(session_id, "buffer")
            
            # 컨텍스트에서 검색 옵션 추출
            folder_id = context.get("folder_id") if context else None
            top_k = context.get("k", 5) if context else 5
            
            # 하이브리드 응답 생성
            if self._hybrid_responder:
                response_data = await self._hybrid_responder.generate_response(
                    query=query,
                    session_id=session_id,
                    conversation_history=conversation_history
                )
                
                answer = response_data["answer"]
                sources = response_data.get("sources", [])
                strategy = response_data.get("strategy", "hybrid")
                confidence = response_data.get("confidence", 0.8)
                
            else:
                # Fallback: 간단한 응답
                answer = f"AgentHub에서 처리된 응답: {query}에 대한 답변을 준비 중입니다."
                sources = []
                strategy = "fallback"
                confidence = 0.5
            
            # 메모리에 대화 저장
            if self._memory_manager and session_id:
                await self._memory_manager.add_message(session_id, query, answer)
            
            # 응답 구성
            response = {
                "status": "success",
                "query": query,
                "answer": answer,
                "agent_type": f"hybrid_{strategy}",
                "session_id": session_id,
                "sources": sources,
                "confidence": confidence,
                "strategy": strategy,
                "session_context": self._get_session_context(session_id) if self._memory_manager else {}
            }
            
            logger.info(f"향상된 쿼리 처리 완료: {strategy} 전략 사용")
            return response
            
        except Exception as e:
            logger.error(f"향상된 쿼리 처리 실패: {e}")
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "agent_type": "error",
                "session_id": session_id
            }
    
    def _get_session_context(self, session_id: str) -> Dict[str, Any]:
        """세션 컨텍스트 정보 반환"""
        if self._memory_manager:
            return self._memory_manager.get_session_context(session_id)
        return {}
    
    async def get_agent_capabilities(self) -> Dict[str, Any]:
        """에이전트 기능 정보 반환"""
        capabilities = {
            "memory_management": self._memory_manager is not None,
            "hybrid_response": self._hybrid_responder is not None,
            "response_strategies": ["vector_based", "hybrid", "general_knowledge"],
            "memory_types": ["buffer", "summary"],
            "features": [
                "대화형 메모리",
                "하이브리드 응답 (벡터DB + 일반지식)",
                "세션별 컨텍스트 관리",
                "자동 응답 전략 선택"
            ]
        }
        
        return capabilities
    
    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """특정 세션 정보 반환"""
        if not self._memory_manager:
            return {"error": "메모리 매니저 사용 불가"}
        
        return self._memory_manager.get_session_context(session_id)
    
    async def clear_session(self, session_id: str) -> Dict[str, Any]:
        """세션 삭제"""
        if not self._memory_manager:
            return {"success": False, "error": "메모리 매니저 사용 불가"}
        
        try:
            await self._memory_manager.clear_session(session_id)
            return {"success": True, "message": f"세션 {session_id} 삭제 완료"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_all_sessions(self) -> Dict[str, Any]:
        """모든 세션 정보 반환"""
        if not self._memory_manager:
            return {"sessions": {}, "error": "메모리 매니저 사용 불가"}
        
        sessions = self._memory_manager.get_all_sessions()
        return {"sessions": sessions, "total_count": len(sessions)}
    
    async def run_tool_directly(
        self,
        tool_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """도구 직접 실행 (향후 확장용)"""
        return {
            "status": "not_implemented",
            "tool": tool_name,
            "message": "도구 직접 실행 기능은 향후 구현 예정입니다."
        }
    
    async def run_chain_directly(
        self,
        chain_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """체인 직접 실행 (향후 확장용)"""
        return {
            "status": "not_implemented",
            "chain": chain_name,
            "message": "체인 직접 실행 기능은 향후 구현 예정입니다."
        } 