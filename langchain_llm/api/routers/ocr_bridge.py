"""
OCR 브릿지 API 라우터
기존 OCR 데이터베이스(ocr_db.texts)와 RAG 시스템 간의 브릿지 역할
기존 데이터를 건드리지 않고 안전하게 통합 관리
CREATED 2024-12-20: 기존 OCR 데이터 안전 통합을 위한 브릿지 API
UPDATED 2025-06-04: 동기화 완료 후 중복 엔드포인트 정리
"""
from fastapi import APIRouter, HTTPException, Query
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

class OCRSyncResponse(BaseModel):
    """OCR 동기화 응답 모델"""
    synced_count: int
    total_new_data: int
    last_sync_time: str
    message: Optional[str]

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

@router.post("/sync", response_model=OCRSyncResponse)
async def sync_ocr_data(
    since_date: Optional[str] = Query(None, description="동기화 시작 날짜 (YYYY-MM-DD 형식)")
):
    """
    OCR 데이터 동기화
    
    - 새로운 OCR 데이터만 RAG 시스템으로 동기화
    - 기존 데이터는 건드리지 않음
    - 실제로는 메타데이터만 복사
    """
    try:
        ocr_bridge = await get_ocr_bridge()
        
        since_timestamp = None
        if since_date:
            try:
                since_timestamp = datetime.strptime(since_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요.")
        
        sync_result = await ocr_bridge.sync_new_ocr_data(since_timestamp)
        
        return OCRSyncResponse(
            synced_count=sync_result["synced_count"],
            total_new_data=sync_result.get("total_new_data", 0),
            last_sync_time=sync_result["last_sync_time"].isoformat(),
            message=sync_result.get("message")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR 데이터 동기화 실패: {e}")
        raise HTTPException(status_code=500, detail=f"동기화 중 오류 발생: {str(e)}")
    finally:
        await ocr_bridge.close_ocr_db()

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
        
        # OCR 데이터베이스 연결 테스트
        ocr_status = "disconnected"
        ocr_error = None
        try:
            await ocr_bridge.connect_ocr_db()
            if ocr_bridge.ocr_db:
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
    OCR 전용 폴더 조회 또는 생성
    
    - 'OCR 텍스트' 폴더가 없으면 자동 생성
    - 폴더 정보 반환
    """
    ocr_bridge = None
    try:
        ocr_bridge = await get_ocr_bridge()
        folder_id = await ocr_bridge.get_or_create_ocr_folder()
        
        # 폴더 상세 정보 조회
        folder_info = await ocr_bridge.rag_db.folders.find_one(
            {"_id": ObjectId(folder_id)}
        )
        
        # ObjectId를 문자열로 변환
        if folder_info and "_id" in folder_info:
            folder_info["_id"] = str(folder_info["_id"])
            # datetime 객체도 문자열로 변환
            for key, value in folder_info.items():
                if isinstance(value, datetime):
                    folder_info[key] = value.isoformat()
        
        return {
            "folder_id": folder_id,
            "folder_info": folder_info,
            "purpose": "OCR 텍스트 전용 폴더",
            "search_tip": f"일반 검색에서 folder_id={folder_id} 사용하여 OCR 데이터만 검색 가능"
        }
        
    except Exception as e:
        logger.error(f"OCR 폴더 조회/생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"폴더 처리 중 오류 발생: {str(e)}")
    finally:
        if ocr_bridge is not None:
            await ocr_bridge.close_ocr_db()

@router.get("/")
async def ocr_bridge_info():
    """
    OCR 브릿지 정보 및 사용 가이드
    """
    return {
        "name": "OCR 브릿지",
        "version": "1.0.0",
        "description": "OCR 데이터베이스와 RAG 시스템 간의 브릿지",
        "status": "동기화 완료 - 일반 검색 사용 권장",
        "endpoints": {
            "stats": "OCR 원본 데이터베이스 통계",
            "sync": "OCR 데이터 동기화", 
            "status": "브릿지 상태 확인",
            "folder/ocr": "OCR 폴더 정보"
        },
        "usage_guide": {
            "search": "일반 검색 사용: /query/search?q=키워드",
            "ocr_only_search": "OCR만 검색: /query/search?q=키워드&folder_id={ocr_folder_id}",
            "folder_search": "/folders 엔드포인트로 OCR 폴더 확인 가능"
        },
        "removed_endpoints": {
            "documents": "→ /query/search + folder_id 사용",
            "search": "→ /query/search 사용",
            "documents/{id}": "→ 일반 문서 조회 사용"
        },
        "note": "새로운 OCR 데이터는 자동으로 감지되어 동기화됩니다."
    } 