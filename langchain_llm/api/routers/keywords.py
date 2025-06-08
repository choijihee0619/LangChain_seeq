"""
키워드 추출 API 라우터
MODIFIED 2024-01-21: TextCollector 유틸리티 적용하여 중복 코드 제거
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from ai_processing.auto_labeler import AutoLabeler
from database.connection import get_database
from utils.logger import get_logger
from utils.text_collector import TextCollector

logger = get_logger(__name__)
router = APIRouter()

class KeywordsRequest(BaseModel):
    """키워드 추출 요청 모델 - 직접 텍스트 입력"""
    text: str
    max_keywords: int = 10

class FileKeywordsRequest(BaseModel):
    """파일 기반 키워드 추출 요청 모델"""
    file_id: Optional[str] = None
    folder_id: Optional[str] = None
    max_keywords: int = 10
    use_chunks: bool = True  # True: 청크들에서 추출, False: 원본 문서에서 추출

class KeywordsResponse(BaseModel):
    """키워드 추출 응답 모델"""
    keywords: List[str]
    count: int
    source_info: Optional[dict] = None  # 소스 정보 (파일명, 청크 수 등)

@router.post("/", response_model=KeywordsResponse)
async def extract_keywords(request: KeywordsRequest):
    """키워드 추출 엔드포인트 - 직접 텍스트 입력"""
    try:
        labeler = AutoLabeler()
        
        # 키워드 추출
        keywords = await labeler.extract_keywords(
            text=request.text,
            max_keywords=request.max_keywords
        )
        
        return KeywordsResponse(
            keywords=keywords,
            count=len(keywords)
        )
        
    except Exception as e:
        logger.error(f"키워드 추출 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/from-file", response_model=KeywordsResponse)
async def extract_keywords_from_file(request: FileKeywordsRequest):
    """파일에서 키워드 추출 엔드포인트"""
    try:
        db = await get_database()
        labeler = AutoLabeler()
        
        # TextCollector를 사용하여 텍스트 수집
        combined_text = ""
        if request.file_id:
            combined_text = await TextCollector.get_text_from_file(
                db, request.file_id, request.use_chunks
            )
            if not combined_text.strip():
                raise HTTPException(status_code=404, detail="해당 파일의 텍스트를 찾을 수 없습니다.")
        
        elif request.folder_id:
            combined_text = await TextCollector.get_text_from_folder(
                db, request.folder_id, request.use_chunks
            )
            if not combined_text.strip():
                raise HTTPException(status_code=404, detail="해당 폴더에 텍스트가 없습니다.")
        
        else:
            raise HTTPException(status_code=400, detail="file_id 또는 folder_id 중 하나는 필수입니다.")
        
        # 텍스트가 너무 긴 경우 제한 (키워드 추출 성능을 위해)
        if len(combined_text) > 10000:
            combined_text = combined_text[:10000] + "..."
            logger.warning("텍스트가 너무 길어 10000자로 제한했습니다.")
        
        # 소스 정보 수집
        source_info = await TextCollector.get_source_info(
            db, request.file_id, request.folder_id, request.use_chunks
        )
        
        # 키워드 추출
        keywords = await labeler.extract_keywords(
            text=combined_text,
            max_keywords=request.max_keywords
        )
        
        return KeywordsResponse(
            keywords=keywords,
            count=len(keywords),
            source_info=source_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 기반 키워드 추출 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/from-folder", response_model=KeywordsResponse)
async def extract_keywords_from_folder(folder_id: str, max_keywords: int = 10, use_chunks: bool = True):
    """폴더에서 키워드 추출 엔드포인트 (간단한 API)"""
    request = FileKeywordsRequest(
        folder_id=folder_id,
        max_keywords=max_keywords,
        use_chunks=use_chunks
    )
    return await extract_keywords_from_file(request)
