"""
텍스트 수집 유틸리티
파일 및 폴더에서 텍스트를 가져오는 공통 기능 제공
CREATED 2024-01-21: 중복 로직 통합을 위한 새 유틸리티
"""
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.logger import get_logger

logger = get_logger(__name__)

class TextCollector:
    """텍스트 수집기 클래스"""
    
    @staticmethod
    async def get_text_from_file(
        db: AsyncIOMotorDatabase, 
        file_id: str, 
        use_chunks: bool = True
    ) -> str:
        """
        특정 파일에서 텍스트 수집
        
        Args:
            db: 데이터베이스 연결
            file_id: 파일 ID
            use_chunks: True면 청크에서, False면 원본 문서에서 가져오기
            
        Returns:
            수집된 텍스트 (없으면 빈 문자열)
        """
        try:
            if use_chunks:
                # 청크들에서 텍스트 수집
                chunks = await db.chunks.find({"file_id": file_id}).sort("sequence", 1).to_list(None)
                if chunks:
                    combined_text = "\n\n".join([chunk["text"] for chunk in chunks if chunk.get("text")])
                    if combined_text.strip():
                        return combined_text
            
            # 청크가 없거나 use_chunks=False면 documents에서 가져오기 (새로운 구조에 맞게 수정)
            document = await db.documents.find_one({"file_metadata.file_id": file_id})
            if document:
                return document.get("raw_text", "")
            
            return ""
            
        except Exception as e:
            logger.error(f"파일 텍스트 수집 실패 (file_id: {file_id}): {e}")
            return ""
    
    @staticmethod
    async def get_text_from_folder(
        db: AsyncIOMotorDatabase, 
        folder_id: str, 
        use_chunks: bool = True
    ) -> str:
        """
        폴더 내 모든 파일에서 텍스트 수집
        
        Args:
            db: 데이터베이스 연결
            folder_id: 폴더 ID
            use_chunks: True면 청크에서, False면 원본 문서에서 가져오기
            
        Returns:
            수집된 텍스트 (없으면 빈 문자열)
        """
        try:
            texts = []
            
            if use_chunks:
                # 폴더 내 모든 청크에서 텍스트 수집
                chunks = await db.chunks.find({"metadata.folder_id": folder_id}).sort("file_id", 1).sort("sequence", 1).to_list(None)
                if chunks:
                    for chunk in chunks:
                        text = chunk.get("text", "")
                        if text.strip():
                            texts.append(text)
                
                if texts:
                    return "\n\n".join(texts)
            
            # 청크가 없거나 use_chunks=False면 documents에서 가져오기
            documents = await db.documents.find({"folder_id": folder_id}).to_list(None)
            for doc in documents:
                text = doc.get("processed_text", doc.get("raw_text", ""))
                if text.strip():
                    texts.append(text)
            
            return "\n\n".join(texts)
            
        except Exception as e:
            logger.error(f"폴더 텍스트 수집 실패 (folder_id: {folder_id}): {e}")
            return ""
    
    @staticmethod
    async def get_text_from_files(
        db: AsyncIOMotorDatabase, 
        file_ids: List[str], 
        use_chunks: bool = True
    ) -> str:
        """
        여러 파일에서 텍스트 수집
        
        Args:
            db: 데이터베이스 연결
            file_ids: 파일 ID 리스트
            use_chunks: True면 청크에서, False면 원본 문서에서 가져오기
            
        Returns:
            수집된 텍스트 (없으면 빈 문자열)
        """
        try:
            texts = []
            
            if use_chunks:
                # 모든 파일의 청크에서 텍스트 수집
                chunks = await db.chunks.find({"file_id": {"$in": file_ids}}).sort("file_id", 1).sort("sequence", 1).to_list(None)
                for chunk in chunks:
                    text = chunk.get("text", "")
                    if text.strip():
                        texts.append(text)
            else:
                # documents에서 텍스트 수집 (새로운 구조에 맞게 수정)
                documents = await db.documents.find({"file_metadata.file_id": {"$in": file_ids}}).to_list(None)
                for doc in documents:
                    text = doc.get("raw_text", "")
                    if text.strip():
                        texts.append(text)
            
            return "\n\n".join(texts)
            
        except Exception as e:
            logger.error(f"다중 파일 텍스트 수집 실패 (file_ids: {file_ids}): {e}")
            return ""
    
    @staticmethod
    async def get_source_info(
        db: AsyncIOMotorDatabase,
        file_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        use_chunks: bool = True
    ) -> dict:
        """
        소스 정보 수집 (파일명, 청크 수 등)
        
        Returns:
            소스 정보 딕셔너리
        """
        try:
            source_info = {}
            
            if file_id:
                # 새로운 구조에 맞게 문서 조회 수정
                document = await db.documents.find_one({"file_metadata.file_id": file_id})
                if document:
                    chunks_count = await db.chunks.count_documents({"file_id": file_id}) if use_chunks else 0
                    text_length = len(await TextCollector.get_text_from_file(db, file_id, use_chunks))
                    
                    file_metadata = document.get("file_metadata", {})
                    source_info = {
                        "file_id": file_id,
                        "filename": file_metadata.get("original_filename", "알 수 없는 파일"),
                        "source_type": "chunks" if use_chunks and chunks_count > 0 else "document",
                        "chunk_count": chunks_count,
                        "text_length": text_length
                    }
            
            elif folder_id:
                documents = await db.documents.find({"folder_id": folder_id}).to_list(None)
                chunks_count = await db.chunks.count_documents({"metadata.folder_id": folder_id}) if use_chunks else 0
                text_length = len(await TextCollector.get_text_from_folder(db, folder_id, use_chunks))
                
                source_info = {
                    "folder_id": folder_id,
                    "source_type": "chunks" if use_chunks and chunks_count > 0 else "documents",
                    "file_count": len(documents),
                    "chunk_count": chunks_count,
                    "total_text_length": text_length
                }
            
            return source_info
            
        except Exception as e:
            logger.error(f"소스 정보 수집 실패: {e}")
            return {} 