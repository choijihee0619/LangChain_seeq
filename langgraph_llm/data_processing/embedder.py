"""
임베딩 모듈
OpenAI 임베딩 API를 사용한 텍스트 벡터화
"""
from typing import List, Dict
import asyncio
from openai import AsyncOpenAI
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class TextEmbedder:
    """텍스트 임베딩 클래스"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_EMBEDDING_MODEL
    
    async def embed_text(self, text: str) -> List[float]:
        """단일 텍스트 임베딩"""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            raise
    
    async def embed_batch(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        """배치 텍스트 임베딩"""
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
                
                logger.info(f"임베딩 생성 진행: {len(embeddings)}/{len(texts)}")
            except Exception as e:
                logger.error(f"배치 임베딩 실패: {e}")
                raise
        
        return embeddings
    
    async def embed_documents(self, documents: List[Dict]) -> List[Dict]:
        """문서 리스트에 임베딩 추가"""
        texts = [doc["text"] for doc in documents]
        embeddings = await self.embed_batch(texts)
        
        for doc, embedding in zip(documents, embeddings):
            doc["text_embedding"] = embedding
        
        logger.info(f"문서 임베딩 완료: {len(documents)}개")
        return documents
