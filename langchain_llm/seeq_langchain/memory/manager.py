"""
Memory Manager
메모리 시스템 중앙 관리자 - 현대적인 대화 기록 관리
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class MemoryManager:
    """메모리 관리자 - 현대적인 대화 기록 관리"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_MODEL,
            temperature=0.1
        )
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    async def initialize(self):
        """메모리 시스템 초기화"""
        if self._initialized:
            return
        
        try:
            # 기존 세션 로드
            await self._load_existing_sessions()
            self._initialized = True
            logger.info("Memory Manager 초기화 완료")
            
        except Exception as e:
            logger.error(f"Memory Manager 초기화 실패: {e}")
            raise
    
    async def _load_existing_sessions(self):
        """기존 세션들을 데이터베이스에서 로드"""
        try:
            collection = self.db.chat_sessions
            sessions = await collection.find({}).to_list(length=None)
            
            for session_doc in sessions:
                session_id = session_doc["session_id"]
                self._sessions[session_id] = {
                    "messages": [],  # 직접 메시지 관리
                    "created_at": session_doc.get("created_at", datetime.now()),
                    "last_activity": session_doc.get("last_activity", datetime.now()),
                    "message_count": session_doc.get("message_count", 0)
                }
                
                # 채팅 기록 복원
                if "messages" in session_doc:
                    for msg in session_doc["messages"]:
                        if msg["role"] == "human":
                            self._sessions[session_id]["messages"].append(
                                HumanMessage(content=msg["content"])
                            )
                        elif msg["role"] == "ai":
                            self._sessions[session_id]["messages"].append(
                                AIMessage(content=msg["content"])
                            )
            
            logger.info(f"기존 세션 {len(self._sessions)}개 로드 완료")
            
        except Exception as e:
            logger.warning(f"기존 세션 로드 실패: {e}")
    
    def get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        """세션 가져오기 또는 생성"""
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "messages": [],
                "created_at": datetime.now(),
                "last_activity": datetime.now(),
                "message_count": 0
            }
            logger.info(f"새 세션 생성: {session_id}")
        
        return self._sessions[session_id]
    
    async def add_message(self, session_id: str, human_message: str, ai_message: str):
        """대화 메시지 추가"""
        session = self.get_or_create_session(session_id)
        
        # 메시지 추가
        session["messages"].append(HumanMessage(content=human_message))
        session["messages"].append(AIMessage(content=ai_message))
        
        # 세션 정보 업데이트
        session["last_activity"] = datetime.now()
        session["message_count"] += 1
        
        # 메시지 제한 (최근 20개 메시지만 유지)
        if len(session["messages"]) > 20:
            session["messages"] = session["messages"][-20:]
        
        # 데이터베이스에 저장
        await self._save_session_to_db(session_id, human_message, ai_message)
        
        logger.debug(f"세션 {session_id}에 메시지 추가")
    
    async def _save_session_to_db(self, session_id: str, human_message: str, ai_message: str):
        """세션을 데이터베이스에 저장"""
        try:
            collection = self.db.chat_sessions
            session = self._sessions[session_id]
            
            # 세션 문서 업데이트 또는 생성
            await collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "session_id": session_id,
                        "last_activity": session["last_activity"],
                        "message_count": session["message_count"]
                    },
                    "$setOnInsert": {
                        "created_at": session["created_at"]
                    },
                    "$push": {
                        "messages": {
                            "$each": [
                                {
                                    "role": "human",
                                    "content": human_message,
                                    "timestamp": datetime.now()
                                },
                                {
                                    "role": "ai", 
                                    "content": ai_message,
                                    "timestamp": datetime.now()
                                }
                            ]
                        }
                    }
                },
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"세션 저장 실패: {e}")
    
    def get_conversation_history(self, session_id: str, memory_type: str = "buffer") -> List:
        """대화 기록 가져오기"""
        if session_id not in self._sessions:
            return []
        
        session = self._sessions[session_id]
        
        if memory_type == "buffer":
            return session["messages"]
        elif memory_type == "summary":
            # 요약된 대화 기록 반환 (향후 구현)
            return session["messages"][-10:]  # 최근 10개만
        
        return []
    
    def get_conversation_summary(self, session_id: str) -> str:
        """대화 요약 생성"""
        if session_id not in self._sessions:
            return ""
        
        messages = self._sessions[session_id]["messages"]
        if not messages:
            return ""
        
        # 간단한 요약 (향후 LLM을 사용한 요약으로 확장 가능)
        human_messages = [msg.content for msg in messages if isinstance(msg, HumanMessage)]
        
        if len(human_messages) > 3:
            return f"이 대화에서는 {len(human_messages)}개의 주제에 대해 논의했습니다."
        else:
            topics = ", ".join(human_messages[:3])
            return f"주요 질문: {topics}"
    
    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """세션 컨텍스트 정보 반환"""
        if session_id not in self._sessions:
            return {}
        
        session = self._sessions[session_id]
        return {
            "session_id": session_id,
            "created_at": session["created_at"],
            "last_activity": session["last_activity"],
            "message_count": session["message_count"],
            "has_history": session["message_count"] > 0,
            "conversation_summary": self.get_conversation_summary(session_id)
        }
    
    async def clear_session(self, session_id: str):
        """세션 삭제"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            
            # 데이터베이스에서도 삭제
            try:
                await self.db.chat_sessions.delete_one({"session_id": session_id})
                logger.info(f"세션 {session_id} 삭제 완료")
            except Exception as e:
                logger.error(f"세션 삭제 실패: {e}")
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """모든 세션 정보 반환"""
        return {
            session_id: {
                "created_at": session["created_at"],
                "last_activity": session["last_activity"],
                "message_count": session["message_count"],
                "conversation_summary": self.get_conversation_summary(session_id)
            }
            for session_id, session in self._sessions.items()
        } 