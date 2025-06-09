"""
Tool Registry
모든 LangChain Tools의 중앙 관리자
"""
from typing import List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_core.tools import Tool

from utils.logger import get_logger

logger = get_logger(__name__)

class ToolRegistry:
    """Tool 레지스트리 관리자"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._tools: Dict[str, Tool] = {}
        self._initialized = False
    
    async def initialize(self):
        """모든 도구 초기화"""
        if self._initialized:
            return
        
        try:
            from .vector_search_tool import VectorSearchTool
            from .summary_tool import SummaryTool
            from .quiz_tool import QuizTool
            from .recommend_tool import RecommendTool
            from .youtube_tool import YouTubeTool
            from .file_tool import FileTool
            
            # 도구 인스턴스 생성
            vector_tool = VectorSearchTool(self.db)
            summary_tool = SummaryTool(self.db)
            quiz_tool = QuizTool(self.db)
            recommend_tool = RecommendTool(self.db)
            youtube_tool = YouTubeTool()
            file_tool = FileTool(self.db)
            
            # 도구 등록
            self._tools.update({
                "vector_search": await vector_tool.create_tool(),
                "document_summary": await summary_tool.create_tool(),
                "quiz_generator": await quiz_tool.create_tool(),
                "content_recommend": await recommend_tool.create_tool(),
                "youtube_search": await youtube_tool.create_tool(),
                "file_management": await file_tool.create_tool()
            })
            
            self._initialized = True
            logger.info(f"Tool Registry 초기화 완료: {len(self._tools)}개 도구 등록")
            
        except Exception as e:
            logger.error(f"Tool Registry 초기화 실패: {e}")
            raise
    
    def get_tool(self, tool_name: str) -> Tool:
        """특정 도구 반환"""
        if not self._initialized:
            raise RuntimeError("Tool Registry가 초기화되지 않았습니다.")
        
        if tool_name not in self._tools:
            raise ValueError(f"도구 '{tool_name}'를 찾을 수 없습니다.")
        
        return self._tools[tool_name]
    
    def get_all_tools(self) -> List[Tool]:
        """모든 도구 반환"""
        if not self._initialized:
            raise RuntimeError("Tool Registry가 초기화되지 않았습니다.")
        
        return list(self._tools.values())
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """카테고리별 도구 반환"""
        if not self._initialized:
            raise RuntimeError("Tool Registry가 초기화되지 않았습니다.")
        
        category_mapping = {
            "search": ["vector_search"],
            "analysis": ["document_summary", "quiz_generator"],
            "recommendation": ["content_recommend", "youtube_search"],
            "management": ["file_management"]
        }
        
        tool_names = category_mapping.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def list_available_tools(self) -> Dict[str, str]:
        """사용 가능한 도구 목록 반환"""
        if not self._initialized:
            return {}
        
        return {
            name: tool.description 
            for name, tool in self._tools.items()
        }
    
    async def add_custom_tool(self, name: str, tool: Tool):
        """사용자 정의 도구 추가"""
        if name in self._tools:
            logger.warning(f"도구 '{name}'가 이미 존재합니다. 덮어씁니다.")
        
        self._tools[name] = tool
        logger.info(f"사용자 정의 도구 '{name}' 추가 완료")
    
    def remove_tool(self, name: str) -> bool:
        """도구 제거"""
        if name in self._tools:
            del self._tools[name]
            logger.info(f"도구 '{name}' 제거 완료")
            return True
        return False 