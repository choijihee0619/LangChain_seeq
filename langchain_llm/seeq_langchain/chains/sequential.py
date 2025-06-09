"""
Sequential Chain Wrapper
여러 작업을 순서대로 실행
"""
from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_openai import ChatOpenAI
from langchain.chains import SequentialChain, LLMChain
from langchain_core.prompts import PromptTemplate

from utils.logger import get_logger

logger = get_logger(__name__)

class SequentialChainWrapper:
    """Sequential Chain 래퍼"""
    
    def __init__(self, db: AsyncIOMotorDatabase, llm: ChatOpenAI):
        self.db = db
        self.llm = llm
    
    async def create_chain(self) -> SequentialChain:
        """Sequential Chain 생성"""
        try:
            # 첫 번째 체인: 분석
            analysis_prompt = PromptTemplate(
                input_variables=["input"],
                template="다음 텍스트를 분석해주세요:\n\n{input}\n\n분석 결과:"
            )
            analysis_chain = LLMChain(
                llm=self.llm,
                prompt=analysis_prompt,
                output_key="analysis"
            )
            
            # 두 번째 체인: 요약
            summary_prompt = PromptTemplate(
                input_variables=["analysis"],
                template="다음 분석 결과를 요약해주세요:\n\n{analysis}\n\n요약:"
            )
            summary_chain = LLMChain(
                llm=self.llm,
                prompt=summary_prompt,
                output_key="summary"
            )
            
            # 세 번째 체인: 결론
            conclusion_prompt = PromptTemplate(
                input_variables=["summary"],
                template="다음 요약을 바탕으로 결론을 도출해주세요:\n\n{summary}\n\n결론:"
            )
            conclusion_chain = LLMChain(
                llm=self.llm,
                prompt=conclusion_prompt,
                output_key="conclusion"
            )
            
            # Sequential Chain 구성
            overall_chain = SequentialChain(
                chains=[analysis_chain, summary_chain, conclusion_chain],
                input_variables=["input"],
                output_variables=["analysis", "summary", "conclusion"],
                verbose=True
            )
            
            logger.info("Sequential Chain 생성 완료")
            return overall_chain
            
        except Exception as e:
            logger.error(f"Sequential Chain 생성 실패: {e}")
            raise 