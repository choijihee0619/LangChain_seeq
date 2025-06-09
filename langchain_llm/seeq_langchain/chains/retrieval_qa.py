"""
RetrievalQA Chain Wrapper
단순 QA 체인 - 질문에 대한 직접적인 답변 생성
"""
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate

from utils.logger import get_logger

logger = get_logger(__name__)

class RetrievalQAChainWrapper:
    """RetrievalQA Chain 래퍼"""
    
    def __init__(self, db: AsyncIOMotorDatabase, llm: ChatOpenAI, vectorstore_manager):
        self.db = db
        self.llm = llm
        self.vectorstore_manager = vectorstore_manager
    
    async def create_chain(self) -> RetrievalQA:
        """RetrievalQA Chain 생성"""
        try:
            # 커스텀 프롬프트 템플릿
            custom_prompt = PromptTemplate(
                template="""컨텍스트를 기반으로 질문에 정확하고 간결하게 답변해주세요. 
컨텍스트에 관련 정보가 없다면, 일반적인 지식을 활용하여 도움이 되는 답변을 제공하세요.

컨텍스트:
{context}

질문: {question}

답변 가이드라인:
- 컨텍스트의 정보를 최우선으로 활용
- 컨텍스트에 없어도 질문에 도움되는 일반 지식 제공
- 명확하고 구체적인 답변
- 한국어로 자연스럽게 작성

답변:""",
                input_variables=["context", "question"]
            )
            
            # Retriever 생성
            retriever = self.vectorstore_manager.retriever
            
            # RetrievalQA Chain 생성
            chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": custom_prompt},
                verbose=True
            )
            
            logger.info("RetrievalQA Chain 생성 완료")
            return chain
            
        except Exception as e:
            logger.error(f"RetrievalQA Chain 생성 실패: {e}")
            raise 