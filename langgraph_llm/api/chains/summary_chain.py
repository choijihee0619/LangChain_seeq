"""
요약 체인
문서 요약 생성
MODIFIED 2024-12-20: 요약 결과 캐싱 기능 추가 및 새 DB 구조 적용
"""
from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from ai_processing.llm_client import LLMClient
from database.operations import DatabaseOperations
from utils.logger import get_logger
from bson import ObjectId

logger = get_logger(__name__)

class SummaryChain:
    """요약 체인 클래스"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.db_ops = DatabaseOperations(db)
        self.llm_client = LLMClient()
        self.documents = db.documents
        self.chunks = db.chunks
        self.file_info = db.file_info
    
    async def process(
        self,
        document_ids: Optional[List[str]] = None,
        folder_id: Optional[str] = None,
        summary_type: str = "brief"
    ) -> Dict:
        """요약 처리"""
        try:
            # document_ids 정리 - "string", "null" 같은 기본값 제거
            clean_document_ids = None
            if document_ids:
                clean_document_ids = [
                    doc_id.strip() for doc_id in document_ids 
                    if doc_id and doc_id.strip() and doc_id.strip() not in ["string", "null"]
                ]
                if not clean_document_ids:
                    clean_document_ids = None
            
            # folder_id 정리
            clean_folder_id = None
            if folder_id and folder_id.strip() and folder_id.strip() not in ["string", "null"]:
                clean_folder_id = folder_id.strip()
            
            logger.info(f"요약 처리 시작 - document_ids: {clean_document_ids}, folder_id: '{clean_folder_id}'")
            
            # 1. 캐시 확인
            cached_summary = await self.db_ops.get_summary_cache(
                folder_id=clean_folder_id,
                document_ids=clean_document_ids,
                summary_type=summary_type
            )
            
            if cached_summary:
                logger.info("캐시된 요약 발견, 캐시 사용")
                # 폴더 접근 시간 업데이트
                if clean_folder_id:
                    await self.db_ops.update_folder_access(clean_folder_id)
                
                return {
                    "summary": cached_summary["summary"],
                    "document_count": len(cached_summary.get("document_ids", [])),
                    "from_cache": True,
                    "cache_created_at": cached_summary.get("created_at")
                }
            
            # 2. 새로운 요약 생성
            summary_result = await self._generate_new_summary(
                clean_document_ids, clean_folder_id, summary_type
            )
            
            # 3. 요약 결과 캐싱
            try:
                await self.db_ops.save_summary_cache(
                    summary=summary_result["summary"],
                    folder_id=clean_folder_id,
                    document_ids=clean_document_ids,
                    summary_type=summary_type
                )
                logger.info("요약 결과 캐시 저장 완료")
            except Exception as cache_error:
                logger.warning(f"요약 캐시 저장 실패: {cache_error}")
            
            # 4. 폴더 접근 시간 업데이트
            if clean_folder_id:
                await self.db_ops.update_folder_access(clean_folder_id)
            
            summary_result["from_cache"] = False
            return summary_result
            
        except Exception as e:
            logger.error(f"요약 처리 실패: {e}")
            raise
    
    async def _generate_new_summary(
        self,
        document_ids: Optional[List[str]],
        folder_id: Optional[str],
        summary_type: str
    ) -> Dict:
        """새로운 요약 생성"""
        
        # 문서 조회 조건 설정
        if document_ids:
            # document_ids가 제공된 경우, 새로운 documents 컬렉션에서 해당 file_id들을 가진 파일들 찾기
            logger.info(f"특정 문서 요약 처리: {document_ids}")
            
            # documents 컬렉션에서 file_metadata.file_id로 조회
            documents = await self.db_ops.find_many(
                "documents", 
                {"file_metadata.file_id": {"$in": document_ids}}
            )
            
            if not documents:
                logger.warning(f"요약할 문서를 찾을 수 없음: {document_ids}")
                return {
                    "summary": "요약할 문서가 없습니다.",
                    "document_count": 0
                }
            
            logger.info(f"요약할 문서 {len(documents)}개 발견")
            
            # 문서들의 raw_text를 결합
            texts = []
            for doc in documents:
                raw_text = doc.get("raw_text", "")
                if raw_text:
                    texts.append(raw_text)
            
            if not texts:
                return {
                    "summary": "요약할 텍스트가 없습니다.",
                    "document_count": len(documents)
                }
            
            combined_text = "\n\n".join(texts)
            document_count = len(documents)
            
        elif folder_id:
            # folder_id가 제공된 경우, 새로운 documents 컬렉션에서 조회
            logger.info(f"폴더별 요약 처리: {folder_id}")
            
            # 해당 폴더의 모든 documents 조회
            folder_documents = await self.db_ops.find_many("documents", {"folder_id": folder_id})
            
            if not folder_documents:
                return {
                    "summary": "요약할 문서가 없습니다.",
                    "document_count": 0
                }
            
            logger.info(f"폴더 '{folder_id}'에서 {len(folder_documents)}개 문서 발견")
            
            # documents의 raw_text들을 결합
            combined_text = "\n\n".join([doc["raw_text"] for doc in folder_documents])
            
            # 파일 개수 계산 (중복 제거)
            unique_file_ids = set()
            for doc in folder_documents:
                file_metadata = doc.get("file_metadata", {})
                if "file_id" in file_metadata:
                    unique_file_ids.add(file_metadata["file_id"])
            
            document_count = len(unique_file_ids)
            
        else:
            raise ValueError("document_ids 또는 folder_id가 필요합니다.")
        
        # 텍스트가 너무 긴 경우 제한
        if len(combined_text) > 8000:  # 토큰 제한 고려
            combined_text = combined_text[:8000] + "..."
            logger.warning("텍스트가 너무 길어 8000자로 제한했습니다.")
        
        logger.info(f"요약할 텍스트 길이: {len(combined_text)} 문자")
        
        # 프롬프트 선택
        if summary_type == "brief":
            prompt = f"다음 텍스트를 1-2문장으로 간단히 요약해주세요:\n\n{combined_text}"
        elif summary_type == "detailed":
            prompt = f"다음 텍스트를 상세하게 요약해주세요. 주요 내용과 핵심 포인트를 포함하여 작성해주세요:\n\n{combined_text}"
        else:  # bullets
            prompt = f"다음 텍스트의 핵심 내용을 불릿 포인트로 정리해주세요:\n\n{combined_text}"
        
        # 요약 생성
        summary = await self.llm_client.generate(prompt, max_tokens=500)
        
        logger.info(f"요약 완료 - 문서 수: {document_count}, 요약 길이: {len(summary)}")
        
        return {
            "summary": summary,
            "document_count": document_count
        }
    
    async def get_cached_summaries(self, folder_id: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """캐시된 요약 목록 조회"""
        try:
            filter_dict = {}
            if folder_id:
                filter_dict["folder_id"] = folder_id
            
            cached_summaries = await self.db_ops.find_many(
                "summaries", 
                filter_dict, 
                limit=limit
            )
            
            return [
                {
                    "cache_id": str(summary["_id"]),
                    "summary_type": summary["summary_type"],
                    "summary_preview": summary["summary"][:100] + "..." if len(summary["summary"]) > 100 else summary["summary"],
                    "document_count": len(summary.get("document_ids", [])),
                    "created_at": summary["created_at"],
                    "last_accessed_at": summary["last_accessed_at"]
                }
                for summary in cached_summaries
            ]
            
        except Exception as e:
            logger.error(f"캐시된 요약 목록 조회 실패: {e}")
            return []
    
    async def delete_summary_cache(self, cache_id: str) -> bool:
        """요약 캐시 삭제"""
        try:
            return await self.db_ops.delete_one("summaries", {"_id": ObjectId(cache_id)})
        except Exception as e:
            logger.error(f"요약 캐시 삭제 실패: {e}")
            return False
