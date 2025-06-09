"""
Quiz Tool
퀴즈 생성을 위한 LangChain Tool
"""
import json
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_core.tools import Tool

from utils.logger import get_logger

logger = get_logger(__name__)

class QuizTool:
    """퀴즈 생성 도구"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def _generate_quiz(self, document_ids: Optional[List[str]] = None,
                           folder_id: Optional[str] = None,
                           count: int = 5, difficulty: str = "medium") -> str:
        """실제 퀴즈 생성"""
        try:
            logger.info(f"퀴즈 생성 시작: document_ids={document_ids}, folder_id={folder_id}")
            
            # 기존 quiz_chain 사용
            from api.chains.quiz_chain import QuizChain
            
            quiz_chain = QuizChain(self.db)
            result = await quiz_chain.process(
                document_ids=document_ids,
                folder_id=folder_id,
                count=count,
                difficulty=difficulty
            )
            
            return json.dumps({
                "status": "success",
                "quizzes": result["qapairs"],
                "quiz_count": len(result["qapairs"]),
                "difficulty": difficulty,
                "document_count": result.get("document_count", 0)
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"퀴즈 생성 실패: {e}")
            return json.dumps({
                "status": "error",
                "message": f"퀴즈 생성 중 오류가 발생했습니다: {str(e)}"
            }, ensure_ascii=False)
    
    async def create_tool(self) -> Tool:
        """LangChain Tool 생성"""
        
        async def quiz_wrapper(document_ids: str = None, folder_id: str = None,
                             count: int = 5, difficulty: str = "medium") -> str:
            """Tool wrapper 함수"""
            parsed_doc_ids = None
            if document_ids and document_ids.strip():
                parsed_doc_ids = [id.strip() for id in document_ids.split(",") if id.strip()]
            
            return await self._generate_quiz(
                document_ids=parsed_doc_ids,
                folder_id=folder_id if folder_id and folder_id.strip() else None,
                count=min(count, 20),  # 최대 20개 제한
                difficulty=difficulty
            )
        
        tool = Tool(
            name="quiz_generator",
            description="""문서 내용으로 퀴즈를 생성하는 도구입니다.
사용법: quiz_generator(document_ids=None, folder_id=None, count=5, difficulty="medium")
- document_ids: 퀴즈를 만들 문서 ID들 (쉼표로 구분)
- folder_id: 폴더 내 모든 문서로 퀴즈 생성할 경우 폴더 ID
- count: 생성할 퀴즈 개수 (1-20개)
- difficulty: 난이도 ("easy", "medium", "hard" 중 선택)

예시: quiz_generator(folder_id="folder123", count=10, difficulty="hard")""",
            func=quiz_wrapper,
            return_direct=False
        )
        
        logger.info("Quiz Tool 생성 완료")
        return tool 