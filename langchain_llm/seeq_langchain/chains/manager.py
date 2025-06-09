"""
Chain Manager
모든 LangChain Chains의 중앙 관리자
"""
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class ChainManager:
    """Chain 관리자"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_MODEL,
            temperature=0.1
        )
        self._chains: Dict[str, Any] = {}
        self._initialized = False
    
    async def initialize(self):
        """모든 체인 초기화"""
        if self._initialized:
            return
        
        try:
            from .conversational_retrieval import ConversationalRetrievalChainWrapper
            from .sequential import SequentialChainWrapper
            from .mapreduce import MapReduceChainWrapper
            from .retrieval_qa import RetrievalQAChainWrapper
            
            # VectorStore Manager 가져오기
            from langchain.vectorstore import VectorStoreManager
            vectorstore_manager = VectorStoreManager(self.db)
            
            # 체인 인스턴스 생성
            conv_retrieval = ConversationalRetrievalChainWrapper(
                self.db, self.llm, vectorstore_manager
            )
            sequential = SequentialChainWrapper(self.db, self.llm)
            mapreduce = MapReduceChainWrapper(self.db, self.llm)
            retrieval_qa = RetrievalQAChainWrapper(
                self.db, self.llm, vectorstore_manager
            )
            
            # 체인 등록
            self._chains.update({
                "conversational_retrieval": await conv_retrieval.create_chain(),
                "sequential": await sequential.create_chain(),
                "mapreduce": await mapreduce.create_chain(),
                "retrieval_qa": await retrieval_qa.create_chain()
            })
            
            self._initialized = True
            logger.info(f"Chain Manager 초기화 완료: {len(self._chains)}개 체인 등록")
            
        except Exception as e:
            logger.error(f"Chain Manager 초기화 실패: {e}")
            raise
    
    def get_chain(self, chain_name: str):
        """특정 체인 반환"""
        if not self._initialized:
            raise RuntimeError("Chain Manager가 초기화되지 않았습니다.")
        
        if chain_name not in self._chains:
            raise ValueError(f"체인 '{chain_name}'를 찾을 수 없습니다.")
        
        return self._chains[chain_name]
    
    def get_all_chains(self) -> Dict[str, Any]:
        """모든 체인 반환"""
        if not self._initialized:
            raise RuntimeError("Chain Manager가 초기화되지 않았습니다.")
        
        return self._chains.copy()
    
    async def run_conversational_chain(
        self,
        query: str,
        chat_history: Optional[list] = None,
        folder_id: Optional[str] = None,
        k: int = 5
    ) -> Dict[str, Any]:
        """대화형 검색 체인 실행"""
        try:
            chain = self.get_chain("conversational_retrieval")
            
            result = await chain.ainvoke({
                "question": query,
                "chat_history": chat_history or [],
                "folder_id": folder_id,
                "k": k
            })
            
            return {
                "answer": result["answer"],
                "source_documents": result.get("source_documents", []),
                "chat_history": result.get("chat_history", [])
            }
            
        except Exception as e:
            logger.error(f"대화형 체인 실행 실패: {e}")
            raise
    
    async def run_retrieval_qa_chain(
        self,
        query: str,
        folder_id: Optional[str] = None,
        k: int = 5
    ) -> Dict[str, Any]:
        """RetrievalQA 체인 실행"""
        try:
            chain = self.get_chain("retrieval_qa")
            
            result = await chain.ainvoke({
                "query": query,
                "folder_id": folder_id,
                "k": k
            })
            
            return {
                "result": result["result"],
                "source_documents": result.get("source_documents", [])
            }
            
        except Exception as e:
            logger.error(f"RetrievalQA 체인 실행 실패: {e}")
            raise
    
    async def run_mapreduce_chain(
        self,
        documents: list,
        task_type: str = "summarize"
    ) -> Dict[str, Any]:
        """MapReduce 체인 실행"""
        try:
            chain = self.get_chain("mapreduce")
            
            result = await chain.ainvoke({
                "input_documents": documents,
                "task_type": task_type
            })
            
            return {
                "output_text": result["output_text"],
                "input_document_count": len(documents)
            }
            
        except Exception as e:
            logger.error(f"MapReduce 체인 실행 실패: {e}")
            raise
    
    async def run_sequential_chain(
        self,
        inputs: Dict[str, Any],
        chain_sequence: list
    ) -> Dict[str, Any]:
        """Sequential 체인 실행"""
        try:
            chain = self.get_chain("sequential")
            
            result = await chain.ainvoke({
                **inputs,
                "chain_sequence": chain_sequence
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Sequential 체인 실행 실패: {e}")
            raise
    
    def list_available_chains(self) -> Dict[str, str]:
        """사용 가능한 체인 목록 반환"""
        if not self._initialized:
            return {}
        
        return {
            "conversational_retrieval": "대화형 검색 체인 - 채팅 기록을 유지하며 문서 검색",
            "retrieval_qa": "단순 QA 체인 - 질문에 대한 직접적인 답변 생성", 
            "mapreduce": "MapReduce 체인 - 대량 문서 요약 및 분석",
            "sequential": "순차 체인 - 여러 작업을 순서대로 실행"
        } 