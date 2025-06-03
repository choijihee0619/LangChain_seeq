"""
YouTube API 연동 모듈
MODIFIED 2024-01-20: YouTube 동영상 검색 및 메타데이터 수집 기능 추가
FIXED 2024-01-20: 동기/비동기 처리 오류 수정, 예외 처리 개선
"""
import os
import asyncio
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import httpx
from dotenv import load_dotenv
from utils.logger import get_logger

# 환경변수 로드
load_dotenv()

logger = get_logger(__name__)

class YouTubeAPI:
    """YouTube API 클래스"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        YouTube API 초기화
        
        Args:
            api_key: YouTube Data API v3 키
        """
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        
        # 디버깅 정보 출력
        logger.info(f"YouTube API 키 초기화 - 제공된 키: {'있음' if api_key else '없음'}")
        logger.info(f"환경변수에서 로드된 키: {'있음' if os.getenv('YOUTUBE_API_KEY') else '없음'}")
        if self.api_key:
            logger.info(f"최종 API 키 길이: {len(self.api_key)}")
            logger.info(f"API 키 시작 부분: {self.api_key[:10]}...")
        
        if not self.api_key:
            logger.warning("YouTube API 키가 설정되지 않았습니다. 환경변수 YOUTUBE_API_KEY를 확인하세요.")
            logger.warning("현재 .env 파일 위치에서 환경변수를 다시 로드합니다.")
        
        self.youtube = None
        self.executor = ThreadPoolExecutor(max_workers=3)  # 동기 API 호출용 스레드 풀
        
        if self.api_key:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)
                logger.info("YouTube API 초기화 완료")
            except Exception as e:
                logger.error(f"YouTube API 초기화 실패: {e}")

    def is_available(self) -> bool:
        """YouTube API 사용 가능 여부 확인"""
        return self.youtube is not None and self.api_key is not None

    async def search_videos(
        self,
        query: str,
        max_results: int = 10,
        order: str = "relevance",
        video_duration: str = "any",
        video_category_id: Optional[str] = None
    ) -> List[Dict]:
        """
        키워드로 YouTube 동영상 검색
        
        Args:
            query: 검색 키워드
            max_results: 최대 결과 수 (1-50)
            order: 정렬 방식 (relevance, date, rating, viewCount, title)
            video_duration: 동영상 길이 (any, short, medium, long)
            video_category_id: 카테고리 ID (선택)
            
        Returns:
            검색 결과 리스트
        """
        if not self.youtube:
            logger.error("YouTube API가 초기화되지 않았습니다.")
            return []
        
        try:
            # 동기 API 호출을 비동기로 실행
            loop = asyncio.get_event_loop()
            search_result = await loop.run_in_executor(
                self.executor,
                self._sync_search_videos,
                query, max_results, order, video_duration, video_category_id
            )
            
            if not search_result:
                return []
            
            video_ids = [item['id']['videoId'] for item in search_result.get('items', [])]
            
            if not video_ids:
                return []
            
            # 상세 정보 가져오기
            videos_details = await loop.run_in_executor(
                self.executor,
                self._sync_get_video_details,
                video_ids
            )
            
            # 결과 정리
            videos = []
            for item in videos_details.get('items', []):
                video_info = self._parse_video_info(item)  # 동기 함수로 변경
                if video_info:
                    videos.append(video_info)
            
            logger.info(f"YouTube 검색 완료: '{query}' - {len(videos)}개 결과")
            return videos
            
        except HttpError as e:
            error_reason = getattr(e, 'reason', 'Unknown error')
            logger.error(f"YouTube API 요청 실패: {error_reason}")
            return []
        except Exception as e:
            logger.error(f"YouTube 검색 중 오류: {e}")
            return []

    def _sync_search_videos(
        self, 
        query: str, 
        max_results: int, 
        order: str, 
        video_duration: str,
        video_category_id: Optional[str]
    ) -> Dict:
        """동기 방식 동영상 검색"""
        search_request = self.youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=min(max_results, 50),  # API 제한
            order=order,
            type='video',
            videoDuration=video_duration,
            regionCode='KR',  # 한국 지역 설정
            relevanceLanguage='ko'  # 한국어 우선
        )
        
        if video_category_id:
            search_request = search_request.list(videoCategoryId=video_category_id)
        
        return search_request.execute()

    def _sync_get_video_details(self, video_ids: List[str]) -> Dict:
        """동기 방식 동영상 상세 정보 조회"""
        return self.youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=','.join(video_ids)
        ).execute()

    def _parse_video_info(self, item: Dict) -> Optional[Dict]:
        """YouTube API 응답을 파싱하여 정리된 동영상 정보 반환 (동기 함수로 변경)"""
        try:
            snippet = item.get('snippet', {})
            statistics = item.get('statistics', {})
            content_details = item.get('contentDetails', {})
            
            # 썸네일 URL 선택 (고화질 우선)
            thumbnails = snippet.get('thumbnails', {})
            thumbnail_url = (
                thumbnails.get('maxres', {}).get('url') or
                thumbnails.get('high', {}).get('url') or
                thumbnails.get('medium', {}).get('url') or
                thumbnails.get('default', {}).get('url')
            )
            
            # 조회수 숫자 변환
            view_count = statistics.get('viewCount', '0')
            try:
                view_count = int(view_count)
            except (ValueError, TypeError):
                view_count = 0
            
            # 좋아요 수 변환
            like_count = statistics.get('likeCount', '0')
            try:
                like_count = int(like_count)
            except (ValueError, TypeError):
                like_count = 0
            
            # 동영상 길이 파싱 (ISO 8601 duration)
            duration = self._parse_duration(content_details.get('duration', ''))
            
            return {
                'video_id': item['id'],
                'title': snippet.get('title', '제목 없음'),
                'description': snippet.get('description', '')[:500],  # 설명 500자 제한
                'channel_title': snippet.get('channelTitle', ''),
                'channel_id': snippet.get('channelId', ''),
                'published_at': snippet.get('publishedAt', ''),
                'thumbnail_url': thumbnail_url,
                'view_count': view_count,
                'like_count': like_count,
                'duration': duration,
                'duration_seconds': self._duration_to_seconds(duration),
                'video_url': f"https://www.youtube.com/watch?v={item['id']}",
                'tags': snippet.get('tags', [])[:10],  # 태그 10개 제한
                'category_id': snippet.get('categoryId', ''),
                'default_language': snippet.get('defaultLanguage', ''),
                'content_type': 'youtube_video'
            }
            
        except Exception as e:
            logger.error(f"동영상 정보 파싱 실패: {e}")
            return None

    def _parse_duration(self, duration: str) -> str:
        """ISO 8601 duration을 읽기 쉬운 형식으로 변환"""
        if not duration or not duration.startswith('PT'):
            return "0:00"
        
        import re
        # PT15M33S 형식 파싱
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration)
        
        if not match:
            return "0:00"
        
        hours, minutes, seconds = match.groups()
        hours = int(hours) if hours else 0
        minutes = int(minutes) if minutes else 0
        seconds = int(seconds) if seconds else 0
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    def _duration_to_seconds(self, duration: str) -> int:
        """duration을 총 초 수로 변환"""
        if not duration or duration == "0:00":
            return 0
        
        parts = duration.split(':')
        try:
            if len(parts) == 3:  # H:M:S
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:  # M:S
                return int(parts[0]) * 60 + int(parts[1])
            else:
                return 0
        except (ValueError, IndexError):
            return 0

    async def get_video_categories(self, region_code: str = 'KR') -> Dict[str, str]:
        """
        YouTube 동영상 카테고리 목록 가져오기
        
        Args:
            region_code: 지역 코드 (기본: KR)
            
        Returns:
            카테고리 ID와 이름 매핑
        """
        if not self.youtube:
            return {}
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                self._sync_get_categories,
                region_code
            )
            
            categories = {}
            for item in response.get('items', []):
                categories[item['id']] = item['snippet']['title']
            
            return categories
            
        except Exception as e:
            logger.error(f"카테고리 조회 실패: {e}")
            return {}

    def _sync_get_categories(self, region_code: str) -> Dict:
        """동기 방식 카테고리 조회"""
        return self.youtube.videoCategories().list(
            part='snippet',
            regionCode=region_code
        ).execute()

    async def search_by_channel(
        self,
        channel_id: str,
        max_results: int = 10,
        order: str = "date"
    ) -> List[Dict]:
        """
        특정 채널의 동영상 검색
        
        Args:
            channel_id: YouTube 채널 ID
            max_results: 최대 결과 수
            order: 정렬 방식
            
        Returns:
            채널 동영상 리스트
        """
        if not self.youtube:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            search_result = await loop.run_in_executor(
                self.executor,
                self._sync_search_by_channel,
                channel_id, max_results, order
            )
            
            videos = []
            for item in search_result.get('items', []):
                video_info = self._parse_video_info(item)
                if video_info:
                    videos.append(video_info)
            
            return videos
            
        except Exception as e:
            logger.error(f"채널 검색 실패: {e}")
            return []

    def _sync_search_by_channel(self, channel_id: str, max_results: int, order: str) -> Dict:
        """동기 방식 채널 검색"""
        return self.youtube.search().list(
            channelId=channel_id,
            part='id,snippet',
            maxResults=min(max_results, 50),
            order=order,
            type='video'
        ).execute()

    def __del__(self):
        """소멸자 - 스레드 풀 정리"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

# 싱글톤 인스턴스
youtube_api = YouTubeAPI() 