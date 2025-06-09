"""
Vector Search Tool
벡터 검색 도구
"""
import json
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from ..vectorstore import VectorStoreManager  # 수정: 상대 임포트로 변경
from utils.logger import get_logger

logger = get_logger(__name__)

class VectorSearchInput(BaseModel):
    """벡터 검색 입력 모델"""
    query: str = Field(description="검색할 텍스트")
    folder_id: Optional[str] = Field(default=None, description="특정 폴더 ID (선택사항)")
    file_id: Optional[str] = Field(default=None, description="특정 파일 내에서만 검색할 경우 파일 ID")
    k: int = Field(default=5, description="반환할 문서 개수 (1-20)")

class VectorSearchTool(BaseTool):
    """벡터 검색 도구"""
    
    name: str = "vector_search"
    description: str = """벡터 데이터베이스에서 유사한 문서를 검색합니다. 
    입력: 검색할 텍스트 (query)
    출력: 관련 문서들과 메타데이터를 JSON 형태로 반환"""
    
    vector_store: VectorStoreManager = Field(exclude=True)
    
    def __init__(self, db: AsyncIOMotorDatabase, **kwargs):
        super().__init__(**kwargs)
        self.vector_store = VectorStoreManager(db)
    
    async def _search_documents(self, query: str, folder_id: Optional[str] = None, 
                              file_id: Optional[str] = None, k: int = 5) -> str:
        """실제 검색 수행"""
        try:
            logger.info(f"벡터 검색 실행: '{query}', folder_id={folder_id}, k={k}")
            
            # 필터 조건 설정
            filter_dict = {}
            if folder_id:
                filter_dict["folder_id"] = folder_id
            elif file_id:
                filter_dict["file_id"] = file_id
            
            # 검색 수행
            documents = await self.vector_store.similarity_search(
                query=query,
                k=min(k, 20),  # 최대 20개 제한
                filter_dict=filter_dict if filter_dict else None
            )
            
            if not documents:
                return json.dumps({
                    "status": "no_results",
                    "message": "검색 결과가 없습니다.",
                    "documents": []
                }, ensure_ascii=False)
            
            # 결과 포맷팅
            results = []
            for i, doc in enumerate(documents):
                result = {
                    "rank": i + 1,
                    "content": doc.page_content[:300] + ("..." if len(doc.page_content) > 300 else ""),
                    "metadata": {
                        "source": doc.metadata.get("source", ""),
                        "file_type": doc.metadata.get("file_type", ""),
                        "chunk_id": doc.metadata.get("chunk_id", ""),
                        "score": doc.metadata.get("score", 0.0)
                    }
                }
                results.append(result)
            
            return json.dumps({
                "status": "success",
                "message": f"{len(results)}개 문서를 찾았습니다.",
                "query": query,
                "total_results": len(results),
                "documents": results
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}")
            return json.dumps({
                "status": "error",
                "message": f"검색 중 오류가 발생했습니다: {str(e)}",
                "documents": []
            }, ensure_ascii=False)
    
    async def create_tool(self) -> Tool:
        """LangChain Tool 생성"""
        
        async def search_wrapper(query: str, folder_id: str = None, 
                               file_id: str = None, k: int = 5) -> str:
            """Tool wrapper 함수"""
            return await self._search_documents(
                query=query,
                folder_id=folder_id if folder_id and folder_id.strip() else None,
                file_id=file_id if file_id and file_id.strip() else None,
                k=k
            )
        
        tool = Tool(
            name="vector_search",
            description="""문서 내용을 벡터 기반으로 검색하는 도구입니다.
사용법: vector_search(query="검색 질문", folder_id=None, file_id=None, k=5)
- query: 검색할 질문이나 키워드 (필수)
- folder_id: 특정 폴더 내에서만 검색할 경우 폴더 ID (선택)
- file_id: 특정 파일 내에서만 검색할 경우 파일 ID (선택)  
- k: 반환할 문서 개수, 기본값 5개 (1-20 사이)

예시: vector_search(query="인공지능의 정의", k=3)""",
            func=search_wrapper,
            return_direct=False
        )
        
        logger.info("Vector Search Tool 생성 완료")
        return tool 