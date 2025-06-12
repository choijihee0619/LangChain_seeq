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
            
            # 3. 기존 DB에서 저장된 추천 검색
            db_recommendations = await self._search_db_recommendations(
                keywords, content_types, max_items
            )
            recommendations.extend(db_recommendations)
            
            # 4. YouTube 실시간 검색 (include_youtube가 True이고 video 관련 타입이 포함된 경우)
            if include_youtube and ("video" in content_types or "youtube_video" in content_types):
                youtube_recommendations = await self._search_youtube_recommendations(
                    keywords, youtube_max_per_keyword
                )
                recommendations.extend(youtube_recommendations)
            
            # 5. 웹 검색 기반 실시간 추천 (book, movie, video 타입)
            web_recommendations = await self._search_web_recommendations(
                keywords, content_types, max_items
            )
            recommendations.extend(web_recommendations)
            
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
            
            for keyword in keywords[:5]:  # 최대 5개 키워드 처리 (모든 키워드)
                # 도서 추천
                if "book" in content_types:
                    books = await web_recommendation_engine.search_books(
                        keyword, max_results=max_per_type
                    )
                    # 키워드 필드 추가
                    for book in books:
                        book["keyword"] = keyword
                    recommendations.extend(books)
                
                # 영화 추천  
                if "movie" in content_types:
                    movies = await web_recommendation_engine.search_movies(
                        keyword, max_results=max_per_type
                    )
                    # 키워드 필드 추가
                    for movie in movies:
                        movie["keyword"] = keyword
                    recommendations.extend(movies)
            
            logger.info(f"웹에서 {len(recommendations)}개 추천 검색")
            return recommendations
            
        except Exception as e:
            logger.warning(f"웹 추천 검색 실패: {e}")
            return []

    def _balance_recommendations(
        self,
        recommendations: List[Dict],
        keywords: List[str],
        max_items: int
    ) -> List[Dict]:
        """추천 항목들을 키워드별로 균등하게 분배"""
        try:
            if not recommendations:
                return []
            
            # 키워드별로 그룹화
            keyword_groups = {}
            for rec in recommendations:
                keyword = rec.get("keyword", "unknown")
                if keyword not in keyword_groups:
                    keyword_groups[keyword] = []
                keyword_groups[keyword].append(rec)
            
            logger.info(f"키워드 그룹화 결과: {[(k, len(v)) for k, v in keyword_groups.items()]}")
            
            # 균등 분배 (더 관대하게)
            balanced = []
            max_per_keyword = max(2, max_items // len(keyword_groups))  # 최소 2개씩
            logger.info(f"키워드당 최대 개수: {max_per_keyword}")
            
            # 키워드별 분배 후 여유 공간이 있으면 추가로 채움
            for keyword, recs in keyword_groups.items():
                selected = recs[:max_per_keyword]
                logger.info(f"키워드 '{keyword}'에서 {len(selected)}개 선택")
                balanced.extend(selected)
            
            # 여유가 있으면 남은 추천들로 채우기
            if len(balanced) < max_items:
                remaining_slots = max_items - len(balanced)
                used_recs = set(id(rec) for rec in balanced)
                
                for keyword, recs in keyword_groups.items():
                    for rec in recs[max_per_keyword:]:
                        if id(rec) not in used_recs and len(balanced) < max_items:
                            balanced.append(rec)
                            used_recs.add(id(rec))
            
            # 소스별 다양성 확보 (웹 추천의 경우 제한 완화)
            final_balanced = []
            source_count = {}
            
            for rec in balanced[:max_items]:
                source = rec.get("recommendation_source", "unknown")
                count = source_count.get(source, 0)
                
                # 웹 추천(llm_realtime)의 경우 더 관대한 제한
                if source == "llm_realtime":
                    max_per_source = max_items  # 웹 추천은 제한 없음
                else:
                    max_per_source = max(2, max_items // 2)  # 다른 소스는 절반까지
                
                if count < max_per_source:
                    final_balanced.append(rec)
                    source_count[source] = count + 1
            
            logger.info(f"소스별 최종 분배: {[(k, v) for k, v in source_count.items()]}")
            return final_balanced
            
        except Exception as e:
            logger.warning(f"추천 균형화 실패: {e}")
            return recommendations[:max_items]

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
            text_collector = TextCollector(self.db)
            
            # 텍스트 수집
            combined_text = await text_collector.collect_text_from_file(
                file_id=file_id,
                folder_id=folder_id
            )
            
            if not combined_text:
                logger.warning(f"텍스트를 찾을 수 없습니다. file_id: {file_id}, folder_id: {folder_id}")
                return []
            
            # 키워드 추출
            keywords = await self.auto_labeler.extract_keywords(combined_text, max_keywords)
            
            logger.info(f"추출된 키워드: {keywords}")
            return keywords
            
        except Exception as e:
            logger.error(f"키워드 추출 실패: {e}")
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
