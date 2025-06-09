"""
Recommend Tool
콘텐츠 추천을 위한 LangChain Tool
"""
import json
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_core.tools import Tool

from utils.logger import get_logger

logger = get_logger(__name__)

class RecommendTool:
    """콘텐츠 추천 도구"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def _generate_recommendations(self, folder_id: Optional[str] = None,
                                      keywords: Optional[str] = None) -> str:
        """실제 추천 생성"""
        try:
            from api.chains.recommend_chain import RecommendChain
            
            recommend_chain = RecommendChain(self.db)
            result = await recommend_chain.process(
                folder_id=folder_id,
                keywords=keywords.split(",") if keywords else None
            )
            
            return json.dumps({
                "status": "success",
                "recommendations": result["recommendations"],
                "keywords": result.get("keywords", [])
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"추천 생성 실패: {e}")
            return json.dumps({
                "status": "error",
                "message": f"추천 생성 중 오류가 발생했습니다: {str(e)}"
            }, ensure_ascii=False)
    
    async def create_tool(self) -> Tool:
        """LangChain Tool 생성"""
        
        async def recommend_wrapper(folder_id: str = None, keywords: str = None) -> str:
            return await self._generate_recommendations(
                folder_id=folder_id if folder_id and folder_id.strip() else None,
                keywords=keywords if keywords and keywords.strip() else None
            )
        
        tool = Tool(
            name="content_recommend",
            description="""관련 콘텐츠를 추천하는 도구입니다.
사용법: content_recommend(folder_id=None, keywords=None)
- folder_id: 추천 대상 폴더 ID
- keywords: 추천 키워드들 (쉼표로 구분)

예시: content_recommend(keywords="인공지능,머신러닝")""",
            func=recommend_wrapper,
            return_direct=False
        )
        
        return tool 