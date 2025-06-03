"""
질의응답 체인
LangChain을 사용한 RAG 파이프라인
"""
from typing import Dict, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from retrieval.hybrid_search import HybridSearch
from retrieval.context_builder import ContextBuilder
from ai_processing.llm_client import LLMClient
from utils.logger import get_logger

logger = get_logger(__name__)

class QueryChain:
    """질의응답 체인 클래스"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.hybrid_search = HybridSearch(db)
        self.context_builder = ContextBuilder()
        self.llm_client = LLMClient()
        
        # 프롬프트 템플릿
        self.prompt_template = """다음 컨텍스트를 참고하여 사용자의 질문에 답변해주세요.
답변은 정확하고 도움이 되도록 작성하되, 컨텍스트에 없는 내용은 추측하지 마세요.

컨텍스트:
{context}

질문: {question}

답변:"""
    
    async def process(
        self,
        query: str,
        folder_id: Optional[str] = None,
        top_k: int = 5
    ) -> Dict:
        """질의 처리"""
        try:
            # folder_id 정리 - "string" 값은 None으로 처리
            clean_folder_id = None
            if folder_id and folder_id.strip() and folder_id not in ["string", "null"]:
                clean_folder_id = folder_id.strip()
            
            logger.info(f"질의 처리 시작 - 쿼리: '{query}', 폴더: '{clean_folder_id}', top_k: {top_k}")
            
            # 1. 관련 문서 검색
            search_results = await self.hybrid_search.search(
                query=query,
                k=top_k,
                folder_id=clean_folder_id
            )
            
            logger.info(f"검색 결과: {len(search_results)}개 청크")
            
            # 2. 컨텍스트 구성
            context = self.context_builder.build_context(search_results)
            
            # 3. LLM 응답 생성
            prompt = self.prompt_template.format(
                context=context,
                question=query
            )
            
            answer = await self.llm_client.generate(prompt)
            
            # 4. 소스 정보 구성 - 파일명 포함
            sources = []
            for result in search_results:
                chunk = result.get("chunk", {})
                document = result.get("document", {})
                
                source_info = {
                    "text": chunk.get("text", "")[:200] + "...",
                    "score": round(result.get("score", 0.0), 3),
                    "filename": document.get("original_filename", "알 수 없는 파일"),
                    "file_id": chunk.get("file_id", ""),
                    "chunk_id": chunk.get("chunk_id", ""),
                    "sequence": chunk.get("sequence", 0),
                    "file_type": document.get("file_type", "unknown")
                }
                sources.append(source_info)
            
            logger.info(f"질의 처리 완료 - 답변 길이: {len(answer)}, 소스: {len(sources)}개")
            
            # 5. 결과 반환
            return {
                "answer": answer,
                "sources": sources,
                "confidence": 0.9
            }
            
        except Exception as e:
            logger.error(f"질의 처리 실패: {e}")
            raise
