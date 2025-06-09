"""
세션 관리 유틸리티
자동 세션 ID 생성 및 검증 기능
"""
import uuid
import time
from typing import Optional

def generate_session_id(prefix: str = "session") -> str:
    """
    자동으로 세션 ID 생성
    
    Args:
        prefix: 세션 ID 접두사 (기본값: "session")
        
    Returns:
        생성된 세션 ID (형식: "prefix_timestamp_randomhex")
    """
    timestamp = int(time.time())
    random_suffix = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{random_suffix}"

def is_valid_session_id(session_id: Optional[str]) -> bool:
    """
    유효한 세션 ID인지 검증
    
    Args:
        session_id: 검증할 세션 ID
        
    Returns:
        유효성 여부
    """
    if not session_id:
        return False
    
    # 공백이나 기본값 문자열 체크
    cleaned_id = session_id.strip()
    if not cleaned_id or cleaned_id in ["", "string", "null", "undefined"]:
        return False
    
    return True

def ensure_valid_session_id(session_id: Optional[str], prefix: str = "session") -> str:
    """
    세션 ID 유효성을 보장 (필요시 자동 생성)
    
    Args:
        session_id: 원본 세션 ID
        prefix: 생성시 사용할 접두사
        
    Returns:
        유효한 세션 ID (원본 또는 새로 생성된 것)
    """
    if is_valid_session_id(session_id):
        return session_id.strip()
    
    return generate_session_id(prefix)

def generate_query_session_id() -> str:
    """Query용 세션 ID 생성"""
    return generate_session_id("query_session")

def generate_quiz_session_id() -> str:
    """Quiz용 세션 ID 생성"""
    return generate_session_id("quiz_session") 