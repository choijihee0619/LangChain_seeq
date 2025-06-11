"""
RAG 백엔드 메인 애플리케이션
FastAPI 서버 초기화 및 라우터 설정
"""
import os
import sys
from pathlib import Path

# 현재 파일의 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from dotenv import load_dotenv

# 환경변수 로드 (최우선)
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from config.settings import settings
from database.connection import init_db, close_db
from api.routers import query, summary, quiz, keywords, mindmap, recommend, upload, folders
from api.routers import ocr_bridge, quiz_qa, reports
from api.routers import memos, highlights
from utils.logger import setup_logger

# 로거 설정
logger = setup_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시
    logger.info("RAG 백엔드 서버 시작...")
    logger.info(f"YouTube API 키 설정 상태: {'설정됨' if os.getenv('YOUTUBE_API_KEY') else '설정 안됨'}")
    logger.info(f"OCR DB 연결 설정 상태: {'설정됨' if settings.OCR_MONGODB_URI else '기본값 사용'}")
    await init_db()
    yield
    # 종료 시
    await close_db()
    logger.info("RAG 백엔드 서버 종료")

# FastAPI 앱 생성
app = FastAPI(
    title="RAG 백엔드 API (AgentHub 통합)",
    description="OpenAI GPT-4o-mini와 MongoDB를 활용한 RAG 시스템 - AgentHub 지원",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(folders.router, prefix="/folders", tags=["Folders"])
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(summary.router, prefix="/summary", tags=["Summary"])
app.include_router(quiz.router, prefix="/quiz", tags=["Quiz"])
app.include_router(quiz_qa.router, prefix="/quiz-qa", tags=["Quiz QA"])
app.include_router(keywords.router, prefix="/keywords", tags=["Keywords"])
app.include_router(mindmap.router, prefix="/mindmap", tags=["Mindmap"])
app.include_router(recommend.router, prefix="/recommend", tags=["Recommend"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(memos.router, prefix="/memos", tags=["Memos"])
app.include_router(highlights.router, prefix="/highlights", tags=["Highlights"])
app.include_router(ocr_bridge.router, prefix="/ocr-bridge", tags=["OCR Bridge"])

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "RAG 백엔드 API",
        "version": "1.0.0",
        "docs": "/docs",
        "ocr_integration": "OCR Bridge 사용 (기존 데이터 안전 보존)"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
