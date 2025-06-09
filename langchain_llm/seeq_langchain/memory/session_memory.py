"""
Session Memory Manager
간단한 세션별 메모리 관리
"""
from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

class SessionMemoryManager:
    """세션 메모리 관리자"""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, session_id: str) -> bool:
        """새 세션 생성"""
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "messages": [],
                "context": {},
                "created_at": None
            }
            logger.info(f"새 세션 생성: {session_id}")
            return True
        return False
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """세션에 메시지 추가"""
        if session_id not in self._sessions:
            self.create_session(session_id)
        
        self._sessions[session_id]["messages"].append({
            "role": role,
            "content": content,
            "timestamp": None
        })
        return True
    
    def get_session_messages(self, session_id: str) -> list:
        """세션 메시지 반환"""
        return self._sessions.get(session_id, {}).get("messages", [])
    
    def clear_session(self, session_id: str) -> bool:
        """세션 삭제"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False 