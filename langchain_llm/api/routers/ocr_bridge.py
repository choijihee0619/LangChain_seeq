"""
OCR 브릿지 API 라우터
기존 OCR 데이터베이스(ocr_db.texts)와 RAG 시스템 간의 브릿지 역할
기존 데이터를 건드리지 않고 안전하게 통합 관리
CREATED 2024-12-20: 기존 OCR 데이터 안전 통합을 위한 브릿지 API
UPDATED 2025-06-04: 동기화 완료 후 중복 엔드포인트 정리
ENHANCED 2025-06-10: 완전 재설계된 동기화 시스템
CLEANED 2025-06-10: 중복 엔드포인트 5개 제거 (sync/all, sync/clean, 구버전 sync, process/search, sync/reset)
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Optional
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId

from database.connection import get_database
from database.ocr_bridge import OCRBridge
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["OCR Bridge"])

class OCRStatsResponse(BaseModel):
    """OCR 통계 응답 모델"""
    total_documents: int
    last_updated: Optional[str]
    text_stats: Dict
    database_info: Dict

async def get_ocr_bridge() -> OCRBridge:
    """OCR 브릿지 인스턴스 생성"""
    rag_db = await get_database()
    return OCRBridge(rag_db)

@router.get("/stats", response_model=OCRStatsResponse)
async def get_ocr_statistics():
    """
    OCR 데이터베이스 통계 조회
    
    - 총 문서 수, 마지막 업데이트 시간
    - 텍스트 길이 통계 (평균, 최대, 최소)
    - 데이터베이스 정보
    """
    try:
        ocr_bridge = await get_ocr_bridge()
        stats = await ocr_bridge.get_ocr_stats()
        
        if "error" in stats:
            # OCR 데이터베이스 연결 문제인 경우 적절한 응답 반환
            if "연결" in stats["error"] or "설정" in stats["error"]:
                return OCRStatsResponse(
                    total_documents=0,
                    last_updated=None,
                    text_stats={
                        "average_length": 0,
                        "max_length": 0,
                        "min_length": 0
                    },
                    database_info={
                        "source_db": "ocr_db.texts",
                        "integration_type": "bridge",
                        "data_preservation": "OCR 데이터베이스 연결 불가",
                        "sync_status": f"연결 오류: {stats['error']}"
                    }
                )
            else:
                raise HTTPException(status_code=500, detail=stats["error"])
        
        return OCRStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류 발생: {str(e)}")
    finally:
        if 'ocr_bridge' in locals():
            await ocr_bridge.close_ocr_db()

@router.post("/sync/force")
async def force_sync_all_ocr_data():
    """모든 OCR 데이터를 강제로 동기화 (청킹/임베딩 자동 포함)"""
    try:
        db = await get_database()
        ocr_bridge = OCRBridge(db)
        
        try:
            result = await ocr_bridge.force_sync_all_data()
            
            return {
                "success": True,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
                "note": "OCR 데이터가 청킹/임베딩까지 완전 처리됨"
            }
            
        finally:
            await ocr_bridge.close_ocr_db()
    
    except Exception as e:
        logger.error(f"강제 OCR 동기화 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"강제 OCR 동기화 실패: {str(e)}"
        )

@router.get("/status")
async def check_ocr_bridge_status():
    """
    OCR 브릿지 연결 상태 확인 (/status 엔드포인트)
    
    - OCR 데이터베이스 연결 테스트
    - RAG 데이터베이스 연결 테스트
    """
    try:
        ocr_bridge = await get_ocr_bridge()
        
        # RAG 데이터베이스 연결 테스트  
        rag_ping = await ocr_bridge.rag_db.command("ping")
        
        # OCR 데이터베이스 연결 테스트 (Motor 드라이버 오류 수정)
        ocr_status = "disconnected"
        ocr_error = None
        try:
            await ocr_bridge.connect_ocr_db()
            # Motor 드라이버 bool 평가 오류 수정: if ocr_bridge.ocr_db → if ocr_bridge.ocr_db is not None
            if ocr_bridge.ocr_db is not None:
                ocr_ping = await ocr_bridge.ocr_db.command("ping")
                ocr_status = "connected" if ocr_ping else "disconnected"
            else:
                ocr_status = "unavailable"
                ocr_error = "OCR 데이터베이스 설정이 없거나 연결 실패"
        except Exception as ocr_e:
            ocr_status = "error"
            ocr_error = str(ocr_e)
        
        bridge_status = "operational" if rag_ping else "degraded"
        overall_status = "healthy" if rag_ping else "unhealthy"
        
        result = {
            "status": overall_status,
            "ocr_database": ocr_status,
            "rag_database": "connected" if rag_ping else "disconnected",
            "bridge_status": bridge_status,
            "timestamp": datetime.utcnow().isoformat(),
            "notes": {
                "ocr_functionality": "OCR 브릿지는 선택적 기능입니다",
                "rag_core": "RAG 핵심 기능은 정상 작동"
            }
        }
        
        if ocr_error:
            result["ocr_error"] = ocr_error
            
        return result
        
    except Exception as e:
        logger.error(f"OCR 브릿지 상태 확인 실패: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "notes": {
                "message": "브릿지 상태 확인 중 오류 발생"
            }
        }
    finally:
        if 'ocr_bridge' in locals():
            await ocr_bridge.close_ocr_db()

@router.get("/folder/ocr")
async def get_or_create_ocr_folder():
    """
    OCR 전용 폴더 조회 또는 생성 (더 이상 사용되지 않음)
    
    - 새로운 구조에서는 title별로 폴더가 자동 생성됨
    - 모든 OCR 폴더 목록 반환
    """
    ocr_bridge = None
    try:
        ocr_bridge = await get_ocr_bridge()
        
        # 모든 OCR 폴더 조회
        ocr_folders = await ocr_bridge.rag_db.folders.find(
            {"folder_type": "ocr"}
        ).to_list(None)
        
        # ObjectId를 문자열로 변환
        for folder in ocr_folders:
            if folder and "_id" in folder:
                folder["_id"] = str(folder["_id"])
                # datetime 객체도 문자열로 변환
                for key, value in folder.items():
                    if isinstance(value, datetime):
                        folder[key] = value.isoformat()
        
        return {
            "total_ocr_folders": len(ocr_folders),
            "folders": ocr_folders,
            "purpose": "OCR 텍스트가 title별로 분류된 폴더들",
            "note": "새로운 OCR 데이터는 title에 따라 자동으로 폴더가 생성됩니다"
        }
        
    except Exception as e:
        logger.error(f"OCR 폴더 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"폴더 처리 중 오류 발생: {str(e)}")
    finally:
        if ocr_bridge is not None:
            await ocr_bridge.close_ocr_db()

@router.get("/folders/list")
async def list_all_ocr_folders():
    """
    모든 OCR 폴더 목록 조회
    
    - title별로 분류된 모든 OCR 폴더
    - 각 폴더의 문서 수와 상태 정보
    """
    try:
        ocr_bridge = await get_ocr_bridge()
        
        # 모든 OCR 폴더 조회 (문서 수 내림차순 정렬)
        ocr_folders = await ocr_bridge.rag_db.folders.find(
            {"folder_type": "ocr"}
        ).sort("document_count", -1).to_list(None)
        
        # 폴더 정보 정리
        folder_list = []
        total_documents = 0
        
        for folder in ocr_folders:
            folder_info = {
                "folder_id": str(folder["_id"]),
                "title": folder["title"],
                "document_count": folder.get("document_count", 0),
                "file_count": folder.get("file_count", 0),
                "created_at": folder["created_at"].isoformat() if isinstance(folder.get("created_at"), datetime) else folder.get("created_at"),
                "last_accessed_at": folder["last_accessed_at"].isoformat() if isinstance(folder.get("last_accessed_at"), datetime) else folder.get("last_accessed_at"),
                "description": folder.get("description", "")
            }
            folder_list.append(folder_info)
            total_documents += folder.get("document_count", 0)
        
        return {
            "total_folders": len(folder_list),
            "total_documents": total_documents,
            "folders": folder_list,
            "note": "OCR 데이터가 title별로 자동 분류되어 저장됩니다"
        }
        
    except Exception as e:
        logger.error(f"OCR 폴더 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"폴더 목록 조회 중 오류 발생: {str(e)}")
    finally:
        if 'ocr_bridge' in locals():
            await ocr_bridge.close_ocr_db()

@router.get("/")
async def ocr_bridge_info():
    """
    OCR 브릿지 정보 및 사용 가이드
    """
    return {
        "name": "OCR 브릿지",
        "version": "1.1.0",
        "description": "OCR 데이터베이스와 RAG 시스템 간의 브릿지",
        "status": "완전 자동화 완료 - 중복 기능 정리됨",
        "main_endpoint": {
            "sync/force": "전체 OCR 데이터 완전 동기화 (청킹/임베딩 자동 포함)"
        },
        "other_endpoints": {
            "stats": "OCR 원본 데이터베이스 통계",
            "status": "브릿지 상태 확인",
            "folders/list": "OCR 폴더 목록",
            "debug/*": "디버깅 도구들"
        },
        "usage_guide": {
            "search": "일반 검색 사용: /upload/search?q=키워드",
            "ocr_only_search": "OCR만 검색: /upload/search?q=키워드&folder_id={ocr_folder_id}",
            "folder_search": "/ocr-bridge/folders/list로 OCR 폴더 확인 가능"
        },
        "removed_endpoints": {
            "sync/all": "→ sync/force로 통합됨",
            "sync/clean": "→ sync/force로 통합됨",
            "sync (구버전)": "→ 중복 제거됨",
            "process/search": "→ 자동 처리로 불필요해짐",
            "sync/reset": "→ 디버깅용으로 제거됨"
        },
        "note": "새로운 OCR 데이터는 sync/force로 완전 자동 처리됩니다."
    }

@router.get("/debug/chunks/{folder_id}")
async def debug_ocr_chunks(
    folder_id: str,
    db = Depends(get_database)
) -> Dict:
    """
    디버깅용: 특정 폴더의 OCR 청크 데이터 확인
    """
    try:
        # chunks 컬렉션에서 OCR 데이터 조회
        chunks = await db.chunks.find({"folder_id": folder_id}).limit(5).to_list(5)
        
        # 기본 통계
        total_chunks = await db.chunks.count_documents({"folder_id": folder_id})
        
        # 임베딩 벡터가 있는 청크 수
        chunks_with_embedding = await db.chunks.count_documents({
            "folder_id": folder_id, 
            "text_embedding": {"$exists": True, "$ne": None}
        })
        
        # 결과 포맷팅 (텍스트 임베딩은 크기 확인만)
        formatted_chunks = []
        for chunk in chunks:
            formatted_chunk = {
                "chunk_id": chunk.get("chunk_id"),
                "file_id": chunk.get("file_id"),
                "sequence": chunk.get("sequence"),
                "text_preview": chunk.get("text", "")[:200] + "..." if len(chunk.get("text", "")) > 200 else chunk.get("text", ""),
                "has_embedding": "text_embedding" in chunk and chunk["text_embedding"] is not None,
                "embedding_size": len(chunk["text_embedding"]) if "text_embedding" in chunk and chunk["text_embedding"] else 0,
                "metadata": chunk.get("metadata", {})
            }
            formatted_chunks.append(formatted_chunk)
        
        return {
            "folder_id": folder_id,
            "total_chunks": total_chunks,
            "chunks_with_embedding": chunks_with_embedding,
            "sample_chunks": formatted_chunks,
            "debug_info": {
                "query_filter": {"folder_id": folder_id},
                "embedding_status": f"{chunks_with_embedding}/{total_chunks} 청크가 임베딩을 가지고 있음"
            }
        }
        
    except Exception as e:
        logger.error(f"OCR 청크 디버깅 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"OCR 청크 디버깅 실패: {str(e)}"
        ) 

@router.get("/debug/failed-docs")
async def debug_failed_documents(
    db = Depends(get_database)
) -> Dict:
    """
    디버깅용: 동기화 실패한 OCR 문서들의 구조 확인
    """
    try:
        ocr_bridge = OCRBridge(db)
        
        try:
            # OCR 데이터베이스 연결
            await ocr_bridge.connect_ocr_db()
            
            # 모든 OCR 문서 조회
            all_ocr_docs = await ocr_bridge.ocr_db.texts.find({}).to_list(None)
            
            # 이미 동기화된 문서들의 ID 조회
            synced_docs = await db.documents.find(
                {"data_source": "ocr_bridge"}
            ).to_list(None)
            synced_ids = [doc["original_ocr_id"] for doc in synced_docs]
            
            # 실패한 문서들 찾기
            failed_docs = []
            for doc in all_ocr_docs:
                doc_id = str(doc["_id"])
                if doc_id not in synced_ids:
                    # 문서 구조 분석
                    doc_info = {
                        "id": doc_id,
                        "title": doc.get("title", "제목없음"),
                        "timestamp": str(doc.get("timestamp", "없음")),
                        "has_pages": "pages" in doc,
                        "pages_type": type(doc.get("pages", None)).__name__,
                        "pages_length": len(doc["pages"]) if "pages" in doc and hasattr(doc["pages"], "__len__") else "N/A",
                        "has_text": "text" in doc,
                        "text_type": type(doc.get("text", None)).__name__,
                        "other_fields": [key for key in doc.keys() if key not in ["_id", "title", "timestamp", "pages", "text"]],
                    }
                    
                    # pages 내용 샘플
                    if "pages" in doc:
                        if isinstance(doc["pages"], list) and len(doc["pages"]) > 0:
                            first_page = doc["pages"][0]
                            doc_info["first_page_type"] = type(first_page).__name__
                            if isinstance(first_page, dict):
                                doc_info["first_page_keys"] = list(first_page.keys())
                                doc_info["first_page_sample"] = {k: str(v)[:100] + "..." if len(str(v)) > 100 else str(v) for k, v in first_page.items()}
                            else:
                                doc_info["first_page_sample"] = str(first_page)[:200] + "..." if len(str(first_page)) > 200 else str(first_page)
                        else:
                            doc_info["pages_sample"] = str(doc["pages"])[:200] + "..." if len(str(doc["pages"])) > 200 else str(doc["pages"])
                    
                    failed_docs.append(doc_info)
            
            return {
                "total_ocr_docs": len(all_ocr_docs),
                "synced_docs": len(synced_ids),
                "failed_docs": len(failed_docs),
                "failed_documents": failed_docs
            }
            
        finally:
            await ocr_bridge.close_ocr_db()
    
    except Exception as e:
        logger.error(f"실패 문서 디버깅 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"실패 문서 디버깅 실패: {str(e)}"
        ) 

@router.post("/sync")
async def sync_new_ocr_data(
    since_date: Optional[str] = Query(None, description="동기화 시작 날짜 (YYYY-MM-DD 형식)")
):
    """새로운 OCR 데이터만 동기화 (청킹/임베딩 자동 포함)"""
    try:
        db = await get_database()
        ocr_bridge = OCRBridge(db)
        
        # 날짜 파싱
        since_timestamp = None
        if since_date:
            try:
                since_timestamp = datetime.strptime(since_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요.")
        
        try:
            result = await ocr_bridge.sync_new_ocr_data(since_timestamp)
            
            return {
                "success": True,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
                "note": "새로운 OCR 데이터가 청킹/임베딩까지 완전 처리됨"
            }
            
        finally:
            await ocr_bridge.close_ocr_db()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR 동기화 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"OCR 동기화 실패: {str(e)}"
        ) 