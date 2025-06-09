"""
퀴즈 QA 기능 확장 API 라우터
답안 제출, 자동 채점, 점수 저장 시스템

CREATED 2025-01-27: QA 기능 확장 구현
- Phase 1: 답안 제출 API / 자동 채점 로직 / 점수 저장 시스템
- Phase 2: 세션 관리 / 개인 통계 / 퀴즈 기록 조회
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.connection import get_database
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# ==================== 데이터 모델 ====================

class QuizAnswer(BaseModel):
    """개별 답안 모델"""
    question_id: str = Field(..., description="문제 고유 ID")
    question_text: str = Field(..., description="문제 텍스트")
    quiz_type: str = Field(..., description="문제 유형: multiple_choice, true_false, short_answer")
    user_answer: Any = Field(..., description="사용자 답안 (문자열, 숫자, 불린)")
    correct_answer: Any = Field(..., description="정답")
    options: Optional[List[str]] = Field(None, description="객관식 선택지")
    time_spent: Optional[int] = Field(None, description="문제당 소요 시간(초)")

class QuizSubmission(BaseModel):
    """퀴즈 제출 모델"""
    session_id: str = Field(..., description="퀴즈 세션 ID")
    folder_id: Optional[str] = Field(None, description="폴더 ID")
    quiz_topic: Optional[str] = Field(None, description="퀴즈 주제")
    answers: List[QuizAnswer] = Field(..., description="모든 답안 리스트")
    total_time: Optional[int] = Field(None, description="총 소요 시간(초)")
    submitted_at: Optional[datetime] = Field(default_factory=datetime.now)

class QuizResult(BaseModel):
    """채점 결과 모델"""
    question_id: str
    question_text: str
    quiz_type: str
    user_answer: Any
    correct_answer: Any
    is_correct: bool
    score: float = Field(description="문제당 점수")
    explanation: Optional[str] = None

class QuizSessionResult(BaseModel):
    """퀴즈 세션 결과 모델"""
    session_id: str
    total_questions: int
    correct_answers: int
    wrong_answers: int
    total_score: float
    percentage: float
    total_time: Optional[int]
    folder_id: Optional[str]
    quiz_topic: Optional[str]
    results: List[QuizResult]
    submitted_at: datetime
    grade: str = Field(description="등급: A, B, C, D, F")

class QuizStats(BaseModel):
    """개인 퀴즈 통계 모델"""
    total_quizzes: int
    total_questions: int
    average_score: float
    highest_score: float
    lowest_score: float
    total_time_spent: int
    favorite_topics: List[str]
    weak_areas: List[str]
    recent_performance: List[float]  # 최근 10회 점수

class QuizRecord(BaseModel):
    """퀴즈 기록 조회 모델"""
    session_id: str
    folder_id: Optional[str]
    quiz_topic: Optional[str]
    total_questions: int
    score: float
    percentage: float
    grade: str
    time_spent: Optional[int]
    submitted_at: datetime

# ==================== Phase 3: 상세 분석 모델 ====================

class LearningAnalysis(BaseModel):
    """학습 패턴 분석 모델"""
    total_study_time: int = Field(description="총 학습 시간(분)")
    average_session_time: float = Field(description="평균 세션 시간(분)")
    study_frequency: float = Field(description="주간 학습 빈도")
    consistency_score: float = Field(description="학습 일관성 점수 (0-1)")
    improvement_trend: str = Field(description="향상 추세: improving, stable, declining")
    peak_performance_time: Optional[str] = Field(None, description="최고 성과 시간대")

class TopicAnalysis(BaseModel):
    """주제별 분석 모델"""
    topic: str
    total_attempts: int
    average_score: float
    improvement_rate: float = Field(description="향상률")
    difficulty_level: str = Field(description="체감 난이도: easy, medium, hard")
    recommended_focus: bool = Field(description="집중 학습 추천 여부")
    
class PerformanceTrend(BaseModel):
    """성과 트렌드 모델"""
    date: datetime
    score: float
    topic: str
    time_spent: int

class PersonalizedRecommendation(BaseModel):
    """개인화된 추천 모델"""
    content_type: str = Field(description="book, video, youtube, article")
    title: str
    description: str
    relevance_score: float = Field(description="관련성 점수")
    difficulty_match: str = Field(description="난이도 적합성")
    source: str
    url: Optional[str] = None
    estimated_time: Optional[str] = None

class DetailedAnalysis(BaseModel):
    """통합 상세 분석 모델"""
    learning_analysis: LearningAnalysis
    topic_analysis: List[TopicAnalysis]
    performance_trends: List[PerformanceTrend]
    personalized_recommendations: List[PersonalizedRecommendation]
    weak_area_focus: List[str] = Field(description="집중 개선 영역")
    next_study_goals: List[str] = Field(description="다음 학습 목표")

class WeeklyReport(BaseModel):
    """주간 학습 리포트"""
    week_start: datetime
    week_end: datetime
    total_quizzes: int
    total_time_spent: int
    average_score: float
    best_topic: str
    challenging_topic: str
    achievement_summary: str
    improvement_suggestions: List[str]

# ==================== 유틸리티 함수 ====================

class QuizGrader:
    """퀴즈 자동 채점 클래스"""
    
    @staticmethod
    def calculate_grade(percentage: float) -> str:
        """점수에 따른 등급 계산"""
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"
    
    @staticmethod
    def grade_single_answer(answer: QuizAnswer) -> QuizResult:
        """개별 답안 채점"""
        try:
            is_correct = False
            score = 0.0
            
            if answer.quiz_type == "multiple_choice":
                # 객관식: 선택지 인덱스 비교
                is_correct = int(answer.user_answer) == int(answer.correct_answer)
                
            elif answer.quiz_type == "true_false":
                # OX 문제: 불린 값 비교
                user_bool = str(answer.user_answer).lower() in ['true', 'o', '참', '1']
                correct_bool = str(answer.correct_answer).lower() in ['true', 'o', '참', '1']
                is_correct = user_bool == correct_bool
                
            elif answer.quiz_type == "short_answer":
                # 단답형: 문자열 유사도 비교 (간단 버전)
                user_text = str(answer.user_answer).strip().lower()
                correct_text = str(answer.correct_answer).strip().lower()
                
                # 완전 일치 또는 키워드 포함 여부
                is_correct = (user_text == correct_text or 
                            correct_text in user_text or 
                            user_text in correct_text)
            
            score = 1.0 if is_correct else 0.0
            
            return QuizResult(
                question_id=answer.question_id,
                question_text=answer.question_text,
                quiz_type=answer.quiz_type,
                user_answer=answer.user_answer,
                correct_answer=answer.correct_answer,
                is_correct=is_correct,
                score=score
            )
            
        except Exception as e:
            logger.error(f"답안 채점 실패: {e}")
            return QuizResult(
                question_id=answer.question_id,
                question_text=answer.question_text,
                quiz_type=answer.quiz_type,
                user_answer=answer.user_answer,
                correct_answer=answer.correct_answer,
                is_correct=False,
                score=0.0
            )

# ==================== API 엔드포인트 ====================

@router.post("/submit", response_model=QuizSessionResult)
async def submit_quiz(submission: QuizSubmission):
    """
    퀴즈 제출 및 자동 채점 API
    Phase 1 핵심 기능: 답안 제출 + 자동 채점 + 점수 저장
    """
    try:
        db = await get_database()
        
        # 1. 자동 채점 수행
        results = []
        correct_count = 0
        total_score = 0.0
        
        for answer in submission.answers:
            result = QuizGrader.grade_single_answer(answer)
            results.append(result)
            
            if result.is_correct:
                correct_count += 1
            total_score += result.score
        
        # 2. 점수 계산
        total_questions = len(submission.answers)
        percentage = (total_score / total_questions * 100) if total_questions > 0 else 0
        grade = QuizGrader.calculate_grade(percentage)
        
        # 3. 세션 결과 생성
        session_result = QuizSessionResult(
            session_id=submission.session_id,
            total_questions=total_questions,
            correct_answers=correct_count,
            wrong_answers=total_questions - correct_count,
            total_score=total_score,
            percentage=percentage,
            total_time=submission.total_time,
            folder_id=submission.folder_id,
            quiz_topic=submission.quiz_topic,
            results=results,
            submitted_at=submission.submitted_at,
            grade=grade
        )
        
        # 4. 데이터베이스에 저장
        try:
            await save_quiz_session(db, session_result, submission.answers)
        except Exception as e:
            # TestClient 호환성을 위한 동기 저장 시도
            logger.warning(f"비동기 저장 실패, 동기 저장 시도: {e}")
            await save_quiz_session_sync(db, session_result, submission.answers)
        
        logger.info(f"퀴즈 제출 완료: {submission.session_id}, 점수: {percentage:.1f}%")
        
        return session_result
        
    except Exception as e:
        logger.error(f"퀴즈 제출 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"퀴즈 제출 처리 중 오류가 발생했습니다: {str(e)}")

@router.get("/sessions/{session_id}", response_model=QuizSessionResult)
async def get_quiz_session(session_id: str):
    """특정 퀴즈 세션 결과 조회"""
    try:
        db = await get_database()
        
        # quiz_sessions 컬렉션에서 세션 조회
        session_doc = await db.quiz_sessions.find_one({"session_id": session_id})
        
        if not session_doc:
            raise HTTPException(status_code=404, detail="퀴즈 세션을 찾을 수 없습니다")
        
        # quiz_submissions 컬렉션에서 상세 답안 조회
        submissions = await db.quiz_submissions.find({"session_id": session_id}).to_list(None)
        
        # 결과 구성
        results = []
        for sub in submissions:
            results.append(QuizResult(
                question_id=sub["question_id"],
                question_text=sub["question_text"],
                quiz_type=sub["quiz_type"],
                user_answer=sub["user_answer"],
                correct_answer=sub["correct_answer"],
                is_correct=sub["is_correct"],
                score=sub["score"]
            ))
        
        return QuizSessionResult(
            session_id=session_doc["session_id"],
            total_questions=session_doc["total_questions"],
            correct_answers=session_doc["correct_answers"],
            wrong_answers=session_doc["wrong_answers"],
            total_score=session_doc["total_score"],
            percentage=session_doc["percentage"],
            total_time=session_doc.get("total_time"),
            folder_id=session_doc.get("folder_id"),
            quiz_topic=session_doc.get("quiz_topic"),
            results=results,
            submitted_at=session_doc["submitted_at"],
            grade=session_doc["grade"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"퀴즈 세션 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/records", response_model=List[QuizRecord])
async def get_quiz_records(
    folder_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """퀴즈 기록 조회 API (Phase 2)"""
    try:
        db = await get_database()
        
        # 필터 조건 구성
        filter_query = {}
        if folder_id:
            filter_query["folder_id"] = folder_id
        
        # 퀴즈 세션 조회 (최신순)
        sessions_cursor = db.quiz_sessions.find(filter_query).sort("submitted_at", -1).skip(offset).limit(limit)
        sessions = await sessions_cursor.to_list(None)
        
        records = []
        for session in sessions:
            records.append(QuizRecord(
                session_id=session["session_id"],
                folder_id=session.get("folder_id"),
                quiz_topic=session.get("quiz_topic"),
                total_questions=session["total_questions"],
                score=session["total_score"],
                percentage=session["percentage"],
                grade=session["grade"],
                time_spent=session.get("total_time"),
                submitted_at=session["submitted_at"]
            ))
        
        return records
        
    except Exception as e:
        logger.error(f"퀴즈 기록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=QuizStats)
async def get_quiz_stats(folder_id: Optional[str] = None):
    """개인 퀴즈 통계 API (Phase 2)"""
    try:
        db = await get_database()
        
        # 필터 조건 구성
        filter_query = {}
        if folder_id:
            filter_query["folder_id"] = folder_id
        
        # 통계 계산
        sessions = await db.quiz_sessions.find(filter_query).to_list(None)
        
        if not sessions:
            return QuizStats(
                total_quizzes=0,
                total_questions=0,
                average_score=0.0,
                highest_score=0.0,
                lowest_score=0.0,
                total_time_spent=0,
                favorite_topics=[],
                weak_areas=[],
                recent_performance=[]
            )
        
        # 기본 통계 계산
        total_quizzes = len(sessions)
        total_questions = sum(s["total_questions"] for s in sessions)
        scores = [s["percentage"] for s in sessions]
        average_score = sum(scores) / len(scores)
        highest_score = max(scores)
        lowest_score = min(scores)
        total_time_spent = sum(s.get("total_time", 0) for s in sessions)
        
        # 주제별 분석
        topic_scores = {}
        for session in sessions:
            topic = session.get("quiz_topic", "기타")
            if topic not in topic_scores:
                topic_scores[topic] = []
            topic_scores[topic].append(session["percentage"])
        
        # 선호 주제 (점수 높은 순)
        favorite_topics = sorted(topic_scores.keys(), 
                               key=lambda t: sum(topic_scores[t])/len(topic_scores[t]), 
                               reverse=True)[:3]
        
        # 약점 영역 (점수 낮은 순)
        weak_areas = sorted(topic_scores.keys(), 
                          key=lambda t: sum(topic_scores[t])/len(topic_scores[t]))[:3]
        
        # 최근 성과 (최근 10회)
        recent_performance = scores[-10:] if len(scores) >= 10 else scores
        
        return QuizStats(
            total_quizzes=total_quizzes,
            total_questions=total_questions,
            average_score=round(average_score, 1),
            highest_score=round(highest_score, 1),
            lowest_score=round(lowest_score, 1),
            total_time_spent=total_time_spent,
            favorite_topics=favorite_topics,
            weak_areas=weak_areas,
            recent_performance=[round(p, 1) for p in recent_performance]
        )
        
    except Exception as e:
        logger.error(f"퀴즈 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
async def delete_quiz_session(session_id: str):
    """퀴즈 세션 삭제 API"""
    try:
        db = await get_database()
        
        # 세션 존재 확인
        session_doc = await db.quiz_sessions.find_one({"session_id": session_id})
        if not session_doc:
            raise HTTPException(status_code=404, detail="퀴즈 세션을 찾을 수 없습니다")
        
        # 관련 데이터 삭제
        await db.quiz_sessions.delete_one({"session_id": session_id})
        await db.quiz_submissions.delete_many({"session_id": session_id})
        
        return {"success": True, "message": "퀴즈 세션이 삭제되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"퀴즈 세션 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 데이터베이스 저장 함수 ====================

async def save_quiz_session(
    db: AsyncIOMotorDatabase, 
    session_result: QuizSessionResult, 
    original_answers: List[QuizAnswer]
):
    """퀴즈 세션 결과를 데이터베이스에 저장"""
    try:
        # 이벤트 루프 확인 및 처리
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 이벤트 루프가 없으면 새로 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        # 1. quiz_sessions 컬렉션에 세션 정보 저장
        session_doc = {
            "session_id": session_result.session_id,
            "folder_id": session_result.folder_id,
            "quiz_topic": session_result.quiz_topic,
            "total_questions": session_result.total_questions,
            "correct_answers": session_result.correct_answers,
            "wrong_answers": session_result.wrong_answers,
            "total_score": session_result.total_score,
            "percentage": session_result.percentage,
            "grade": session_result.grade,
            "total_time": session_result.total_time,
            "submitted_at": session_result.submitted_at,
            "created_at": datetime.now()
        }
        
        await db.quiz_sessions.insert_one(session_doc)
        
        # 2. quiz_submissions 컬렉션에 개별 답안 저장
        submission_docs = []
        for i, (result, original) in enumerate(zip(session_result.results, original_answers)):
            submission_doc = {
                "session_id": session_result.session_id,
                "question_id": result.question_id,
                "question_text": result.question_text,
                "quiz_type": result.quiz_type,
                "user_answer": result.user_answer,
                "correct_answer": result.correct_answer,
                "is_correct": result.is_correct,
                "score": result.score,
                "options": original.options,
                "time_spent": original.time_spent,
                "question_order": i + 1,
                "created_at": datetime.now()
            }
            submission_docs.append(submission_doc)
        
        if submission_docs:
            await db.quiz_submissions.insert_many(submission_docs)
        
        logger.info(f"퀴즈 세션 저장 완료: {session_result.session_id}")
        
    except Exception as e:
        logger.error(f"퀴즈 세션 저장 실패: {e}")
        raise

async def save_quiz_session_sync(
    db: AsyncIOMotorDatabase, 
    session_result: QuizSessionResult, 
    original_answers: List[QuizAnswer]
):
    """TestClient 호환을 위한 동기식 퀴즈 세션 저장"""
    try:
        import pymongo
        import asyncio
        
        # 동기 클라이언트 생성
        from config.settings import settings
        sync_client = pymongo.MongoClient(settings.MONGODB_URI)
        sync_db = sync_client[settings.MONGODB_DB_NAME]
        
        # 1. quiz_sessions 컬렉션에 세션 정보 저장
        session_doc = {
            "session_id": session_result.session_id,
            "folder_id": session_result.folder_id,
            "quiz_topic": session_result.quiz_topic,
            "total_questions": session_result.total_questions,
            "correct_answers": session_result.correct_answers,
            "wrong_answers": session_result.wrong_answers,
            "total_score": session_result.total_score,
            "percentage": session_result.percentage,
            "grade": session_result.grade,
            "total_time": session_result.total_time,
            "submitted_at": session_result.submitted_at,
            "created_at": datetime.now()
        }
        
        sync_db.quiz_sessions.insert_one(session_doc)
        
        # 2. quiz_submissions 컬렉션에 개별 답안 저장
        submission_docs = []
        for i, (result, original) in enumerate(zip(session_result.results, original_answers)):
            submission_doc = {
                "session_id": session_result.session_id,
                "question_id": result.question_id,
                "question_text": result.question_text,
                "quiz_type": result.quiz_type,
                "user_answer": result.user_answer,
                "correct_answer": result.correct_answer,
                "is_correct": result.is_correct,
                "score": result.score,
                "options": original.options,
                "time_spent": original.time_spent,
                "question_order": i + 1,
                "created_at": datetime.now()
            }
            submission_docs.append(submission_doc)
        
        if submission_docs:
            sync_db.quiz_submissions.insert_many(submission_docs)
        
        sync_client.close()
        logger.info(f"퀴즈 세션 동기 저장 완료: {session_result.session_id}")
        
    except Exception as e:
        logger.error(f"퀴즈 세션 동기 저장 실패: {e}")
        raise 

# ==================== Phase 3: 상세 분석 API ====================

@router.get("/analysis/detailed", response_model=DetailedAnalysis)
async def get_detailed_analysis(
    folder_id: Optional[str] = None,
    days_back: int = Query(30, description="분석 기간 (일)")
):
    """종합 상세 분석 API - 학습 패턴, 성과 트렌드, 개인화 추천"""
    try:
        db = await get_database()
        
        # 분석 기간 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # 기본 필터
        filter_query = {
            "submitted_at": {"$gte": start_date, "$lte": end_date}
        }
        if folder_id:
            filter_query["folder_id"] = folder_id
        
        # 세션 데이터 조회
        sessions = await db.quiz_sessions.find(filter_query).sort("submitted_at", 1).to_list(None)
        
        if not sessions:
            raise HTTPException(status_code=404, detail="분석할 퀴즈 데이터가 없습니다")
        
        # 1. 학습 패턴 분석
        learning_analysis = await _analyze_learning_patterns(sessions)
        
        # 2. 주제별 분석
        topic_analysis = await _analyze_topics(sessions)
        
        # 3. 성과 트렌드 분석
        performance_trends = await _analyze_performance_trends(sessions)
        
        # 4. 개인화된 추천 생성
        personalized_recommendations = await _generate_personalized_recommendations(
            db, topic_analysis, learning_analysis
        )
        
        # 5. 약점 영역 및 학습 목표 설정
        weak_area_focus = [ta.topic for ta in topic_analysis if ta.recommended_focus][:3]
        next_study_goals = await _generate_study_goals(topic_analysis, learning_analysis)
        
        return DetailedAnalysis(
            learning_analysis=learning_analysis,
            topic_analysis=topic_analysis,
            performance_trends=performance_trends,
            personalized_recommendations=personalized_recommendations,
            weak_area_focus=weak_area_focus,
            next_study_goals=next_study_goals
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상세 분석 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/weekly", response_model=WeeklyReport)
async def get_weekly_report(
    folder_id: Optional[str] = None,
    week_offset: int = Query(0, description="주차 오프셋 (0=이번주, 1=지난주)")
):
    """주간 학습 리포트 API"""
    try:
        db = await get_database()
        
        # 주간 범위 설정
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday() + (week_offset * 7))
        end_of_week = start_of_week + timedelta(days=6)
        
        filter_query = {
            "submitted_at": {"$gte": start_of_week, "$lte": end_of_week}
        }
        if folder_id:
            filter_query["folder_id"] = folder_id
        
        sessions = await db.quiz_sessions.find(filter_query).to_list(None)
        
        if not sessions:
            return WeeklyReport(
                week_start=start_of_week,
                week_end=end_of_week,
                total_quizzes=0,
                total_time_spent=0,
                average_score=0.0,
                best_topic="없음",
                challenging_topic="없음",
                achievement_summary="이번 주 퀴즈 활동이 없습니다.",
                improvement_suggestions=["새로운 퀴즈에 도전해보세요!"]
            )
        
        # 주간 통계 계산
        total_quizzes = len(sessions)
        total_time_spent = sum(s.get("total_time", 0) for s in sessions)
        scores = [s["percentage"] for s in sessions]
        average_score = sum(scores) / len(scores)
        
        # 주제별 성과 분석
        topic_scores = {}
        for session in sessions:
            topic = session.get("quiz_topic", "기타")
            if topic not in topic_scores:
                topic_scores[topic] = []
            topic_scores[topic].append(session["percentage"])
        
        # 최고/최악 주제
        best_topic = max(topic_scores.keys(), 
                        key=lambda t: sum(topic_scores[t])/len(topic_scores[t])) if topic_scores else "없음"
        challenging_topic = min(topic_scores.keys(), 
                              key=lambda t: sum(topic_scores[t])/len(topic_scores[t])) if topic_scores else "없음"
        
        # 성취 요약 생성
        achievement_summary = await _generate_achievement_summary(sessions, average_score, total_quizzes)
        
        # 개선 제안 생성
        improvement_suggestions = await _generate_improvement_suggestions(topic_scores, average_score)
        
        return WeeklyReport(
            week_start=start_of_week,
            week_end=end_of_week,
            total_quizzes=total_quizzes,
            total_time_spent=total_time_spent // 60,  # 분 단위로 변환
            average_score=round(average_score, 1),
            best_topic=best_topic,
            challenging_topic=challenging_topic,
            achievement_summary=achievement_summary,
            improvement_suggestions=improvement_suggestions
        )
        
    except Exception as e:
        logger.error(f"주간 리포트 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/recommendations", response_model=List[PersonalizedRecommendation])
async def get_personalized_recommendations(
    folder_id: Optional[str] = None,
    focus_area: Optional[str] = None,
    limit: int = Query(10, description="추천 개수")
):
    """개인화된 학습 자료 추천 API"""
    try:
        db = await get_database()
        
        # 최근 30일 퀴즈 성과 분석
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        filter_query = {
            "submitted_at": {"$gte": start_date, "$lte": end_date}
        }
        if folder_id:
            filter_query["folder_id"] = folder_id
        
        sessions = await db.quiz_sessions.find(filter_query).to_list(None)
        
        if not sessions:
            # 기본 추천 제공
            return await _get_default_recommendations(db, limit)
        
        # 주제별 성과 분석
        topic_analysis = await _analyze_topics(sessions)
        learning_analysis = await _analyze_learning_patterns(sessions)
        
        # 포커스 영역이 지정된 경우 필터링
        if focus_area:
            topic_analysis = [ta for ta in topic_analysis if ta.topic == focus_area]
        
        # 개인화된 추천 생성
        recommendations = await _generate_personalized_recommendations(
            db, topic_analysis, learning_analysis, limit
        )
        
        return recommendations[:limit]
        
    except Exception as e:
        logger.error(f"개인화 추천 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Phase 3: 분석 헬퍼 함수 ====================

async def _analyze_learning_patterns(sessions: List[Dict]) -> LearningAnalysis:
    """학습 패턴 분석"""
    if not sessions:
        return LearningAnalysis(
            total_study_time=0,
            average_session_time=0.0,
            study_frequency=0.0,
            consistency_score=0.0,
            improvement_trend="stable",
            peak_performance_time=None
        )
    
    # 총 학습 시간 계산 (분)
    total_time = sum(s.get("total_time", 0) for s in sessions) // 60
    
    # 평균 세션 시간
    avg_session_time = total_time / len(sessions) if sessions else 0
    
    # 학습 빈도 (주간 평균)
    date_range = (sessions[-1]["submitted_at"] - sessions[0]["submitted_at"]).days + 1
    study_frequency = len(sessions) / max(date_range / 7, 1)
    
    # 일관성 점수 (날짜별 분포의 균등함)
    study_days = set(s["submitted_at"].date() for s in sessions)
    consistency_score = min(len(study_days) / date_range, 1.0) if date_range > 0 else 0
    
    # 향상 추세 분석
    scores = [s["percentage"] for s in sessions]
    if len(scores) >= 3:
        recent_avg = sum(scores[-3:]) / 3
        early_avg = sum(scores[:3]) / 3
        if recent_avg > early_avg + 5:
            improvement_trend = "improving"
        elif recent_avg < early_avg - 5:
            improvement_trend = "declining"
        else:
            improvement_trend = "stable"
    else:
        improvement_trend = "stable"
    
    # 최고 성과 시간대 분석
    hour_scores = {}
    for session in sessions:
        hour = session["submitted_at"].hour
        if hour not in hour_scores:
            hour_scores[hour] = []
        hour_scores[hour].append(session["percentage"])
    
    if hour_scores:
        best_hour = max(hour_scores.keys(), 
                       key=lambda h: sum(hour_scores[h])/len(hour_scores[h]))
        peak_performance_time = f"{best_hour:02d}:00-{best_hour+1:02d}:00"
    else:
        peak_performance_time = None
    
    return LearningAnalysis(
        total_study_time=total_time,
        average_session_time=round(avg_session_time, 1),
        study_frequency=round(study_frequency, 1),
        consistency_score=round(consistency_score, 2),
        improvement_trend=improvement_trend,
        peak_performance_time=peak_performance_time
    )

async def _analyze_topics(sessions: List[Dict]) -> List[TopicAnalysis]:
    """주제별 분석"""
    topic_data = {}
    
    for session in sessions:
        topic = session.get("quiz_topic", "기타")
        if topic not in topic_data:
            topic_data[topic] = {
                "scores": [],
                "attempts": 0,
                "timestamps": []
            }
        
        topic_data[topic]["scores"].append(session["percentage"])
        topic_data[topic]["attempts"] += 1
        topic_data[topic]["timestamps"].append(session["submitted_at"])
    
    topic_analyses = []
    for topic, data in topic_data.items():
        scores = data["scores"]
        avg_score = sum(scores) / len(scores)
        
        # 향상률 계산
        if len(scores) >= 2:
            recent_score = scores[-1]
            early_score = scores[0]
            improvement_rate = ((recent_score - early_score) / early_score) * 100 if early_score > 0 else 0
        else:
            improvement_rate = 0
        
        # 체감 난이도 결정
        if avg_score >= 80:
            difficulty_level = "easy"
        elif avg_score >= 60:
            difficulty_level = "medium"
        else:
            difficulty_level = "hard"
        
        # 집중 학습 추천 여부
        recommended_focus = avg_score < 70 or improvement_rate < -10
        
        topic_analyses.append(TopicAnalysis(
            topic=topic,
            total_attempts=data["attempts"],
            average_score=round(avg_score, 1),
            improvement_rate=round(improvement_rate, 1),
            difficulty_level=difficulty_level,
            recommended_focus=recommended_focus
        ))
    
    return sorted(topic_analyses, key=lambda x: x.average_score)

async def _analyze_performance_trends(sessions: List[Dict]) -> List[PerformanceTrend]:
    """성과 트렌드 분석"""
    trends = []
    for session in sessions:
        trends.append(PerformanceTrend(
            date=session["submitted_at"],
            score=session["percentage"],
            topic=session.get("quiz_topic", "기타"),
            time_spent=session.get("total_time", 0) // 60  # 분 단위
        ))
    
    return sorted(trends, key=lambda x: x.date)

async def _generate_personalized_recommendations(
    db, topic_analysis: List[TopicAnalysis], 
    learning_analysis: LearningAnalysis, 
    limit: int = 10
) -> List[PersonalizedRecommendation]:
    """개인화된 추천 생성 (기존 추천 시스템 연동)"""
    recommendations = []
    
    # 약점 주제에 대한 추천
    weak_topics = [ta for ta in topic_analysis if ta.recommended_focus][:3]
    
    for topic_info in weak_topics:
        topic = topic_info.topic
        difficulty = topic_info.difficulty_level
        
        try:
            # 기존 추천 시스템에서 관련 콘텐츠 조회
            existing_recommendations = await db.recommendations.find({
                "keyword": {"$regex": topic, "$options": "i"}
            }).limit(3).to_list(None)
            
            for rec in existing_recommendations:
                recommendations.append(PersonalizedRecommendation(
                    content_type=rec.get("content_type", "article"),
                    title=rec.get("title", "추천 자료"),
                    description=rec.get("description", f"{topic} 관련 학습 자료"),
                    relevance_score=0.9,  # 높은 관련성
                    difficulty_match=difficulty,
                    source=rec.get("source", "database"),
                    url=rec.get("source"),
                    estimated_time=_estimate_study_time(rec.get("content_type", "article"))
                ))
        except Exception as e:
            logger.warning(f"기존 추천 시스템 연동 실패: {e}")
    
    # 학습 패턴 기반 추천
    if learning_analysis.improvement_trend == "declining":
        recommendations.extend(await _get_motivation_content(limit=2))
    elif learning_analysis.consistency_score < 0.3:
        recommendations.extend(await _get_habit_building_content(limit=2))
    
    # 부족한 경우 기본 추천으로 채우기
    if len(recommendations) < limit:
        default_recs = await _get_default_recommendations(db, limit - len(recommendations))
        recommendations.extend(default_recs)
    
    return recommendations[:limit]

async def _generate_study_goals(
    topic_analysis: List[TopicAnalysis], 
    learning_analysis: LearningAnalysis
) -> List[str]:
    """다음 학습 목표 생성"""
    goals = []
    
    # 약점 주제 기반 목표
    weak_topics = [ta.topic for ta in topic_analysis if ta.recommended_focus]
    if weak_topics:
        goals.append(f"{weak_topics[0]} 영역에서 70점 이상 달성하기")
    
    # 학습 패턴 기반 목표
    if learning_analysis.consistency_score < 0.5:
        goals.append("주 3회 이상 꾸준한 학습 습관 만들기")
    
    if learning_analysis.improvement_trend == "declining":
        goals.append("최근 성과 하락 원인 분석 및 개선하기")
    
    # 전체적인 목표
    avg_score = sum(ta.average_score for ta in topic_analysis) / len(topic_analysis) if topic_analysis else 0
    if avg_score < 80:
        goals.append("전체 평균 점수 80점 이상 달성하기")
    
    return goals[:3]  # 최대 3개까지

async def _generate_achievement_summary(sessions: List[Dict], avg_score: float, total_quizzes: int) -> str:
    """성취 요약 생성"""
    if avg_score >= 90:
        performance_desc = "뛰어난 성과"
    elif avg_score >= 80:
        performance_desc = "우수한 성과"
    elif avg_score >= 70:
        performance_desc = "양호한 성과"
    else:
        performance_desc = "개선이 필요한 성과"
    
    return f"이번 주 {total_quizzes}개의 퀴즈를 완료하며 평균 {avg_score:.1f}점으로 {performance_desc}를 보였습니다."

async def _generate_improvement_suggestions(topic_scores: Dict, avg_score: float) -> List[str]:
    """개선 제안 생성"""
    suggestions = []
    
    if avg_score < 70:
        suggestions.append("기초 개념 복습을 통해 전반적인 이해도를 높여보세요")
    
    # 가장 낮은 점수의 주제에 대한 제안
    if topic_scores:
        worst_topic = min(topic_scores.keys(), 
                         key=lambda t: sum(topic_scores[t])/len(topic_scores[t]))
        worst_avg = sum(topic_scores[worst_topic]) / len(topic_scores[worst_topic])
        if worst_avg < 60:
            suggestions.append(f"{worst_topic} 영역의 집중 학습이 필요합니다")
    
    # 일반적인 제안
    suggestions.append("꾸준한 학습 습관 유지로 장기적인 성과 향상을 도모하세요")
    
    return suggestions[:3]

async def _get_default_recommendations(db, limit: int) -> List[PersonalizedRecommendation]:
    """기본 추천 콘텐츠"""
    default_recs = [
        PersonalizedRecommendation(
            content_type="article",
            title="효과적인 학습 방법론",
            description="과학적으로 검증된 학습 전략과 기법들",
            relevance_score=0.7,
            difficulty_match="medium",
            source="educational_database",
            estimated_time="15분"
        ),
        PersonalizedRecommendation(
            content_type="video",
            title="집중력 향상 기법",
            description="학습 효율을 높이는 집중력 향상 방법",
            relevance_score=0.6,
            difficulty_match="easy",
            source="learning_platform",
            estimated_time="20분"
        )
    ]
    
    return default_recs[:limit]

async def _get_motivation_content(limit: int) -> List[PersonalizedRecommendation]:
    """동기부여 콘텐츠"""
    return [
        PersonalizedRecommendation(
            content_type="article",
            title="학습 동기 회복하기",
            description="학습 슬럼프를 극복하는 효과적인 방법들",
            relevance_score=0.8,
            difficulty_match="easy",
            source="motivation_library",
            estimated_time="10분"
        )
    ][:limit]

async def _get_habit_building_content(limit: int) -> List[PersonalizedRecommendation]:
    """습관 형성 콘텐츠"""
    return [
        PersonalizedRecommendation(
            content_type="guide",
            title="21일 학습 습관 만들기",
            description="꾸준한 학습 습관을 만드는 단계별 가이드",
            relevance_score=0.8,
            difficulty_match="medium",
            source="habit_coach",
            estimated_time="25분"
        )
    ][:limit]

def _estimate_study_time(content_type: str) -> str:
    """콘텐츠 타입별 예상 학습 시간"""
    time_map = {
        "book": "2-3시간",
        "article": "10-15분",
        "video": "20-30분",
        "youtube": "10-20분",
        "guide": "30-45분"
    }
    return time_map.get(content_type, "15-20분") 