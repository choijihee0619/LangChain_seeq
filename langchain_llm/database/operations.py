"""
데이터베이스 작업 모듈
공통 CRUD 작업
MODIFIED 2024-12-20: 새로운 컬렉션 구조에 맞는 특화 메서드 추가
"""
from typing import Dict, List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.logger import get_logger
from bson import ObjectId
import hashlib

logger = get_logger(__name__)

class DatabaseOperations:
    """데이터베이스 작업 클래스"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def insert_one(
        self,
        collection_name: str,
        document: Dict
    ) -> str:
        """단일 문서 삽입"""
        try:
            # 타임스탬프 추가
            if "created_at" not in document:
                document["created_at"] = datetime.utcnow()
            
            collection = self.db[collection_name]
            result = await collection.insert_one(document)
            
            logger.info(f"{collection_name}에 문서 삽입: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"문서 삽입 실패: {e}")
            raise
    
    async def insert_many(
        self,
        collection_name: str,
        documents: List[Dict]
    ) -> List[str]:
        """다중 문서 삽입"""
        try:
            # 타임스탬프 추가
            for doc in documents:
                if "created_at" not in doc:
                    doc["created_at"] = datetime.utcnow()
            
            collection = self.db[collection_name]
            result = await collection.insert_many(documents)
            
            logger.info(f"{collection_name}에 {len(result.inserted_ids)}개 문서 삽입")
            return [str(id) for id in result.inserted_ids]
            
        except Exception as e:
            logger.error(f"다중 문서 삽입 실패: {e}")
            raise
    
    async def find_one(
        self,
        collection_name: str,
        filter_dict: Dict
    ) -> Optional[Dict]:
        """단일 문서 조회"""
        try:
            collection = self.db[collection_name]
            document = await collection.find_one(filter_dict)
            return document
            
        except Exception as e:
            logger.error(f"문서 조회 실패: {e}")
            raise
    
    async def find_many(
        self,
        collection_name: str,
        filter_dict: Dict,
        limit: Optional[int] = None,
        skip: Optional[int] = None
    ) -> List[Dict]:
        """다중 문서 조회"""
        try:
            collection = self.db[collection_name]
            cursor = collection.find(filter_dict)
            
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            
            documents = await cursor.to_list(None)
            return documents
            
        except Exception as e:
            logger.error(f"다중 문서 조회 실패: {e}")
            raise
    
    async def update_one(
        self,
        collection_name: str,
        filter_dict: Dict,
        update_dict: Dict
    ) -> bool:
        """단일 문서 업데이트"""
        try:
            # 업데이트 타임스탬프 추가
            update_dict["$set"] = update_dict.get("$set", {})
            update_dict["$set"]["updated_at"] = datetime.utcnow()
            
            collection = self.db[collection_name]
            result = await collection.update_one(filter_dict, update_dict)
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"문서 업데이트 실패: {e}")
            raise
    
    async def delete_one(
        self,
        collection_name: str,
        filter_dict: Dict
    ) -> bool:
        """단일 문서 삭제"""
        try:
            collection = self.db[collection_name]
            result = await collection.delete_one(filter_dict)
            
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"문서 삭제 실패: {e}")
            raise
    
    # === 새로운 특화 메서드들 ===
    
    async def create_folder(self, title: str, folder_type: str = "library", cover_image_url: Optional[str] = None) -> str:
        """폴더 생성"""
        try:
            folder_doc = {
                "title": title,
                "folder_type": folder_type,
                "created_at": datetime.utcnow(),
                "last_accessed_at": datetime.utcnow(),
                "cover_image_url": cover_image_url
            }
            
            folder_id = await self.insert_one("folders", folder_doc)
            logger.info(f"폴더 생성 완료: {title} ({folder_id})")
            return folder_id
            
        except Exception as e:
            logger.error(f"폴더 생성 실패: {e}")
            raise
    
    async def update_folder_access(self, folder_id: str) -> bool:
        """폴더 마지막 접근 시간 업데이트"""
        try:
            # ObjectId 유효성 검증
            if not folder_id or folder_id == "string" or len(folder_id) != 24:
                logger.warning(f"유효하지 않은 folder_id: {folder_id}")
                return False
            
            # ObjectId 변환 가능한지 확인
            try:
                obj_id = ObjectId(folder_id)
            except Exception:
                logger.warning(f"ObjectId 변환 실패: {folder_id}")
                return False
            
            return await self.update_one(
                "folders",
                {"_id": obj_id},
                {"$set": {"last_accessed_at": datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"폴더 접근 시간 업데이트 실패: {e}")
            return False
    
    async def save_summary_cache(
        self,
        summary: str,
        folder_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        summary_type: str = "brief"
    ) -> str:
        """요약 결과 캐싱"""
        try:
            # 캐시 키 생성
            cache_data = f"{folder_id}_{document_ids}_{summary_type}"
            cache_key = hashlib.md5(cache_data.encode()).hexdigest()
            
            summary_doc = {
                "cache_key": cache_key,
                "summary": summary,
                "folder_id": folder_id,
                "document_ids": document_ids or [],
                "summary_type": summary_type,
                "created_at": datetime.utcnow(),
                "last_accessed_at": datetime.utcnow()
            }
            
            # 기존 캐시가 있으면 업데이트, 없으면 생성
            existing = await self.find_one("summaries", {"cache_key": cache_key})
            if existing:
                await self.update_one(
                    "summaries",
                    {"cache_key": cache_key},
                    {"$set": {"last_accessed_at": datetime.utcnow()}}
                )
                return str(existing["_id"])
            else:
                return await self.insert_one("summaries", summary_doc)
                
        except Exception as e:
            logger.error(f"요약 캐시 저장 실패: {e}")
            raise
    
    async def get_summary_cache(
        self,
        folder_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        summary_type: str = "brief"
    ) -> Optional[Dict]:
        """요약 캐시 조회"""
        try:
            cache_data = f"{folder_id}_{document_ids}_{summary_type}"
            cache_key = hashlib.md5(cache_data.encode()).hexdigest()
            
            return await self.find_one("summaries", {"cache_key": cache_key})
            
        except Exception as e:
            logger.error(f"요약 캐시 조회 실패: {e}")
            return None
    
    async def save_quiz_results(
        self,
        quizzes: List[Dict],
        folder_id: Optional[str] = None,
        topic: Optional[str] = None,
        source_document_id: Optional[str] = None
    ) -> List[str]:
        """퀴즈 결과 저장"""
        try:
            quiz_docs = []
            for quiz in quizzes:
                quiz_doc = {
                    "folder_id": folder_id,
                    "source_document_id": source_document_id,
                    "topic": topic,
                    "question": quiz["question"],
                    "quiz_type": quiz.get("quiz_type", "multiple_choice"),
                    "quiz_options": quiz.get("options", []),
                    "correct_option": quiz.get("correct_option"),
                    "correct_answer": quiz.get("correct_answer"),
                    "difficulty": quiz.get("difficulty", "medium"),
                    "answer": quiz.get("explanation", ""),
                    "created_at": datetime.utcnow()
                }
                quiz_docs.append(quiz_doc)
            
            quiz_ids = await self.insert_many("qapairs", quiz_docs)
            logger.info(f"퀴즈 {len(quiz_ids)}개 저장 완료")
            return quiz_ids
            
        except Exception as e:
            logger.error(f"퀴즈 저장 실패: {e}")
            raise
    
    async def save_recommendation_cache(
        self,
        recommendations: List[Dict],
        keywords: List[str],
        content_types: List[str],
        folder_id: Optional[str] = None
    ) -> str:
        """추천 결과 캐싱"""
        try:
            # 캐시 키 생성
            cache_data = f"{folder_id}_{sorted(keywords)}_{sorted(content_types)}"
            cache_key = hashlib.md5(cache_data.encode()).hexdigest()
            
            rec_doc = {
                "cache_key": cache_key,
                "folder_id": folder_id,
                "keywords": keywords,
                "content_types": content_types,
                "recommendations": recommendations,
                "created_at": datetime.utcnow(),
                "last_accessed_at": datetime.utcnow()
            }
            
            # 기존 캐시가 있으면 업데이트, 없으면 생성
            existing = await self.find_one("recommendations", {"cache_key": cache_key})
            if existing:
                await self.update_one(
                    "recommendations",
                    {"cache_key": cache_key},
                    {"$set": {
                        "recommendations": recommendations,
                        "last_accessed_at": datetime.utcnow()
                    }}
                )
                return str(existing["_id"])
            else:
                return await self.insert_one("recommendations", rec_doc)
                
        except Exception as e:
            logger.error(f"추천 캐시 저장 실패: {e}")
            raise
    
    async def get_recommendation_cache(
        self,
        keywords: List[str],
        content_types: List[str],
        folder_id: Optional[str] = None
    ) -> Optional[Dict]:
        """추천 캐시 조회"""
        try:
            cache_data = f"{folder_id}_{sorted(keywords)}_{sorted(content_types)}"
            cache_key = hashlib.md5(cache_data.encode()).hexdigest()
            
            return await self.find_one("recommendations", {"cache_key": cache_key})
            
        except Exception as e:
            logger.error(f"추천 캐시 조회 실패: {e}")
            return None
    
    async def save_document_labels(
        self,
        document_id: str,
        folder_id: Optional[str],
        labels: Dict
    ) -> str:
        """문서 라벨 저장"""
        try:
            label_doc = {
                "document_id": document_id,
                "folder_id": folder_id,
                **labels,
                "created_at": datetime.utcnow()
            }
            
            # 기존 라벨이 있으면 업데이트, 없으면 생성
            existing = await self.find_one("labels", {"document_id": document_id})
            if existing:
                await self.update_one(
                    "labels",
                    {"document_id": document_id},
                    {"$set": label_doc}
                )
                return str(existing["_id"])
            else:
                return await self.insert_one("labels", label_doc)
                
        except Exception as e:
            logger.error(f"문서 라벨 저장 실패: {e}")
            raise

    # === 보고서 관련 메서드들 ===
    
    async def save_report(self, report_data: Dict) -> str:
        """보고서 데이터 저장"""
        try:
            report_id = await self.insert_one("reports", report_data)
            logger.info(f"보고서 저장 완료: {report_data['title']} ({report_id})")
            return report_id
            
        except Exception as e:
            logger.error(f"보고서 저장 실패: {e}")
            raise
    
    async def get_report_by_id(self, report_id: str) -> Optional[Dict]:
        """ID로 보고서 조회"""
        try:
            # ObjectId 형태인지 확인
            if len(report_id) == 24:
                report = await self.find_one("reports", {"_id": ObjectId(report_id)})
            else:
                # report_id 필드로 검색
                report = await self.find_one("reports", {"report_id": report_id})
            
            return report
            
        except Exception as e:
            logger.error(f"보고서 조회 실패: {e}")
            return None
    
    async def get_reports_by_folder(
        self,
        folder_id: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[Dict]:
        """폴더별 보고서 목록 조회"""
        try:
            reports = await self.find_many(
                "reports",
                {"folder_id": folder_id},
                limit=limit,
                skip=skip
            )
            
            # 최신순으로 정렬
            reports.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
            return reports
            
        except Exception as e:
            logger.error(f"폴더별 보고서 조회 실패: {e}")
            return []
    
    async def get_all_reports(
        self,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict]:
        """전체 보고서 목록 조회 (최신순)"""
        try:
            reports = await self.find_many(
                "reports",
                {},
                limit=limit,
                skip=skip
            )
            
            # 최신순으로 정렬
            reports.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
            return reports
            
        except Exception as e:
            logger.error(f"전체 보고서 조회 실패: {e}")
            return []
    
    async def delete_report(self, report_id: str) -> bool:
        """보고서 삭제"""
        try:
            # ObjectId 형태인지 확인
            if len(report_id) == 24:
                success = await self.delete_one("reports", {"_id": ObjectId(report_id)})
            else:
                success = await self.delete_one("reports", {"report_id": report_id})
            
            if success:
                logger.info(f"보고서 삭제 완료: {report_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"보고서 삭제 실패: {e}")
            return False
    
    async def update_report(self, report_id: str, update_data: Dict) -> bool:
        """보고서 수정"""
        try:
            # 수정 시간 추가
            update_data["updated_at"] = datetime.utcnow()
            
            # ObjectId 형태인지 확인
            if len(report_id) == 24:
                success = await self.update_one(
                    "reports",
                    {"_id": ObjectId(report_id)},
                    {"$set": update_data}
                )
            else:
                success = await self.update_one(
                    "reports",
                    {"report_id": report_id},
                    {"$set": update_data}
                )
            
            if success:
                logger.info(f"보고서 수정 완료: {report_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"보고서 수정 실패: {e}")
            return False
    
    async def get_folder_files_for_report(self, folder_id: str) -> List[Dict]:
        """보고서 생성용 폴더 내 파일 목록 조회"""
        try:
            # documents 컬렉션에서 폴더별 파일 정보 조회
            documents = await self.find_many("documents", {"folder_id": folder_id})
            
            # 파일별로 그룹화하여 고유 파일 목록 생성
            files_dict = {}
            for doc in documents:
                file_metadata = doc.get("file_metadata", {})
                file_id = file_metadata.get("file_id")
                
                if file_id and file_id not in files_dict:
                    files_dict[file_id] = {
                        "file_id": file_id,
                        "filename": file_metadata.get("original_filename", "Unknown"),
                        "file_type": file_metadata.get("file_type", "unknown"),
                        "file_size": file_metadata.get("file_size", 0),
                        "description": file_metadata.get("description", ""),
                        "chunk_count": 0
                    }
                
                # 청크 수 카운트
                if file_id in files_dict:
                    files_dict[file_id]["chunk_count"] += 1
            
            # 리스트로 변환하고 파일명 순으로 정렬
            file_list = list(files_dict.values())
            file_list.sort(key=lambda x: x["filename"])
            
            logger.info(f"폴더 {folder_id}에서 {len(file_list)}개 파일 조회")
            return file_list
            
        except Exception as e:
            logger.error(f"폴더 파일 목록 조회 실패: {e}")
            return []
    
    async def get_documents_content_by_files(
        self,
        folder_id: str,
        selected_file_ids: List[str]
    ) -> List[str]:
        """선택된 파일들의 문서 내용 조회"""
        try:
            documents = await self.find_many(
                "documents",
                {
                    "folder_id": folder_id,
                    "file_metadata.file_id": {"$in": selected_file_ids}
                }
            )
            
            # 파일별로 그룹화하고 청크 순서대로 정렬
            files_content = {}
            for doc in documents:
                file_id = doc.get("file_metadata", {}).get("file_id")
                chunk_sequence = doc.get("chunk_sequence", 0)
                content = doc.get("raw_text", "")
                
                if file_id not in files_content:
                    files_content[file_id] = []
                
                files_content[file_id].append((chunk_sequence, content))
            
            # 각 파일의 청크들을 순서대로 정렬하고 결합
            combined_contents = []
            for file_id in selected_file_ids:
                if file_id in files_content:
                    # 청크 순서대로 정렬
                    chunks = sorted(files_content[file_id], key=lambda x: x[0])
                    # 내용만 추출하여 결합
                    file_content = "\n".join([chunk[1] for chunk in chunks])
                    combined_contents.append(file_content)
            
            logger.info(f"선택된 {len(selected_file_ids)}개 파일의 내용 조회 완료")
            return combined_contents
            
        except Exception as e:
            logger.error(f"문서 내용 조회 실패: {e}")
            return []
    
    async def get_report_statistics(self, folder_id: Optional[str] = None) -> Dict:
        """보고서 통계 조회"""
        try:
            filter_dict = {"folder_id": folder_id} if folder_id else {}
            reports = await self.find_many("reports", filter_dict)
            
            if not reports:
                return {
                    "total_reports": 0,
                    "average_pages": 0,
                    "average_word_count": 0,
                    "most_common_topics": [],
                    "recent_reports": []
                }
            
            # 통계 계산
            total_reports = len(reports)
            total_pages = sum(r.get("metadata", {}).get("total_pages", 0) for r in reports)
            total_words = sum(r.get("metadata", {}).get("word_count", 0) for r in reports)
            
            # 주제별 빈도 계산
            topics = [r.get("analysis_summary", {}).get("main_topic", "기타") for r in reports]
            topic_counts = {}
            for topic in topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            most_common_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 최근 보고서 (5개)
            recent_reports = sorted(reports, key=lambda x: x.get("created_at", datetime.min), reverse=True)[:5]
            recent_reports_info = [
                {
                    "report_id": r["report_id"],
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "pages": r.get("metadata", {}).get("total_pages", 0)
                }
                for r in recent_reports
            ]
            
            return {
                "total_reports": total_reports,
                "average_pages": round(total_pages / total_reports, 1) if total_reports > 0 else 0,
                "average_word_count": round(total_words / total_reports) if total_reports > 0 else 0,
                "most_common_topics": most_common_topics,
                "recent_reports": recent_reports_info
            }
            
        except Exception as e:
            logger.error(f"보고서 통계 조회 실패: {e}")
            return {
                "total_reports": 0,
                "average_pages": 0,
                "average_word_count": 0,
                "most_common_topics": [],
                "recent_reports": []
            }
