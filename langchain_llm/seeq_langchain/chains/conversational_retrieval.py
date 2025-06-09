"""
Conversational Retrieval Chain Wrapper
대화형 검색 체인 - 채팅 기록 유지하며 문서 검색
"""
from typing import Dict, Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate

from utils.logger import get_logger

logger = get_logger(__name__)

class ConversationalRetrievalChainWrapper:
    """ConversationalRetrievalChain 래퍼"""
    
    def __init__(self, db: AsyncIOMotorDatabase, llm: ChatOpenAI, vectorstore_manager):
        self.db = db
        self.llm = llm
        self.vectorstore_manager = vectorstore_manager
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
    
    async def create_chain(self) -> ConversationalRetrievalChain:
        """ConversationalRetrievalChain 생성"""
        try:
            # 커스텀 프롬프트 템플릿
            custom_prompt = PromptTemplate(
                template="""다음 컨텍스트를 기반으로 질문에 답변해주세요. 컨텍스트에 관련 정보가 없다면, 일반적인 지식을 활용하여 도움이 되는 답변을 제공해주세요.

컨텍스트:
{context}

채팅 기록:
{chat_history}

질문: {question}

답변을 작성할 때:
1. 컨텍스트의 정보를 최우선으로 활용하세요
2. 컨텍스트에 없는 내용이라도 질문에 도움이 되는 일반적인 정보를 제공하세요
3. 답변의 근거를 명확히 제시하세요
4. 한국어로 자연스럽고 친근하게 답변하세요

답변:""",
                input_variables=["context", "chat_history", "question"]
            )
            
            # Retriever 생성 (기본)
            retriever = self.vectorstore_manager.retriever
            
            # ConversationalRetrievalChain 생성
            chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever,
                memory=self.memory,
                return_source_documents=True,
                combine_docs_chain_kwargs={"prompt": custom_prompt},
                verbose=True
            )
            
            logger.info("ConversationalRetrievalChain 생성 완료")
            return chain
            
        except Exception as e:
            logger.error(f"ConversationalRetrievalChain 생성 실패: {e}")
            raise
    
    async def create_filtered_chain(self, folder_id: Optional[str] = None, 
                                  file_id: Optional[str] = None, k: int = 5) -> ConversationalRetrievalChain:
        """필터가 적용된 체인 생성"""
        try:
            # 필터된 Retriever 생성
            retriever = await self.vectorstore_manager.get_retriever_with_filter(
                folder_id=folder_id,
                file_id=file_id,
                k=k
            )
            
            # 새로운 메모리 인스턴스 생성
            filtered_memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
            
            custom_prompt = PromptTemplate(
                template="""다음 컨텍스트를 기반으로 질문에 답변해주세요.

컨텍스트 (폴더 ID: {folder_id}, 파일 ID: {file_id}):
{context}

채팅 기록:
{chat_history}

질문: {question}

답변:""",
                input_variables=["context", "chat_history", "question", "folder_id", "file_id"]
            )
            
            chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever,
                memory=filtered_memory,
                return_source_documents=True,
                combine_docs_chain_kwargs={"prompt": custom_prompt},
                verbose=True
            )
            
            logger.info(f"필터된 ConversationalRetrievalChain 생성 완료 (folder_id={folder_id}, file_id={file_id})")
            return chain
            
        except Exception as e:
            logger.error(f"필터된 ConversationalRetrievalChain 생성 실패: {e}")
            raise 