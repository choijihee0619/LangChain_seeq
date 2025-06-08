"""
로깅 모듈
애플리케이션 로깅 설정
"""
import sys
from loguru import logger
from config.settings import settings

def setup_logger():
    """로거 설정"""
    # 기본 로거 제거
    logger.remove()
    
    # 콘솔 출력 설정
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # 파일 출력 설정
    logger.add(
        "logs/app.log",
        level=settings.LOG_LEVEL,
        rotation="1 day",
        retention="7 days",
        compression="zip"
    )
    
    return logger

def get_logger(name: str):
    """모듈별 로거 반환"""
    return logger.bind(name=name)
