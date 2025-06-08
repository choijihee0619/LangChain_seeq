"""
설정 관리 모듈
환경 변수 로드 및 설정 값 관리
"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # OpenAI 설정
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    
    # MongoDB 설정
    MONGODB_URI: str
    MONGODB_DB_NAME: str = "rag_database"
    
    # OCR 데이터베이스 설정
    OCR_MONGODB_URI: Optional[str] = None
    OCR_DB_NAME: str = "ocr_db"
    
    # YouTube API 설정
    YOUTUBE_API_KEY: Optional[str] = None
    
    # API 설정
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # 청킹 설정
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    
    # 검색 설정
    DEFAULT_TOP_K: int = 5
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
