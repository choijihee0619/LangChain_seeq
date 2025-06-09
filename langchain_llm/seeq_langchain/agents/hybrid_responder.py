"""
하이브리드 응답 생성기
벡터 검색 + 일반 지식을 결합한 응답 시스템
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
import openai

from config.settings import settings
from retrieval.vector_search import VectorSearch
from utils.logger import get_logger

logger = get_logger(__name__)

class HybridResponder:
    """
    하이브리드 응답 생성기
    벡터 검색 + 일반 지식을 결합한 응답 시스템
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.vector_search = VectorSearch(db)
        self.openai_client = None
        self._initialized = False
    
    async def initialize(self):
        """OpenAI 클라이언트 초기화"""
        if self._initialized:
            return
        
        try:
            # OpenAI 클라이언트 직접 사용
            self.openai_client = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY
            )
            
            logger.info("Hybrid Responder 초기화 완료")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Hybrid Responder 초기화 실패: {e}")
            raise
    
    async def generate_response(
        self,
        query: str,
        session_id: str,
        conversation_history: List = None
    ) -> Dict[str, Any]:
        """응답 생성"""
        try:
            # 1. 벡터 검색 수행
            vector_results = await self.vector_search.search_similar(
                query=query,
                k=5,
                filter_dict=None
            )
            
            # 2. 전략 결정 및 응답 생성
            best_score = max([r.get("score", 0.0) for r in vector_results]) if vector_results else 0.0
            
            if best_score >= 0.8:
                # 높은 유사도: 벡터 기반 응답
                return await self._generate_vector_based_response(query, vector_results, conversation_history)
            elif best_score >= 0.3:
                # 중간 유사도: 하이브리드 응답
                return await self._generate_hybrid_response(query, vector_results, conversation_history)
            else:
                # 낮은 유사도: 일반 지식 응답
                return await self._generate_general_knowledge_response(query, conversation_history)
                
        except Exception as e:
            logger.error(f"하이브리드 응답 생성 실패: {e}")
            return {
                "answer": "죄송합니다. 현재 질문에 대한 답변을 생성하는 데 문제가 발생했습니다. 다시 시도해주시거나 질문을 다르게 표현해주세요.",
                "sources": [],
                "strategy": "fallback",
                "confidence": 0.1
            }

    async def _call_openai(self, prompt: str) -> str:
        """OpenAI API 직접 호출"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API 호출 실패: {e}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"

    async def _generate_vector_based_response(
        self, 
        query: str, 
        vector_results: List[Dict],
        conversation_history: List = None
    ) -> Dict[str, Any]:
        """벡터 기반 응답 생성 - 출처 정보 포함"""
        
        try:
            # 컨텍스트 구성
            context_texts = []
            source_info = []
            
            for result in vector_results[:3]:
                context_texts.append(result["chunk"]["text"])
                filename = result["document"].get("original_filename", "알 수 없는 파일")
                source_info.append(f"📄 {filename}")
            
            context = "\n\n".join(context_texts)
            sources_text = "\n".join(source_info)
            
            # 단순한 프롬프트 생성
            prompt = f"""
당신은 친근하고 도움이 되는 AI 어시스턴트입니다.
아래 문서 내용을 바탕으로 사용자의 질문에 답변해주세요.

참고 문서:
{context}

질문: {query}

답변 마지막에는 다음과 같이 출처를 명시해주세요:

