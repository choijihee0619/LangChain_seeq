"""
Summary Tool
문서 요약을 위한 LangChain Tool
"""
import json
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_core.tools import Tool

from utils.logger import get_logger

logger = get_logger(__name__)

class SummaryTool:
    """문서 요약 도구"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def _generate_summary(self, document_ids: Optional[List[str]] = None, 
                              folder_id: Optional[str] = None, 
                              summary_type: str = "detailed") -> str:
        """실제 요약 생성"""
        try:
            logger.info(f"요약 생성 시작: document_ids={document_ids}, folder_id={folder_id}")
            
            # 기존 summary_chain 사용
            from api.chains.summary_chain import SummaryChain
            
            summary_chain = SummaryChain(self.db)
            result = await summary_chain.process(
                document_ids=document_ids,
                folder_id=folder_id,
                summary_type=summary_type
            )
            
            return json.dumps({
                "status": "success",
                "summary": result["summary"],
                "document_count": result["document_count"],
                "from_cache": result.get("from_cache", False),
                "summary_type": summary_type
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"요약 생성 실패: {e}")
            return json.dumps({
                "status": "error", 
                "message": f"요약 생성 중 오류가 발생했습니다: {str(e)}"
            }, ensure_ascii=False)
    
    async def create_tool(self) -> Tool:
        """LangChain Tool 생성"""
        
        async def summary_wrapper(document_ids: str = None, folder_id: str = None,
                                summary_type: str = "detailed") -> str:
            """Tool wrapper 함수"""
            # document_ids 파싱 (쉼표로 구분된 문자열)
            parsed_doc_ids = None
            if document_ids and document_ids.strip():
                parsed_doc_ids = [id.strip() for id in document_ids.split(",") if id.strip()]
            
            return await self._generate_summary(
                document_ids=parsed_doc_ids,
                folder_id=folder_id if folder_id and folder_id.strip() else None,
                summary_type=summary_type
            )
        
        tool = Tool(
            name="document_summary",
            description="""문서를 요약하는 도구입니다.
사용법: document_summary(document_ids=None, folder_id=None, summary_type="detailed")
- document_ids: 요약할 문서 ID들 (쉼표로 구분, 예: "doc1,doc2,doc3")
- folder_id: 폴더 내 모든 문서 요약할 경우 폴더 ID  
- summary_type: 요약 타입 ("brief", "detailed", "bullets" 중 선택)

예시: document_summary(folder_id="folder123", summary_type="brief")""",
            func=summary_wrapper,
            return_direct=False
        )
        
        logger.info("Summary Tool 생성 완료")
        return tool 