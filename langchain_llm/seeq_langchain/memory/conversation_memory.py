"""
Conversation Memory Wrapper
LangChain 메모리 래퍼
"""
from typing import Dict, Any, Optional
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_openai import ChatOpenAI

from utils.logger import get_logger

logger = get_logger(__name__)

class ConversationMemoryWrapper:
    """대화 메모리 래퍼"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def create_buffer_memory(self, max_token_limit: int = 2000) -> ConversationBufferMemory:
        """버퍼 메모리 생성"""
        return ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=max_token_limit
        )
    
    def create_summary_memory(self, max_token_limit: int = 2000) -> ConversationSummaryMemory:
        """요약 메모리 생성"""
        return ConversationSummaryMemory(
            llm=self.llm,
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=max_token_limit
        ) 