"""
퀴즈 체인
퀴즈 생성 파이프라인
MODIFIED 2024-12-20: 퀴즈 결과 저장 기능 추가 및 새 DB 구조 적용
"""
from typing import Dict, Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from ai_processing.qa_generator import QAGenerator
from retrieval.hybrid_search import HybridSearch
from database.operations import DatabaseOperations
from utils.logger import get_logger

logger = get_logger(__name__)

class QuizChain:
    """퀴즈 체인 클래스"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.db_ops = DatabaseOperations(db)
        self.qa_generator = QAGenerator()
        self.hybrid_search = HybridSearch(db)
        self.qapairs = db.qapairs
        self.documents = db.documents
        self.chunks = db.chunks
        self.file_info = db.file_info
    
    async def process(
        self,
        topic: Optional[str] = None,
        folder_id: Optional[str] = None,
        difficulty: str = "medium",
        count: int = 5,
        quiz_type: str = "multiple_choice"
    ) -> Dict:
        """퀴즈 처리"""
        try:
            quizzes = []
            source_document_id = None
            
            # 1. 기존 퀴즈 조회
            filter_dict = {"difficulty": difficulty, "quiz_type": quiz_type}
            if folder_id:
                filter_dict["folder_id"] = folder_id
            if topic:
                filter_dict["topic"] = topic
            
            existing_quizzes = await self.qapairs.find(
                filter_dict
            ).limit(count).to_list(None)
            
            # 2. 기존 퀴즈가 충분하면 사용
            if len(existing_quizzes) >= count:
                logger.info(f"기존 퀴즈 {len(existing_quizzes)}개 발견, 재사용")
                for quiz in existing_quizzes[:count]:
                    quizzes.append({
                        "question": quiz["question"],
                        "quiz_type": quiz.get("quiz_type", "multiple_choice"),
                        "options": quiz.get("quiz_options", []),
                        "correct_option": quiz.get("correct_option"),
                        "correct_answer": quiz.get("correct_answer"),
                        "difficulty": quiz["difficulty"],
                        "explanation": quiz.get("answer", ""),
                        "from_existing": True
                    })
                
                # 폴더 접근 시간 업데이트
                if folder_id:
                    await self.db_ops.update_folder_access(folder_id)
                
                return {"quizzes": quizzes}
            
            # 3. 새로운 퀴즈 생성 필요
            texts_for_quiz = []
            
            if topic:
                # 주제 관련 청크 검색
                search_results = await self.hybrid_search.search(
                    query=topic,
                    k=10,  # 더 많은 청크에서 텍스트 수집
                    folder_id=folder_id
                )
                
                # 검색된 청크들의 텍스트 수집
                for result in search_results:
                    chunk_text = result.get("chunk", {}).get("text", "")
                    if chunk_text and len(chunk_text) > 100:  # 충분한 길이의 텍스트만
                        texts_for_quiz.append(chunk_text)
                        
                        # 첫 번째 검색 결과의 문서 ID를 source로 사용
                        if not source_document_id:
                            chunk_info = result.get("chunk", {})
                            source_document_id = chunk_info.get("document_id")
                
            else:
                # topic이 없으면 폴더 또는 전체에서 텍스트 수집
                if folder_id:
                    # 새로운 documents 컬렉션에서 조회
                    folder_docs = await self.db_ops.find_many("documents", {"folder_id": folder_id}, limit=10)
                    
                    for doc in folder_docs:
                        doc_text = doc.get("raw_text", "")
                        if doc_text and len(doc_text) > 100:
                            texts_for_quiz.append(doc_text)
                            
                            # 첫 번째 문서 ID를 source로 사용
                            if not source_document_id:
                                source_document_id = str(doc["_id"])
                else:
                    # 전체에서 샘플링 (chunks 컬렉션 사용)
                    chunks = await self.chunks.find({}).limit(10).to_list(None)
                    
                    for chunk in chunks:
                        chunk_text = chunk.get("text", "")
                        if chunk_text and len(chunk_text) > 100:
                            texts_for_quiz.append(chunk_text)
                            
                            if not source_document_id:
                                source_document_id = chunk.get("document_id")
            
            # 4. 수집된 텍스트로 퀴즈 생성
            logger.info(f"퀴즈 생성용 텍스트 {len(texts_for_quiz)}개 수집")
            
            new_quizzes = []
            for i, text in enumerate(texts_for_quiz):
                if len(quizzes) + len(new_quizzes) >= count:
                    break
                    
                try:
                    quiz = await self.qa_generator.generate_quiz(
                        text=text,
                        quiz_type=quiz_type,
                        difficulty=difficulty
                    )
                    
                    if quiz:
                        quiz["from_existing"] = False
                        new_quizzes.append(quiz)
                        logger.info(f"새 퀴즈 {len(new_quizzes)}/{count} 생성 완료")
                        
                except Exception as e:
                    logger.warning(f"텍스트 {i+1}에서 퀴즈 생성 실패: {e}")
                    continue
            
            # 5. 생성된 퀴즈가 없는 경우 기본 퀴즈 제공
            if not new_quizzes and not quizzes:
                new_quizzes = self._generate_fallback_quizzes(topic or "일반", difficulty, count)
            
            # 6. 새로 생성된 퀴즈를 데이터베이스에 저장
            if new_quizzes:
                try:
                    saved_quiz_ids = await self.db_ops.save_quiz_results(
                        quizzes=new_quizzes,
                        folder_id=folder_id,
                        topic=topic,
                        source_document_id=source_document_id
                    )
                    logger.info(f"새 퀴즈 {len(saved_quiz_ids)}개 저장 완료")
                except Exception as save_error:
                    logger.warning(f"퀴즈 저장 실패: {save_error}")
            
            # 7. 기존 + 새 퀴즈 결합
            all_quizzes = quizzes + new_quizzes
            
            # 8. 폴더 접근 시간 업데이트
            if folder_id:
                await self.db_ops.update_folder_access(folder_id)
            
            return {
                "quizzes": all_quizzes[:count],
                "generated_new": len(new_quizzes),
                "used_existing": len(quizzes),
                "source_document_id": source_document_id
            }
            
        except Exception as e:
            logger.error(f"퀴즈 처리 실패: {e}")
            raise
    
    def _generate_fallback_quizzes(self, topic: str, difficulty: str, count: int) -> List[Dict]:
        """기본 퀴즈 생성 (텍스트가 없을 때)"""
        fallback_quizzes = [
            {
                "question": f"{topic}에 대한 퀴즈를 생성하려고 했지만, 관련 문서가 부족합니다. 문서를 업로드한 후 다시 시도해주세요.",
                "quiz_type": "multiple_choice",
                "options": ["문서 업로드 필요", "관련 자료 부족", "퀴즈 생성 불가", "다시 시도 필요"],
                "correct_option": 0,
                "difficulty": difficulty,
                "explanation": f"{topic}에 대한 퀴즈를 생성하려면 관련 문서가 필요합니다. 먼저 관련 문서를 업로드해주세요.",
                "from_existing": False
            }
        ]
        
        return fallback_quizzes * min(count, 1)  # 최대 1개만 반환
    
    async def get_quiz_history(self, folder_id: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """퀴즈 히스토리 조회"""
        try:
            filter_dict = {}
            if folder_id:
                filter_dict["folder_id"] = folder_id
            
            quiz_history = await self.db_ops.find_many(
                "qapairs", 
                filter_dict, 
                limit=limit
            )
            
            return [
                {
                    "quiz_id": str(quiz["_id"]),
                    "question": quiz["question"],
                    "quiz_type": quiz.get("quiz_type", "multiple_choice"),
                    "difficulty": quiz["difficulty"],
                    "topic": quiz.get("topic"),
                    "created_at": quiz["created_at"],
                    "folder_id": quiz.get("folder_id")
                }
                for quiz in quiz_history
            ]
            
        except Exception as e:
            logger.error(f"퀴즈 히스토리 조회 실패: {e}")
            return []
    
    async def delete_quiz(self, quiz_id: str) -> bool:
        """퀴즈 삭제"""
        try:
            from bson import ObjectId
            return await self.db_ops.delete_one("qapairs", {"_id": ObjectId(quiz_id)})
        except Exception as e:
            logger.error(f"퀴즈 삭제 실패: {e}")
            return False
    
    async def get_quiz_stats(self, folder_id: Optional[str] = None) -> Dict:
        """퀴즈 통계 조회"""
        try:
            filter_dict = {}
            if folder_id:
                filter_dict["folder_id"] = folder_id
            
            # 총 퀴즈 수
            total_count = await self.qapairs.count_documents(filter_dict)
            
            # 난이도별 분포
            difficulty_pipeline = [
                {"$match": filter_dict},
                {"$group": {"_id": "$difficulty", "count": {"$sum": 1}}}
            ]
            difficulty_stats = await self.qapairs.aggregate(difficulty_pipeline).to_list(None)
            
            # 타입별 분포
            type_pipeline = [
                {"$match": filter_dict},
                {"$group": {"_id": "$quiz_type", "count": {"$sum": 1}}}
            ]
            type_stats = await self.qapairs.aggregate(type_pipeline).to_list(None)
            
            return {
                "total_quizzes": total_count,
                "difficulty_distribution": {stat["_id"]: stat["count"] for stat in difficulty_stats},
                "type_distribution": {stat["_id"]: stat["count"] for stat in type_stats},
                "folder_id": folder_id
            }
            
        except Exception as e:
            logger.error(f"퀴즈 통계 조회 실패: {e}")
            return {"error": str(e)}
