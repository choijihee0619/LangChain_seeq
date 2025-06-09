"""
YouTube Tool
YouTube 검색을 위한 LangChain Tool
"""
import json
from typing import Optional
from langchain_core.tools import Tool

from utils.logger import get_logger

logger = get_logger(__name__)

class YouTubeTool:
    """YouTube 검색 도구"""
    
    def __init__(self):
        pass
    
    async def _search_youtube(self, query: str, max_results: int = 5) -> str:
        """YouTube 검색"""
        try:
            from api.routers.youtube import search_youtube_videos
            
            results = await search_youtube_videos(query, max_results)
            
            return json.dumps({
                "status": "success",
                "query": query,
                "videos": results.get("videos", []),
                "total_results": len(results.get("videos", []))
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"YouTube 검색 실패: {e}")
            return json.dumps({
                "status": "error",
                "message": f"YouTube 검색 중 오류가 발생했습니다: {str(e)}"
            }, ensure_ascii=False)
    
    async def create_tool(self) -> Tool:
        """LangChain Tool 생성"""
        
        async def youtube_wrapper(query: str, max_results: int = 5) -> str:
            return await self._search_youtube(query, min(max_results, 10))
        
        tool = Tool(
            name="youtube_search",
            description="""YouTube에서 비디오를 검색하는 도구입니다.
사용법: youtube_search(query="검색 키워드", max_results=5)
- query: 검색할 키워드 (필수)
- max_results: 반환할 최대 결과 수 (1-10개)

예시: youtube_search(query="파이썬 프로그래밍", max_results=3)""",
            func=youtube_wrapper,
            return_direct=False
        )
        
        return tool 