📚 **참고 문서:**
{sources_text}
"""
            
            # OpenAI API 직접 호출
            answer = await self._call_openai(prompt)
            
            return {
                "answer": answer,
                "sources": [
                    {
                        "text": result["chunk"]["text"][:200] + "...",
                        "score": result.get("score", 0.0),
                        "filename": result["document"].get("original_filename", ""),
                        "file_id": result["chunk"].get("file_id", ""),
                        "chunk_id": result["chunk"].get("chunk_id", "")
                    }
                    for result in vector_results[:3]
                ],
                "strategy": "vector_based",
                "confidence": 0.9
            }
            
        except Exception as e:
            logger.error(f"벡터 기반 응답 생성 실패: {e}")
            return {
                "answer": f"데이터베이스에서 관련 문서를 찾았지만, 응답 생성 중 오류가 발생했습니다: {str(e)}",
                "sources": [],
                "strategy": "vector_error",
                "confidence": 0.3
            }
    
    async def _generate_hybrid_response(
        self,
        query: str,
        vector_results: List[Dict],
        conversation_history: List = None
    ) -> Dict[str, Any]:
        """하이브리드 응답 생성 - 부분적 정보 + 일반 지식"""
        
        try:
            # 관련 있는 문서들만 선별
            relevant_docs = [r for r in vector_results if r.get("score", 0) >= 0.3]
            
            if relevant_docs:
                # 부분적 정보가 있는 경우
                context_texts = [result["chunk"]["text"] for result in relevant_docs[:2]]
                context = "\n\n".join(context_texts)
                
                source_info = []
                for result in relevant_docs[:2]:
                    filename = result["document"].get("original_filename", "알 수 없는 파일")
                    source_info.append(f"📄 {filename}")
                sources_text = "\n".join(source_info)
                
                prompt = f"""
당신은 친근하고 지식이 풍부한 AI 어시스턴트입니다.
제공된 문서에는 부분적인 관련 정보만 있습니다. 이 정보를 참고하되, 부족한 부분은 당신의 일반 지식으로 보완하여 완전한 답변을 제공해주세요.

부분적 관련 문서:
{context}

질문: {query}

답변 형식:
1. 문서에서 찾은 정보: [문서 내용 기반]
2. 추가 일반 정보: [일반 지식 기반]

📚 **참고한 문서:**
{sources_text}
"""
                
            else:
                # 관련 문서가 전혀 없는 경우
                prompt = f"""
질문: {query}

⚠️ 데이터베이스에서 이 질문과 직접 관련된 문서를 찾을 수 없었습니다.

하지만 일반적인 지식을 바탕으로 도움이 되는 답변을 드리겠습니다:
"""
            
            # OpenAI API 직접 호출
            answer = await self._call_openai(prompt)
            
            return {
                "answer": answer,
                "sources": [
                    {
                        "text": result["chunk"]["text"][:200] + "...",
                        "score": result.get("score", 0.0),
                        "filename": result["document"].get("original_filename", ""),
                        "file_id": result["chunk"].get("file_id", ""),
                        "chunk_id": result["chunk"].get("chunk_id", "")
                    }
                    for result in relevant_docs
                ] if relevant_docs else [],
                "strategy": "hybrid",
                "confidence": 0.8
            }
            
        except Exception as e:
            logger.error(f"하이브리드 응답 생성 실패: {e}")
            return {
                "answer": f"⚠️ 데이터베이스에서 관련 문서를 찾을 수 없었으며, 응답 생성 중 오류가 발생했습니다: {str(e)}",
                "sources": [],
                "strategy": "hybrid_error",
                "confidence": 0.3
            }
    
    async def _generate_general_knowledge_response(
        self,
        query: str,
        conversation_history: List = None
    ) -> Dict[str, Any]:
        """일반 지식 기반 응답 생성 - 데이터베이스에 없음을 명시"""
        
        try:
            prompt = f"""
질문: {query}

❌ **데이터베이스 검색 결과:** 이 질문과 관련된 문서를 찾을 수 없었습니다.

💡 **일반 지식 기반 답변:**
당신의 일반적인 지식을 바탕으로 위 질문에 대해 정확하고 유용한 정보를 제공해주세요.
"""
            
            # OpenAI API 직접 호출
            answer = await self._call_openai(prompt)
            
            return {
                "answer": answer,
                "sources": [],
                "strategy": "general_knowledge",
                "confidence": 0.7
            }
            
        except Exception as e:
            logger.error(f"일반 지식 응답 생성 실패: {e}")
            return {
                "answer": f"❌ 데이터베이스에서 관련 문서를 찾을 수 없었으며, 일반 지식 응답 생성 중 오류가 발생했습니다: {str(e)}",
                "sources": [],
                "strategy": "general_error",
                "confidence": 0.1
            } 