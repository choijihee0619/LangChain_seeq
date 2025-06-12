"""
추천 체인
콘텐츠 추천 생성
MODIFIED 2024-01-20: YouTube API 연동 추가 - 실시간 YouTube 동영상 추천 기능 통합
ENHANCED 2024-01-21: 파일 기반 키워드 자동 추출 기능 추가
CLEANED 2024-01-21: 불필요한 YouTube 개별 API 제거, 핵심 추천 기능만 유지
REFACTORED 2024-01-21: 키워드 추출 통합 및 TextCollector 적용
ENHANCED 2024-12-20: 추천 결과 캐싱 기능 추가 및 새 DB 구조 적용
"""
from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.operations import DatabaseOperations
from utils.logger import get_logger
from utils.youtube_api import youtube_api
from utils.text_collector import TextCollector
from ai_processing.auto_labeler import AutoLabeler
from utils.web_recommendation import web_recommendation_engine

logger = get_logger(__name__)

class RecommendChain:
    """추천 체인 클래스"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.db_ops = DatabaseOperations(db)
        self.recommendations = db.recommendations
        self.documents = db.documents  # documents 컬렉션 추가
        self.chunks = db.chunks        # chunks 컬렉션 추가
        self.file_info = db.file_info  # 새로운 file_info 컬렉션
        self.auto_labeler = AutoLabeler()  # AutoLabeler 초기화 추가
    
    async def process(
        self,
        keywords: List[str],
        content_types: List[str] = ["book", "movie", "youtube_video"],
        max_items: int = 10,
        include_youtube: bool = True,
        youtube_max_per_keyword: int = 3,
        folder_id: Optional[str] = None
    ) -> Dict:
        """
        추천 처리
        
        Args:
            keywords: 검색 키워드 리스트
            content_types: 콘텐츠 타입 리스트
            max_items: 최대 추천 항목 수
            include_youtube: YouTube 검색 포함 여부
            youtube_max_per_keyword: 키워드당 YouTube 결과 최대 수
            folder_id: 폴더 ID (캐싱 및 접근 시간 업데이트용)
        """
        try:
            # 1. 캐시 확인
            cached_recommendations = await self.db_ops.get_recommendation_cache(
                keywords=keywords,
                content_types=content_types,
                folder_id=folder_id
            )
            
            if cached_recommendations:
                logger.info("캐시된 추천 발견, 캐시 사용")
                # 폴더 접근 시간 업데이트
                if folder_id:
                    await self.db_ops.update_folder_access(folder_id)
                
                return {
                    "recommendations": cached_recommendations["recommendations"],
                    "from_cache": True,
                    "cache_created_at": cached_recommendations.get("created_at")
                }
            
            # 2. 새로운 추천 생성
            recommendations = []
            logger.info(f"추천 생성 시작 - 키워드: {keywords}, 타입: {content_types}")
            
            # 3. 기존 DB에서 저장된 추천 검색
            db_recommendations = await self._search_db_recommendations(
                keywords, content_types, max_items
            )
            recommendations.extend(db_recommendations)
            logger.info(f"DB 추천: {len(db_recommendations)}개 추가")
            
            # 4. YouTube 실시간 검색 (include_youtube가 True이고 video 관련 타입이 포함된 경우)
            if include_youtube and ("video" in content_types or "youtube_video" in content_types):
                youtube_recommendations = await self._search_youtube_recommendations(
                    keywords, youtube_max_per_keyword
                )
                recommendations.extend(youtube_recommendations)
                logger.info(f"YouTube 추천: {len(youtube_recommendations)}개 추가")
            else:
                logger.info("YouTube 검색 건너뜀")
            
            # 5. 웹 검색 기반 실시간 추천 (book, movie, video 타입)
            web_recommendations = await self._search_web_recommendations(
                keywords, content_types, max_items
            )
            recommendations.extend(web_recommendations)
            logger.info(f"웹 추천: {len(web_recommendations)}개 추가")
            
            # 6. 결과 정렬 및 제한
            # 다양성을 위해 키워드별로 균등하게 분배
            final_recommendations = self._balance_recommendations(
                recommendations, keywords, max_items
            )
            
            # 7. 추천이 부족하고 실제 추천이 없는 경우에만 fallback 데이터 추가
            has_real_recommendations = any(
                rec.get("recommendation_source") in ["llm_realtime", "youtube_realtime", "database"]
                for rec in final_recommendations
            )
            
            if len(final_recommendations) < max_items and not has_real_recommendations:
                fallback_recommendations = self._generate_fallback_recommendations(keywords)
                final_recommendations.extend(fallback_recommendations)
            
            final_result = final_recommendations[:max_items]
            
            # 8. 추천 결과 캐싱 (빈 결과가 아닌 경우에만)
            if final_result:
                try:
                    await self.db_ops.save_recommendation_cache(
                        recommendations=final_result,
                        keywords=keywords,
                        content_types=content_types,
                        folder_id=folder_id
                    )
                    logger.info("추천 결과 캐시 저장 완료")
                except Exception as cache_error:
                    logger.warning(f"추천 캐시 저장 실패: {cache_error}")
            
            # 9. 폴더 접근 시간 업데이트
            if folder_id:
                await self.db_ops.update_folder_access(folder_id)
            
            return {
                "recommendations": final_result,
                "from_cache": False
            }
            
        except Exception as e:
            logger.error(f"추천 처리 실패: {e}")
            raise

    async def _search_db_recommendations(
        self,
        keywords: List[str],
        content_types: List[str],
        max_items: int
    ) -> List[Dict]:
        """저장된 추천에서 검색"""
        try:
            # MongoDB 텍스트 검색 사용
            search_query = " ".join(keywords)
            
            cursor = self.recommendations.find({
                "$text": {"$search": search_query},
                "content_type": {"$in": content_types}
            }).limit(max_items)
            
            recommendations = []
            async for doc in cursor:
                recommendations.append({
                    "title": doc["title"],
                    "content_type": doc["content_type"],
                    "description": doc.get("description"),
                    "source": doc.get("source", "database"),
                    "metadata": doc.get("metadata", {}),
                    "keyword": keywords[0] if keywords else "",
                    "recommendation_source": "database"
                })
            
            logger.info(f"DB에서 {len(recommendations)}개 추천 검색")
            return recommendations
            
        except Exception as e:
            logger.warning(f"DB 추천 검색 실패: {e}")
            return []

    async def _search_youtube_recommendations(
        self,
        keywords: List[str],
        max_per_keyword: int
    ) -> List[Dict]:
        """YouTube에서 실시간 추천 검색"""
        try:
            logger.info(f"YouTube API 상태 확인 중...")
            logger.info(f"YouTube API 사용 가능: {youtube_api.is_available()}")
            logger.info(f"YouTube API 키 존재: {youtube_api.api_key is not None}")
            logger.info(f"YouTube 객체 존재: {youtube_api.youtube is not None}")
            
            if not youtube_api.is_available():
                logger.warning("YouTube API를 사용할 수 없습니다.")
                return []
            
            recommendations = []
            
            for keyword in keywords:
                try:
                    logger.info(f"YouTube에서 '{keyword}' 검색 시작...")
                    videos = await youtube_api.search_videos(
                        query=keyword,
                        max_results=max_per_keyword,
                        order="relevance"
                    )
                    
                    for video in videos:
                        recommendations.append({
                            "title": video["title"],
                            "content_type": "youtube_video",
                            "description": video.get("description", "")[:200] + "...",
                            "source": video["video_url"],
                            "metadata": {
                                "channel": video.get("channel_title"),
                                "duration": video.get("duration"),
                                "view_count": video.get("view_count", 0),
                                "thumbnail": video.get("thumbnail_url")
                            },
                            "keyword": keyword,
                            "recommendation_source": "youtube_realtime"
                        })
                    
                    logger.info(f"YouTube에서 '{keyword}' 키워드로 {len(videos)}개 동영상 검색")
                    
                except Exception as e:
                    logger.warning(f"YouTube 검색 실패 (키워드: {keyword}): {e}")
                    continue
            
            return recommendations
            
        except Exception as e:
            logger.error(f"YouTube 추천 검색 실패: {e}")
            return []

    async def _search_web_recommendations(
        self,
        keywords: List[str],
        content_types: List[str],
        max_items: int
    ) -> List[Dict]:
        """웹 검색 기반 실시간 추천"""
        try:
            recommendations = []
            max_per_type = max(1, max_items // len(content_types))
            
            logger.info(f"웹 추천 시작 - 키워드: {keywords}, 타입: {content_types}")
            
            for keyword in keywords[:5]:  # 최대 5개 키워드 처리 (모든 키워드)
                logger.info(f"키워드 '{keyword}' 처리 중...")
                
                # 도서 추천
                if "book" in content_types:
                    try:
                        logger.info(f"도서 검색 시작: {keyword}")
                        books = await web_recommendation_engine.search_books(
                            keyword, max_results=max_per_type
                        )
                        logger.info(f"도서 검색 결과: {len(books)}개")
                        
                        # 키워드 필드 추가
                        for book in books:
                            book["keyword"] = keyword
                        recommendations.extend(books)
                        
                    except Exception as e:
                        logger.error(f"도서 검색 실패 ({keyword}): {e}")
                
                # 영화 추천  
                if "movie" in content_types:
                    try:
                        logger.info(f"영화 검색 시작: {keyword}")
                        movies = await web_recommendation_engine.search_movies(
                            keyword, max_results=max_per_type
                        )
                        logger.info(f"영화 검색 결과: {len(movies)}개")
                        
                        # 키워드 필드 추가
                        for movie in movies:
                            movie["keyword"] = keyword
                        recommendations.extend(movies)
                        
                    except Exception as e:
                        logger.error(f"영화 검색 실패 ({keyword}): {e}")
            
            logger.info(f"웹에서 총 {len(recommendations)}개 추천 검색 완료")
            
            # 추천 결과 상세 로깅
            type_count = {}
            for rec in recommendations:
                content_type = rec.get("content_type", "unknown")
                type_count[content_type] = type_count.get(content_type, 0) + 1
            logger.info(f"웹 추천 타입별 결과: {type_count}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"웹 추천 검색 전체 실패: {e}")
            return []

    def _balance_recommendations(
        self,
        recommendations: List[Dict],
        keywords: List[str],
        max_items: int
    ) -> List[Dict]:
        """추천 항목들을 콘텐츠 타입별로 균등하게 분배 (수정됨)"""
        try:
            if not recommendations:
                return []
            
            logger.info(f"균형화 전 총 추천 수: {len(recommendations)}")
            
            # 콘텐츠 타입별로 그룹화 (우선 순위 기반)
            content_type_groups = {
                "book": [],
                "movie": [], 
                "youtube_video": [],
                "video": [],
                "other": []
            }
            
            for rec in recommendations:
                content_type = rec.get("content_type", "other")
                if content_type in content_type_groups:
                    content_type_groups[content_type].append(rec)
                else:
                    content_type_groups["other"].append(rec)
            
            # 각 타입별 추천 수 로깅
            for content_type, recs in content_type_groups.items():
                if recs:
                    logger.info(f"{content_type}: {len(recs)}개")
            
            # 타입별 균등 분배 (book, movie를 우선적으로 포함)
            balanced = []
            
            # 1단계: 각 타입에서 최소 1개씩 선택 (book, movie 우선)
            priority_types = ["book", "movie", "youtube_video", "video"]
            items_per_type = max(1, max_items // len(priority_types))
            
            logger.info(f"타입별 기본 할당: {items_per_type}개씩")
            
            for content_type in priority_types:
                type_recs = content_type_groups[content_type]
                if type_recs:
                    # 키워드별로 다양성 확보
                    selected = self._select_diverse_by_keyword(type_recs, items_per_type)
                    balanced.extend(selected)
                    logger.info(f"{content_type}에서 {len(selected)}개 선택")
            
            # 2단계: 남은 자리가 있으면 추가 선택 (book, movie 우선)
            if len(balanced) < max_items:
                remaining_slots = max_items - len(balanced)
                used_ids = set(id(rec) for rec in balanced)
                
                # book, movie를 우선적으로 추가
                for content_type in ["book", "movie", "youtube_video", "video"]:
                    if remaining_slots <= 0:
                        break
                        
                    type_recs = content_type_groups[content_type]
                    unused_recs = [rec for rec in type_recs if id(rec) not in used_ids]
                    
                    additional_count = min(remaining_slots, len(unused_recs))
                    if additional_count > 0:
                        additional = unused_recs[:additional_count]
                        balanced.extend(additional)
                        remaining_slots -= additional_count
                        
                        for rec in additional:
                            used_ids.add(id(rec))
                        
                        logger.info(f"{content_type}에서 추가로 {len(additional)}개 선택")
            
            # 최종 결과 로깅
            final_type_count = {}
            for rec in balanced:
                content_type = rec.get("content_type", "unknown")
                final_type_count[content_type] = final_type_count.get(content_type, 0) + 1
            
            logger.info(f"최종 타입별 분배: {final_type_count}")
            return balanced[:max_items]
            
        except Exception as e:
            logger.warning(f"추천 균형화 실패: {e}")
            return recommendations[:max_items]
    
    def _select_diverse_by_keyword(self, recommendations: List[Dict], max_count: int) -> List[Dict]:
        """키워드별로 다양성을 확보하여 추천 선택"""
        if not recommendations:
            return []
        
        # 키워드별로 그룹화
        keyword_groups = {}
        for rec in recommendations:
            keyword = rec.get("keyword", "unknown")
            if keyword not in keyword_groups:
                keyword_groups[keyword] = []
            keyword_groups[keyword].append(rec)
        
        # 각 키워드에서 골고루 선택
        selected = []
        keyword_list = list(keyword_groups.keys())
        keyword_idx = 0
        
        while len(selected) < max_count and any(keyword_groups.values()):
            keyword = keyword_list[keyword_idx % len(keyword_list)]
            
            if keyword_groups[keyword]:
                selected.append(keyword_groups[keyword].pop(0))
            
            keyword_idx += 1
            
            # 모든 키워드 그룹이 비었으면 종료
            if all(not group for group in keyword_groups.values()):
                break
        
        return selected

    def _generate_fallback_recommendations(self, keywords: List[str]) -> List[Dict]:
        """기본 추천 생성 (검색 결과가 부족할 때)"""
        try:
            fallback_items = []
            
            for i, keyword in enumerate(keywords[:3]):
                fallback_items.extend([
                    {
                        "title": f"{keyword} 관련 추천 도서",
                        "content_type": "book",
                        "description": f"{keyword}에 대해 더 알아볼 수 있는 도서를 찾아보세요.",
                        "source": "fallback",
                        "metadata": {"type": "fallback"},
                        "keyword": keyword,
                        "recommendation_source": "fallback"
                    },
                    {
                        "title": f"{keyword} 관련 영상",
                        "content_type": "youtube_video",
                        "description": f"{keyword}에 대한 유용한 영상을 검색해보세요.",
                        "source": "fallback",
                        "metadata": {"type": "fallback"},
                        "keyword": keyword,
                        "recommendation_source": "fallback"
                    }
                ])
            
            return fallback_items
            
        except Exception as e:
            logger.warning(f"기본 추천 생성 실패: {e}")
            return []

    async def extract_keywords_from_file(
        self,
        file_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        max_keywords: int = 5
    ) -> List[str]:
        """파일에서 키워드 자동 추출"""
        try:
            logger.info(f"키워드 추출 시작 - file_id: {file_id}, folder_id: {folder_id}")
            
            # 텍스트 수집
            combined_text = ""
            
            if file_id:
                logger.info(f"파일 ID {file_id}에서 텍스트 수집 중...")
                combined_text = await TextCollector.get_text_from_file(
                    db=self.db,
                    file_id=file_id,
                    use_chunks=True
                )
                logger.info(f"파일에서 수집된 텍스트 길이: {len(combined_text)}")
                
            elif folder_id:
                logger.info(f"폴더 ID {folder_id}에서 텍스트 수집 중...")
                combined_text = await TextCollector.get_text_from_folder(
                    db=self.db,
                    folder_id=folder_id,
                    use_chunks=True
                )
                logger.info(f"폴더에서 수집된 텍스트 길이: {len(combined_text)}")
            
            if not combined_text or not combined_text.strip():
                logger.warning(f"수집된 텍스트가 비어있음. file_id: {file_id}, folder_id: {folder_id}")
                
                # 청크가 없을 수도 있으니 문서에서 직접 시도
                if file_id:
                    logger.info("청크에서 텍스트를 찾을 수 없어 문서에서 직접 시도...")
                    combined_text = await TextCollector.get_text_from_file(
                        db=self.db,
                        file_id=file_id,
                        use_chunks=False
                    )
                    logger.info(f"문서에서 직접 수집된 텍스트 길이: {len(combined_text)}")
                elif folder_id:
                    logger.info("청크에서 텍스트를 찾을 수 없어 문서에서 직접 시도...")
                    combined_text = await TextCollector.get_text_from_folder(
                        db=self.db,
                        folder_id=folder_id,
                        use_chunks=False
                    )
                    logger.info(f"문서에서 직접 수집된 텍스트 길이: {len(combined_text)}")
                
                if not combined_text or not combined_text.strip():
                    logger.error(f"최종적으로 텍스트를 찾을 수 없음. file_id: {file_id}, folder_id: {folder_id}")
                    return []
            
            # 소스 정보 로깅
            source_info = await TextCollector.get_source_info(
                db=self.db,
                file_id=file_id,
                folder_id=folder_id,
                use_chunks=True
            )
            logger.info(f"소스 정보: {source_info}")
            
            # 키워드 추출
            logger.info("LLM을 사용하여 키워드 추출 중...")
            keywords = await self.auto_labeler.extract_keywords(combined_text, max_keywords)
            
            logger.info(f"추출된 키워드: {keywords}")
            return keywords
            
        except Exception as e:
            logger.error(f"키워드 추출 실패: {e}", exc_info=True)
            return []

    async def extract_keywords_from_folder_labels(self, folder_id: str) -> List[str]:
        """폴더 ID로부터 labels.tags 추출하여 키워드로 사용"""
        try:
            # labels 컬렉션에서 해당 폴더의 모든 태그 수집
            cursor = self.db.labels.find({"folder_id": folder_id})
            
            tag_frequency = {}
            async for label_doc in cursor:
                # labels.labels.tags 구조에서 태그 추출
                labels = label_doc.get("labels", {})
                tags = labels.get("tags", [])
                
                # tags가 리스트가 아닌 경우 처리
                if isinstance(tags, str):
                    tags = [tags]
                elif not isinstance(tags, list):
                    continue
                    
                for tag in tags:
                    if isinstance(tag, str) and len(tag) >= 2:  # 2글자 이상만
                        # 최소한의 필터링: 정말 의미 없는 태그만 제외
                        excluded_tags = ["문서", "파일", "텍스트", "자료", "기타"]
                        if tag.lower() not in excluded_tags:
                            tag_frequency[tag] = tag_frequency.get(tag, 0) + 1
            
            # 빈도순 정렬하여 상위 5개 선택
            sorted_tags = sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)
            keywords = [tag for tag, freq in sorted_tags[:5]]
            
            logger.info(f"폴더 {folder_id}에서 추출된 키워드: {keywords} (총 {len(tag_frequency)}개 태그 중)")
            return keywords
            
        except Exception as e:
            logger.warning(f"폴더 라벨에서 키워드 추출 실패: {e}")
            return []

    async def get_cached_recommendations(self, folder_id: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """캐시된 추천 목록 조회"""
        try:
            filter_dict = {}
            if folder_id:
                filter_dict["folder_id"] = folder_id
            
            cached_recs = await self.db_ops.find_many(
                "recommendations", 
                filter_dict, 
                limit=limit
            )
            
            return [
                {
                    "cache_id": str(rec["_id"]),
                    "keywords": rec.get("keywords", []),
                    "content_types": rec.get("content_types", []),
                    "recommendation_count": len(rec.get("recommendations", [])),
                    "created_at": rec["created_at"],
                    "last_accessed_at": rec["last_accessed_at"]
                }
                for rec in cached_recs
            ]
            
        except Exception as e:
            logger.error(f"캐시된 추천 목록 조회 실패: {e}")
            return []
    
    async def delete_recommendation_cache(self, cache_id: str) -> bool:
        """추천 캐시 삭제"""
        try:
            from bson import ObjectId
            return await self.db_ops.delete_one("recommendations", {"_id": ObjectId(cache_id)})
        except Exception as e:
            logger.error(f"추천 캐시 삭제 실패: {e}")
            return False
