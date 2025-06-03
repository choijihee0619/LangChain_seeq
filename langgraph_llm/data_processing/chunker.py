"""
청킹 모듈
문서를 적절한 크기로 분할
"""
from typing import List, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class TextChunker:
    """텍스트 청킹 클래스"""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        
        # LangChain 텍스트 분할기 초기화
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\\n\\n", "\\n", ".", "!", "?", " ", ""],
            length_function=len
        )
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """텍스트를 청크로 분할"""
        # 텍스트 분할
        chunks = self.splitter.split_text(text)
        
        # 청크 메타데이터 추가
        chunk_docs = []
        for i, chunk in enumerate(chunks):
            chunk_doc = {
                "text": chunk,
                "sequence": i,
                "metadata": {
                    "chunk_method": "recursive",
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap,
                    "total_chunks": len(chunks)
                }
            }
            
            # 추가 메타데이터가 있으면 병합
            if metadata:
                chunk_doc["metadata"].update(metadata)
            
            chunk_docs.append(chunk_doc)
        
        logger.info(f"청킹 완료: {len(chunks)}개 청크 생성")
        return chunk_docs
    
    def chunk_by_sentences(self, text: str, sentences_per_chunk: int = 5) -> List[Dict]:
        """문장 단위로 청킹"""
        # 간단한 문장 분리 (실제로는 더 정교한 방법 필요)
        sentences = text.split('. ')
        
        chunks = []
        for i in range(0, len(sentences), sentences_per_chunk):
            chunk_sentences = sentences[i:i+sentences_per_chunk]
            chunk_text = '. '.join(chunk_sentences)
            if not chunk_text.endswith('.'):
                chunk_text += '.'
            
            chunks.append({
                "text": chunk_text,
                "sequence": i // sentences_per_chunk,
                "metadata": {
                    "chunk_method": "sentences",
                    "sentences_per_chunk": sentences_per_chunk
                }
            })
        
        return chunks
