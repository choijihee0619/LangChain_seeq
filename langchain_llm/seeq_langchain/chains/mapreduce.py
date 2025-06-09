"""
MapReduce Chain Wrapper
대량 문서 요약 및 분석
"""
from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_openai import ChatOpenAI
from langchain.chains.mapreduce import MapReduceDocumentsChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document

from utils.logger import get_logger

logger = get_logger(__name__)

class MapReduceChainWrapper:
    """MapReduce Chain 래퍼"""
    
    def __init__(self, db: AsyncIOMotorDatabase, llm: ChatOpenAI):
        self.db = db
        self.llm = llm
    
    async def create_chain(self) -> MapReduceDocumentsChain:
        """MapReduce Chain 생성"""
        try:
            # Map 단계 프롬프트
            map_template = """다음 문서의 핵심 내용을 요약해주세요:

문서:
{docs}

요약:"""
            map_prompt = PromptTemplate.from_template(map_template)
            map_chain = LLMChain(llm=self.llm, prompt=map_prompt)
            
            # Reduce 단계 프롬프트
            reduce_template = """다음은 여러 문서의 요약들입니다. 이를 종합하여 전체적인 요약을 작성해주세요:

요약들:
{docs}

최종 종합 요약:"""
            reduce_prompt = PromptTemplate.from_template(reduce_template)
            reduce_chain = LLMChain(llm=self.llm, prompt=reduce_prompt)
            
            # Combine documents chain
            combine_documents_chain = StuffDocumentsChain(
                llm_chain=reduce_chain,
                document_variable_name="docs"
            )
            
            # MapReduce chain
            reduce_documents_chain = MapReduceDocumentsChain(
                llm_chain=map_chain,
                combine_document_chain=combine_documents_chain,
                document_variable_name="docs",
                return_intermediate_steps=False
            )
            
            logger.info("MapReduce Chain 생성 완료")
            return reduce_documents_chain
            
        except Exception as e:
            logger.error(f"MapReduce Chain 생성 실패: {e}")
            raise 