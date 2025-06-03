"""
퀴즈 API 라우터
MODIFIED 2024-12-20: 퀴즈 히스토리 및 통계 조회 기능 추가
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from api.chains.quiz_chain import QuizChain
from database.connection import get_database
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

class QuizRequest(BaseModel):
    """퀴즈 요청 모델"""
    topic: Optional[str] = None
    folder_id: Optional[str] = None
    difficulty: str = "medium"
    count: int = 5
    quiz_type: str = "multiple_choice"

class QuizItem(BaseModel):
    """퀴즈 항목 모델"""
    question: str
    quiz_type: Optional[str] = "multiple_choice"  # multiple_choice, true_false, short_answer, fill_in_blank
    options: Optional[List[str]] = None  # 객관식/참거짓용
    correct_option: Optional[int] = None  # 객관식/참거짓용 정답 인덱스
    correct_answer: Optional[str] = None  # 단답형/빈칸채우기용 정답
    difficulty: str
    explanation: Optional[str] = None
    from_existing: Optional[bool] = False

class QuizResponse(BaseModel):
    """퀴즈 응답 모델"""
    quizzes: List[QuizItem]
    topic: Optional[str]
    total_count: int
    generated_new: Optional[int] = 0
    used_existing: Optional[int] = 0

class QuizHistoryItem(BaseModel):
    """퀴즈 히스토리 항목 모델"""
    quiz_id: str
    question: str
    quiz_type: str
    difficulty: str
    topic: Optional[str]
    created_at: str
    folder_id: Optional[str]

class QuizHistoryResponse(BaseModel):
    """퀴즈 히스토리 응답 모델"""
    quiz_history: List[QuizHistoryItem]
    total_count: int

class QuizStatsResponse(BaseModel):
    """퀴즈 통계 응답 모델"""
    total_quizzes: int
    difficulty_distribution: dict
    type_distribution: dict
    folder_id: Optional[str]

@router.post("/", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest):
    """퀴즈 생성 엔드포인트"""
    try:
        db = await get_database()
        quiz_chain = QuizChain(db)
        
        # 퀴즈 생성
        result = await quiz_chain.process(
            topic=request.topic,
            folder_id=request.folder_id,
            difficulty=request.difficulty,
            count=request.count,
            quiz_type=request.quiz_type
        )
        
        # 퀴즈 항목 변환
        quiz_items = []
        for quiz in result["quizzes"]:
            quiz_items.append(QuizItem(
                question=quiz["question"],
                quiz_type=quiz.get("quiz_type", "multiple_choice"),
                options=quiz.get("options"),
                correct_option=quiz.get("correct_option"),
                correct_answer=quiz.get("correct_answer"),
                difficulty=quiz["difficulty"],
                explanation=quiz.get("explanation"),
                from_existing=quiz.get("from_existing", False)
            ))
        
        return QuizResponse(
            quizzes=quiz_items,
            topic=request.topic,
            total_count=len(quiz_items),
            generated_new=result.get("generated_new", 0),
            used_existing=result.get("used_existing", 0)
        )
        
    except Exception as e:
        logger.error(f"퀴즈 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=QuizHistoryResponse)
async def get_quiz_history(folder_id: Optional[str] = None, limit: int = 20):
    """퀴즈 히스토리 조회 엔드포인트"""
    try:
        db = await get_database()
        quiz_chain = QuizChain(db)
        
        quiz_history = await quiz_chain.get_quiz_history(folder_id, limit)
        
        return QuizHistoryResponse(
            quiz_history=[
                QuizHistoryItem(
                    quiz_id=item["quiz_id"],
                    question=item["question"],
                    quiz_type=item["quiz_type"],
                    difficulty=item["difficulty"],
                    topic=item["topic"],
                    created_at=str(item["created_at"]),
                    folder_id=item["folder_id"]
                )
                for item in quiz_history
            ],
            total_count=len(quiz_history)
        )
        
    except Exception as e:
        logger.error(f"퀴즈 히스토리 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=QuizStatsResponse)
async def get_quiz_stats(folder_id: Optional[str] = None):
    """퀴즈 통계 조회 엔드포인트"""
    try:
        db = await get_database()
        quiz_chain = QuizChain(db)
        
        stats = await quiz_chain.get_quiz_stats(folder_id)
        
        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])
        
        return QuizStatsResponse(
            total_quizzes=stats["total_quizzes"],
            difficulty_distribution=stats["difficulty_distribution"],
            type_distribution=stats["type_distribution"],
            folder_id=stats["folder_id"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"퀴즈 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{quiz_id}")
async def delete_quiz(quiz_id: str):
    """퀴즈 삭제 엔드포인트"""
    try:
        db = await get_database()
        quiz_chain = QuizChain(db)
        
        success = await quiz_chain.delete_quiz(quiz_id)
        
        if success:
            return {"success": True, "message": "퀴즈가 삭제되었습니다."}
        else:
            raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다.")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"퀴즈 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
