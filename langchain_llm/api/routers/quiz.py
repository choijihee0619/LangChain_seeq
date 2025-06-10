"""
퀴즈 API 라우터
MODIFIED 2024-12-20: 퀴즈 히스토리 및 통계 조회 기능 추가
MODIFIED 2024-12-20: 퀴즈 목록 조회 및 상세 조회 API 추가
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
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

class QuizDetailItem(BaseModel):
    """퀴즈 상세 정보 모델 (웹 조회용)"""
    quiz_id: str
    question: str
    quiz_type: str = "multiple_choice"
    quiz_options: Optional[List[str]] = None
    correct_option: Optional[int] = None
    correct_answer: Optional[str] = None
    answer: Optional[str] = None  # 해설
    difficulty: str
    topic: Optional[str] = None
    folder_id: Optional[str] = None
    source_document_id: Optional[str] = None
    created_at: Optional[str] = None

class QuizResponse(BaseModel):
    """퀴즈 응답 모델"""
    quizzes: List[QuizItem]
    topic: Optional[str]
    total_count: int
    generated_new: Optional[int] = 0
    used_existing: Optional[int] = 0

class QuizListResponse(BaseModel):
    """퀴즈 목록 응답 모델"""
    quizzes: List[QuizDetailItem]
    total_count: int
    page: int
    limit: int
    has_next: bool

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

@router.get("/list", response_model=QuizListResponse)
async def get_quiz_list(
    folder_id: Optional[str] = Query(None, description="폴더 ID로 필터링"),
    topic: Optional[str] = Query(None, description="주제로 필터링"),
    difficulty: Optional[str] = Query(None, description="난이도로 필터링 (easy, medium, hard)"),
    quiz_type: Optional[str] = Query(None, description="퀴즈 타입으로 필터링 (multiple_choice, true_false, short_answer)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 항목 수")
):
    """
    퀴즈 목록 조회 엔드포인트 (웹 전용)
    qapairs 컬렉션에서 저장된 퀴즈들을 필터링하여 조회
    """
    try:
        db = await get_database()
        
        # 필터 조건 구성
        filter_dict = {}
        if folder_id:
            filter_dict["folder_id"] = folder_id
        if topic:
            filter_dict["topic"] = {"$regex": topic, "$options": "i"}
        if difficulty:
            filter_dict["difficulty"] = difficulty
        if quiz_type:
            filter_dict["quiz_type"] = quiz_type
        
        # 총 개수 조회
        total_count = await db.qapairs.count_documents(filter_dict)
        
        # 페이징 계산
        skip = (page - 1) * limit
        has_next = skip + limit < total_count
        
        # 퀴즈 목록 조회
        quizzes_cursor = db.qapairs.find(filter_dict).sort("created_at", -1).skip(skip).limit(limit)
        quizzes = await quizzes_cursor.to_list(None)
        
        # 응답 데이터 구성
        quiz_items = []
        for quiz in quizzes:
            quiz_items.append(QuizDetailItem(
                quiz_id=str(quiz["_id"]),
                question=quiz["question"],
                quiz_type=quiz.get("quiz_type", "multiple_choice"),
                quiz_options=quiz.get("quiz_options", []),
                correct_option=quiz.get("correct_option"),
                correct_answer=quiz.get("correct_answer"),
                answer=quiz.get("answer", ""),
                difficulty=quiz["difficulty"],
                topic=quiz.get("topic"),
                folder_id=quiz.get("folder_id"),
                source_document_id=quiz.get("source_document_id"),
                created_at=str(quiz.get("created_at", ""))
            ))
        
        logger.info(f"퀴즈 목록 조회 완료: {len(quiz_items)}개 (총 {total_count}개)")
        
        return QuizListResponse(
            quizzes=quiz_items,
            total_count=total_count,
            page=page,
            limit=limit,
            has_next=has_next
        )
        
    except Exception as e:
        logger.error(f"퀴즈 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{quiz_id}", response_model=QuizDetailItem)
async def get_quiz_detail(quiz_id: str):
    """
    개별 퀴즈 상세 조회 엔드포인트
    특정 퀴즈의 모든 정보 (선택지, 정답, 해설 포함) 조회
    """
    try:
        db = await get_database()
        
        # ObjectId 변환
        try:
            object_id = ObjectId(quiz_id)
        except:
            raise HTTPException(status_code=400, detail="유효하지 않은 퀴즈 ID 형식입니다")
        
        # 퀴즈 조회
        quiz = await db.qapairs.find_one({"_id": object_id})
        
        if not quiz:
            raise HTTPException(status_code=404, detail="퀴즈를 찾을 수 없습니다")
        
        # 응답 데이터 구성
        quiz_detail = QuizDetailItem(
            quiz_id=str(quiz["_id"]),
            question=quiz["question"],
            quiz_type=quiz.get("quiz_type", "multiple_choice"),
            quiz_options=quiz.get("quiz_options", []),
            correct_option=quiz.get("correct_option"),
            correct_answer=quiz.get("correct_answer"),
            answer=quiz.get("answer", ""),
            difficulty=quiz["difficulty"],
            topic=quiz.get("topic"),
            folder_id=quiz.get("folder_id"),
            source_document_id=quiz.get("source_document_id"),
            created_at=str(quiz.get("created_at", ""))
        )
        
        logger.info(f"퀴즈 상세 조회 완료: {quiz_id}")
        return quiz_detail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"퀴즈 상세 조회 실패: {e}")
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
