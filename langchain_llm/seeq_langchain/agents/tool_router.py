"""
Tool Router
도구 라우팅 관리
"""
from typing import Dict, Any, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

class ToolRouter:
    """도구 라우터"""
    
    def __init__(self, tool_registry):
        self.tool_registry = tool_registry
    
    async def route_request(self, query: str, context: Optional[Dict] = None) -> List[str]:
        """요청을 적절한 도구로 라우팅"""
        tools_to_use = []
        
        query_lower = query.lower()
        
        # 간단한 키워드 기반 라우팅
        if any(keyword in query_lower for keyword in ["검색", "찾아", "찾기", "search"]):
            tools_to_use.append("vector_search")
        
        if any(keyword in query_lower for keyword in ["요약", "정리", "summary"]):
            tools_to_use.append("document_summary")
        
        if any(keyword in query_lower for keyword in ["퀴즈", "문제", "quiz"]):
            tools_to_use.append("quiz_generator")
        
        if any(keyword in query_lower for keyword in ["추천", "recommend"]):
            tools_to_use.append("content_recommend")
        
        if any(keyword in query_lower for keyword in ["유튜브", "youtube", "비디오"]):
            tools_to_use.append("youtube_search")
        
        if any(keyword in query_lower for keyword in ["파일", "폴더", "file", "folder"]):
            tools_to_use.append("file_management")
        
        # 기본값: 벡터 검색
        if not tools_to_use:
            tools_to_use.append("vector_search")
        
        logger.info(f"도구 라우팅: '{query}' -> {tools_to_use}")
        return tools_to_use 