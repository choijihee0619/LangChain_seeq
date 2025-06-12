"""
추천 API 라우터
MODIFIED 2024-01-20: YouTube 연동 옵션 추가 및 응답 모델 확장
FIXED 2024-01-20: YouTube 동영상 저장 API 수정
ENHANCED 2024-01-21: 업로드된 파일 기반 자동 추천 기능 추가
CLEANED 2024-01-21: 불필요한 YouTube 개별 API 제거, 핵심 기능만 유지
OPTIMIZED 2024-01-21: 디버그 엔드포인트 제거, 프로덕션 준비 완료
ENHANCED 2024-12-20: 캐시 관리 및 folder_id 지원 추가
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from api.chains.recommend_chain import RecommendChain
from database.connection import get_database
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

class RecommendRequest(BaseModel):
    """추천 요청 모델"""
    keywords: Optional[List[str]] = []  # Optional로 변경, 기본값은 빈 리스트
    content_types: List[str] = ["book", "movie", "youtube_video"]
    max_items: int = 10
    include_youtube: bool = True  # YouTube 검색 포함 여부
    youtube_max_per_keyword: int = 3  # 키워드당 YouTube 결과 수
    folder_id: Optional[str] = None  # 폴더 ID 추가

class FileBasedRecommendRequest(BaseModel):
    """파일 기반 추천 요청 모델"""
    file_id: Optional[str] = None  # 특정 파일 ID
    folder_id: Optional[str] = None  # 폴더 ID (폴더 내 모든 파일)
    content_types: List[str] = ["book", "movie", "youtube_video"]
    max_items: int = 10
    include_youtube: bool = True
    youtube_max_per_keyword: int = 3
    max_keywords: int = 5  # 추출할 최대 키워드 수

class RecommendItem(BaseModel):
    """추천 항목 모델"""
    title: str
    content_type: str
    description: Optional[str]
    source: str
    metadata: Dict
    keyword: Optional[str] = None  # 어떤 키워드로 검색된 항목인지
    recommendation_source: Optional[str] = None  # 추천 소스 (database, youtube_realtime, fallback)

class RecommendResponse(BaseModel):
    """추천 응답 모델"""
    recommendations: List[RecommendItem]
    total_count: int
    youtube_included: bool  # YouTube 결과 포함 여부
    sources_summary: Dict  # 소스별 개수 요약
    extracted_keywords: Optional[List[str]] = None  # 자동 추출된 키워드 (파일 기반 추천에서만)
    from_cache: Optional[bool] = False  # 캐시 사용 여부 추가

class CachedRecommendationItem(BaseModel):
    """캐시된 추천 항목 모델"""
    cache_id: str
    keywords: List[str]
    content_types: List[str]
    recommendation_count: int
    created_at: str
    last_accessed_at: str

class CachedRecommendationsResponse(BaseModel):
    """캐시된 추천 목록 응답 모델"""
    cached_recommendations: List[CachedRecommendationItem]
    total_count: int

@router.post("/", response_model=RecommendResponse)
async def get_recommendations(request: RecommendRequest):
    """키워드 기반 콘텐츠 추천 엔드포인트"""
    try:
        db = await get_database()
        recommend_chain = RecommendChain(db)
        
        # keywords가 비어있고 folder_id가 있으면 자동 추출
        keywords = request.keywords
        if not keywords and request.folder_id:
            logger.info(f"키워드가 비어있음. 폴더 {request.folder_id}의 labels.tags에서 자동 추출 시도")
            keywords = await recommend_chain.extract_keywords_from_folder_labels(
                request.folder_id
            )
            
            # 자동 추출도 실패한 경우 에러 처리
            if not keywords:
                raise HTTPException(
                    status_code=400,
                    detail=f"폴더 {request.folder_id}에서 키워드를 추출할 수 없습니다. 키워드를 직접 제공하거나 해당 폴더에 라벨링된 문서가 있는지 확인하세요."
                )
        elif not keywords:
            # folder_id도 없고 keywords도 없는 경우
            raise HTTPException(
                status_code=400,
                detail="키워드를 제공하거나 folder_id를 제공하여 자동 키워드 추출을 사용하세요."
            )
        
        logger.info(f"사용할 키워드: {keywords}")
        
        # 추천 생성
        result = await recommend_chain.process(
            keywords=keywords,  # 자동 추출되거나 원본 키워드 사용
            content_types=request.content_types,
            max_items=request.max_items,
            include_youtube=request.include_youtube,
            youtube_max_per_keyword=request.youtube_max_per_keyword,
            folder_id=request.folder_id  # 폴더 ID 추가
        )
        
        # 추천 항목 변환
        recommendations = []
        sources_count = {}
        youtube_count = 0
        
        for item in result["recommendations"]:
            recommendation = RecommendItem(
                title=item["title"],
                content_type=item["content_type"],
                description=item.get("description"),
                source=item["source"],
                metadata=item.get("metadata", {}),
                keyword=item.get("keyword"),
                recommendation_source=item.get("recommendation_source")
            )
            recommendations.append(recommendation)
            
            # 소스별 개수 집계
            source = item.get("recommendation_source", "unknown")
            sources_count[source] = sources_count.get(source, 0) + 1
            
            if item["content_type"] == "youtube_video":
                youtube_count += 1
        
        return RecommendResponse(
            recommendations=recommendations,
            total_count=len(recommendations),
            youtube_included=youtube_count > 0,
            sources_summary=sources_count,
            extracted_keywords=keywords if not request.keywords else None,  # 자동 추출된 경우만 반환
            from_cache=result.get("from_cache", False)  # 캐시 사용 여부 추가
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"추천 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/from-file", response_model=RecommendResponse)
async def get_file_based_recommendations(request: FileBasedRecommendRequest):
    """업로드된 파일 기반 자동 추천 엔드포인트 - 핵심 기능!"""
    try:
        # file_id 또는 folder_id 중 하나는 필수
        if not request.file_id and not request.folder_id:
            raise HTTPException(
                status_code=400, 
                detail="file_id 또는 folder_id 중 하나는 반드시 제공되어야 합니다"
            )
        
        db = await get_database()
        recommend_chain = RecommendChain(db)
        
        # 1. 파일에서 키워드 자동 추출
        extracted_keywords = await recommend_chain.extract_keywords_from_file(
            file_id=request.file_id,
            folder_id=request.folder_id,
            max_keywords=request.max_keywords
        )
        
        if not extracted_keywords:
            raise HTTPException(
                status_code=404, 
                detail="파일에서 키워드를 추출할 수 없습니다. 파일이 존재하고 처리되었는지 확인하세요."
            )
        
        logger.info(f"파일에서 추출된 키워드: {extracted_keywords}")
        
        # 2. 추출된 키워드로 추천 생성
        result = await recommend_chain.process(
            keywords=extracted_keywords,
            content_types=request.content_types,
            max_items=request.max_items,
            include_youtube=request.include_youtube,
            youtube_max_per_keyword=request.youtube_max_per_keyword,
            folder_id=request.folder_id  # 폴더 ID 전달
        )
        
        # 3. 추천 항목 변환
        recommendations = []
        sources_count = {}
        youtube_count = 0
        
        for item in result["recommendations"]:
            recommendation = RecommendItem(
                title=item["title"],
                content_type=item["content_type"],
                description=item.get("description"),
                source=item["source"],
                metadata=item.get("metadata", {}),
                keyword=item.get("keyword"),
                recommendation_source=item.get("recommendation_source")
            )
            recommendations.append(recommendation)
            
            # 소스별 개수 집계
            source = item.get("recommendation_source", "unknown")
            sources_count[source] = sources_count.get(source, 0) + 1
            
            if item["content_type"] == "youtube_video":
                youtube_count += 1
        
        return RecommendResponse(
            recommendations=recommendations,
            total_count=len(recommendations),
            youtube_included=youtube_count > 0,
            sources_summary=sources_count,
            extracted_keywords=extracted_keywords,  # 추출된 키워드도 함께 반환
            from_cache=result.get("from_cache", False)  # 캐시 사용 여부 추가
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 기반 추천 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cached", response_model=CachedRecommendationsResponse)
async def get_cached_recommendations(folder_id: Optional[str] = None, limit: int = 10):
    """캐시된 추천 목록 조회 엔드포인트"""
    try:
        db = await get_database()
        recommend_chain = RecommendChain(db)
        
        cached_recs = await recommend_chain.get_cached_recommendations(folder_id, limit)
        
        return CachedRecommendationsResponse(
            cached_recommendations=[
                CachedRecommendationItem(
                    cache_id=item["cache_id"],
                    keywords=item["keywords"],
                    content_types=item["content_types"],
                    recommendation_count=item["recommendation_count"],
                    created_at=str(item["created_at"]),
                    last_accessed_at=str(item["last_accessed_at"])
                )
                for item in cached_recs
            ],
            total_count=len(cached_recs)
        )
        
    except Exception as e:
        logger.error(f"캐시된 추천 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cached/{cache_id}")
async def delete_recommendation_cache(cache_id: str):
    """추천 캐시 삭제 엔드포인트"""
    try:
        db = await get_database()
        recommend_chain = RecommendChain(db)
        
        success = await recommend_chain.delete_recommendation_cache(cache_id)
        
        if success:
            return {"success": True, "message": "추천 캐시가 삭제되었습니다."}
        else:
            raise HTTPException(status_code=404, detail="추천 캐시를 찾을 수 없습니다.")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"추천 캐시 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
