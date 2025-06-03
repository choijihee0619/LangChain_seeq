"""
LLM 클라이언트 모듈
OpenAI GPT-4o-mini API 인터페이스
"""
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class LLMClient:
    """LLM 클라이언트 클래스"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """LLM 응답 생성"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM 생성 실패: {e}")
            raise
    
    async def generate_with_context(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """컨텍스트 기반 응답 생성"""
        prompt = f"""다음 컨텍스트를 참고하여 질문에 답변해주세요.

컨텍스트:
{context}

질문: {query}

답변:"""
        
        return await self.generate(prompt, system_prompt)
