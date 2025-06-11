"""
데이터베이스 연결 모듈
MongoDB 연결 관리
MODIFIED 2024-12-20: 새로운 컬렉션 구조에 맞게 인덱스 재설계
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseConnection:
    """데이터베이스 연결 클래스"""
    
    def __init__(self):
        self.client: AsyncIOMotorClient = None
        self.db: AsyncIOMotorDatabase = None
    
    async def connect(self):
        """데이터베이스 연결"""
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URI)
            self.db = self.client[settings.MONGODB_DB_NAME]
            
            # 연결 테스트
            await self.client.server_info()
            logger.info("MongoDB 연결 성공")
            
            # 인덱스 생성
            await self.create_indexes()
            
        except Exception as e:
            logger.error(f"MongoDB 연결 실패: {e}")
            raise
    
    async def disconnect(self):
        """데이터베이스 연결 해제"""
        if self.client is not None:
            self.client.close()
            logger.info("MongoDB 연결 해제")
    
    async def create_indexes(self):
        """필요한 인덱스 생성"""
        try:
            # folders 컬렉션 인덱스
            await self.db.folders.create_index("folder_type")
            await self.db.folders.create_index("title")
            await self.db.folders.create_index("created_at")
            await self.db.folders.create_index("last_accessed_at")
            
            # documents 컬렉션 인덱스 (새로운 구조)
            await self.db.documents.create_index("folder_id")
            await self.db.documents.create_index("chunk_sequence")
            await self._create_text_index("documents", "raw_text")
            await self.db.documents.create_index("created_at")
            
            # chunks 컬렉션 인덱스 (기존 유지하되 개선)
            await self.db.chunks.create_index("folder_id")
            await self.db.chunks.create_index("document_id")
            await self.db.chunks.create_index("file_id")
            await self.db.chunks.create_index("sequence")
            await self._create_text_index("chunks", "text")
            
            # summaries 컬렉션 인덱스 (새로 추가)
            await self.db.summaries.create_index("folder_id")
            await self.db.summaries.create_index("document_ids")
            await self.db.summaries.create_index("summary_type")
            await self.db.summaries.create_index("created_at")
            await self.db.summaries.create_index("cache_key", unique=True)
            
            # qapairs 컬렉션 인덱스 (개선)
            await self.db.qapairs.create_index("folder_id")
            await self.db.qapairs.create_index("source_document_id")
            await self.db.qapairs.create_index("difficulty")
            await self.db.qapairs.create_index("quiz_type")
            await self.db.qapairs.create_index("topic")
            await self.db.qapairs.create_index("created_at")
            
            # recommendations 컬렉션 인덱스 (새로 추가)
            await self.db.recommendations.create_index("folder_id")
            await self.db.recommendations.create_index("keywords")
            await self.db.recommendations.create_index("content_types")
            await self.db.recommendations.create_index("created_at")
            await self.db.recommendations.create_index("cache_key", unique=True)
            
            # labels 컬렉션 인덱스 (자동 라벨링용)
            await self.db.labels.create_index("folder_id")
            await self.db.labels.create_index("document_id")
            await self.db.labels.create_index("tags")
            await self.db.labels.create_index("category")
            await self.db.labels.create_index("confidence_score")
            await self.db.labels.create_index("created_at")
            
            # quiz_sessions 컬렉션 인덱스 (QA 기능용 - 새로 추가)
            await self.db.quiz_sessions.create_index("session_id", unique=True)
            await self.db.quiz_sessions.create_index("folder_id")
            await self.db.quiz_sessions.create_index("quiz_topic")
            await self.db.quiz_sessions.create_index("submitted_at")
            await self.db.quiz_sessions.create_index("percentage")
            await self.db.quiz_sessions.create_index("grade")
            await self.db.quiz_sessions.create_index("created_at")
            
            # quiz_submissions 컬렉션 인덱스 (QA 기능용 - 새로 추가)
            await self.db.quiz_submissions.create_index("session_id")
            await self.db.quiz_submissions.create_index("question_id")
            await self.db.quiz_submissions.create_index("quiz_type")
            await self.db.quiz_submissions.create_index("is_correct")
            await self.db.quiz_submissions.create_index("question_order")
            await self.db.quiz_submissions.create_index("created_at")
            
            # reports 컬렉션 인덱스 (보고서 기능용 - 새로 추가)
            await self.db.reports.create_index("report_id", unique=True)
            await self.db.reports.create_index("folder_id")
            await self.db.reports.create_index("title")
            await self.db.reports.create_index("created_at")
            await self.db.reports.create_index("updated_at")
            await self._create_text_index("reports", "title")
            
            # memos 컬렉션 인덱스 (메모 기능용 - 새로 추가)
            await self.db.memos.create_index("folder_id")
            await self.db.memos.create_index("title")
            await self.db.memos.create_index("tags")
            await self.db.memos.create_index("created_at")
            await self.db.memos.create_index("updated_at")
            await self._create_text_index("memos", "content")
            
            # highlights 컬렉션 인덱스 (하이라이트 기능용 - 새로 추가)
            await self.db.highlights.create_index("file_id")
            await self.db.highlights.create_index("folder_id")
            await self.db.highlights.create_index("start_offset")
            await self.db.highlights.create_index("end_offset")
            await self.db.highlights.create_index([("file_id", 1), ("start_offset", 1), ("end_offset", 1)], unique=True)
            await self.db.highlights.create_index("color")
            await self.db.highlights.create_index("created_at")
            await self._create_text_index("highlights", "highlight_text")
            
            logger.info("인덱스 생성 완료")
            
        except Exception as e:
            logger.error(f"인덱스 생성 실패: {e}")
    
    async def _create_text_index(self, collection_name: str, field_name: str):
        """텍스트 인덱스 안전 생성"""
        try:
            collection = self.db[collection_name]
            
            # 기존 텍스트 인덱스 확인
            indexes = await collection.list_indexes().to_list(None)
            text_indexes = [idx for idx in indexes if idx.get('key', {}).get('_fts') == 'text']
            
            # 원하는 필드의 텍스트 인덱스가 이미 있는지 확인
            desired_index_exists = False
            for idx in text_indexes:
                weights = idx.get('weights', {})
                if field_name in weights and len(weights) == 1:
                    desired_index_exists = True
                    break
            
            if desired_index_exists:
                logger.info(f"{collection_name}.{field_name} 텍스트 인덱스가 이미 존재함")
                return
            
            # 다른 필드의 텍스트 인덱스가 있으면 삭제
            for idx in text_indexes:
                weights = idx.get('weights', {})
                if field_name not in weights or len(weights) > 1:
                    index_name = idx.get('name', '')
                    if index_name:
                        logger.info(f"기존 텍스트 인덱스 삭제: {collection_name}.{index_name}")
                        await collection.drop_index(index_name)
            
            # 새 텍스트 인덱스 생성
            await collection.create_index([(field_name, "text")])
            logger.info(f"{collection_name}.{field_name} 텍스트 인덱스 생성 완료")
            
        except Exception as e:
            logger.warning(f"{collection_name}.{field_name} 텍스트 인덱스 생성 실패: {e}")
            # 텍스트 인덱스 실패는 치명적이지 않으므로 경고만 출력

# 싱글톤 인스턴스
db_connection = DatabaseConnection()

async def init_db():
    """데이터베이스 초기화"""
    await db_connection.connect()

async def close_db():
    """데이터베이스 종료"""
    await db_connection.disconnect()

async def get_database() -> AsyncIOMotorDatabase:
    """데이터베이스 인스턴스 반환"""
    if db_connection.db is None:
        await init_db()
    return db_connection.db

async def get_db() -> AsyncIOMotorDatabase:
    """get_database의 별칭 (간편 사용용)"""
    return await get_database()
