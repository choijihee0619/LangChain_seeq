"""
보고서 생성 및 관리 API
학술적 보고서 자동 생성 및 관리 시스템
CREATED 2024-12-20: 폴더 기반 문서 분석 및 보고서 생성
MODIFIED 2024-12-20: API 구조 개선 - 상태 조회 제거, 목록 API 통합, 논리적 순서 재정렬
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from database.connection import get_db
from database.operations import DatabaseOperations
from ai_processing.report_generator import ReportGenerator
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# === Pydantic 모델들 ===

class FileSelection(BaseModel):
    """파일 선택 정보"""
    file_id: str = Field(..., description="파일 고유 ID")
    filename: str = Field(..., description="파일명")
    file_type: str = Field(..., description="파일 타입")
    selected: bool = Field(True, description="선택 여부")

class ReportGenerationRequest(BaseModel):
    """보고서 생성 요청"""
    folder_id: str = Field(..., description="폴더 ID")
    selected_files: List[FileSelection] = Field(..., description="선택된 파일 목록")
    custom_title: Optional[str] = Field(None, description="사용자 지정 제목")
    background_generation: bool = Field(False, description="백그라운드 생성 여부 (기본: 동기 처리)")

class ReportSummary(BaseModel):
    """보고서 요약 정보"""
    report_id: str
    title: str
    subtitle: str
    folder_id: str
    created_at: datetime
    metadata: Dict[str, Any]
    analysis_summary: Dict[str, Any]

class ReportResponse(BaseModel):
    """보고서 전체 정보"""
    report_id: str
    title: str
    subtitle: str
    folder_id: str
    selected_files: List[Dict]
    report_structure: Dict[str, Any]
    analysis_summary: Dict[str, Any]
    metadata: Dict[str, Any]
    formatted_text: str
    created_at: datetime
    updated_at: datetime

# === 백그라운드 처리용 상태 관리 (최소한으로 유지) ===
background_reports = {}

# === API 엔드포인트들 (논리적 순서) ===

@router.get("/files/{folder_id}", response_model=List[Dict])
async def get_folder_files(folder_id: str):
    """
    1단계: 폴더 내 파일 목록 조회 (보고서 생성 준비)
    
    Args:
        folder_id: 폴더 ID (ObjectId 또는 폴더명)
    
    Returns:
        파일 목록 (체크박스 형태)
    """
    try:
        db = await get_db()
        db_ops = DatabaseOperations(db)
        
        # 폴더 ID 검증 및 변환
        if len(folder_id) != 24:
            folder = await db_ops.find_one("folders", {"title": folder_id})
            if not folder:
                raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다")
            folder_id = str(folder["_id"])
        
        # 폴더 내 파일 목록 조회
        files = await db_ops.get_folder_files_for_report(folder_id)
        
        if not files:
            raise HTTPException(status_code=404, detail="폴더에 파일이 없습니다")
        
        # 체크박스 형태로 반환
        file_list = [
            {
                "file_id": file_info["file_id"],
                "filename": file_info["filename"],
                "file_type": file_info["file_type"],
                "file_size": file_info["file_size"],
                "chunk_count": file_info["chunk_count"],
                "description": file_info.get("description", ""),
                "selected": False  # 기본적으로 선택 해제
            }
            for file_info in files
        ]
        
        logger.info(f"폴더 {folder_id}의 파일 목록 조회 완료: {len(file_list)}개")
        return file_list
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"폴더 파일 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="파일 목록 조회 중 오류가 발생했습니다")

@router.post("/generate", response_model=Dict)
async def generate_report(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    2단계: 보고서 생성 (기본: 동기 처리)
    
    Args:
        request: 보고서 생성 요청 데이터
        background_tasks: 백그라운드 작업 관리 (선택적)
    
    Returns:
        보고서 생성 결과
    """
    try:
        # 선택된 파일 확인
        selected_files = [f for f in request.selected_files if f.selected]
        if not selected_files:
            raise HTTPException(status_code=400, detail="최소 1개 이상의 파일을 선택해주세요")
        
        report_id = str(uuid.uuid4())
        
        if request.background_generation:
            # 백그라운드 생성 (특수한 경우에만)
            background_reports[report_id] = {
                "status": "processing",
                "created_at": datetime.utcnow()
            }
            
            background_tasks.add_task(
                _generate_report_background,
                report_id,
                request.folder_id,
                selected_files,
                request.custom_title
            )
            
            return {
                "message": "보고서 생성이 시작되었습니다",
                "report_id": report_id,
                "status": "processing",
                "background_generation": True,
                "estimated_time": "2-5분"
            }
        else:
            # 동기 생성 (권장)
            report_data = await _generate_report_sync(
                report_id,
                request.folder_id,
                selected_files,
                request.custom_title
            )
            
            return {
                "message": "보고서 생성이 완료되었습니다",
                "report_id": report_data["report_id"],
                "status": "completed",
                "background_generation": False,
                "title": report_data["title"],
                "subtitle": report_data["subtitle"]
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"보고서 생성 요청 실패: {e}")
        raise HTTPException(status_code=500, detail="보고서 생성 요청 중 오류가 발생했습니다")

@router.get("/", response_model=List[ReportSummary])
async def get_reports(
    folder_id: Optional[str] = Query(None, description="폴더 ID로 필터링 (선택사항)"),
    limit: int = Query(20, ge=1, le=100, description="조회할 보고서 수"),
    skip: int = Query(0, ge=0, description="건너뛸 보고서 수")
):
    """
    3단계: 보고서 목록 조회 (전체 또는 폴더별)
    
    Args:
        folder_id: 폴더 ID (선택사항 - 없으면 전체 조회)
        limit: 조회할 보고서 수
        skip: 건너뛸 보고서 수
    
    Returns:
        보고서 요약 목록
    """
    try:
        db = await get_db()
        db_ops = DatabaseOperations(db)
        
        if folder_id:
            # 폴더별 보고서 조회
            # 폴더 ID 검증 및 변환
            if len(folder_id) != 24:
                folder = await db_ops.find_one("folders", {"title": folder_id})
                if not folder:
                    raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다")
                folder_id = str(folder["_id"])
            
            reports = await db_ops.get_reports_by_folder(folder_id, limit, skip)
            logger.info(f"폴더 {folder_id}의 보고서 목록 조회 완료: {len(reports)}개")
        else:
            # 전체 보고서 조회
            reports = await db_ops.get_all_reports(limit, skip)
            logger.info(f"전체 보고서 목록 조회 완료: {len(reports)}개")
        
        return [
            ReportSummary(
                report_id=report["report_id"],
                title=report["title"],
                subtitle=report["subtitle"],
                folder_id=report["folder_id"],
                created_at=report["created_at"],
                metadata=report["metadata"],
                analysis_summary=report["analysis_summary"]
            )
            for report in reports
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"보고서 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="보고서 목록 조회 중 오류가 발생했습니다")

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str):
    """
    4단계: 보고서 상세 조회
    
    Args:
        report_id: 보고서 ID
    
    Returns:
        보고서 전체 정보
    """
    try:
        db = await get_db()
        db_ops = DatabaseOperations(db)
        
        # 먼저 백그라운드 처리 중인지 확인
        if report_id in background_reports:
            background_status = background_reports[report_id]
            if background_status["status"] == "processing":
                raise HTTPException(
                    status_code=202, 
                    detail="보고서가 아직 생성 중입니다. 잠시 후 다시 시도해주세요."
                )
        
        # 데이터베이스에서 보고서 조회
        report = await db_ops.get_report_by_id(report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다")
        
        # 포맷팅된 텍스트 생성
        report_generator = ReportGenerator()
        formatted_text = await report_generator.format_report_text(report)
        
        logger.info(f"보고서 {report_id} 조회 완료")
        
        return ReportResponse(
            report_id=report["report_id"],
            title=report["title"],
            subtitle=report["subtitle"],
            folder_id=report["folder_id"],
            selected_files=report["selected_files"],
            report_structure=report["report_structure"],
            analysis_summary=report["analysis_summary"],
            metadata=report["metadata"],
            formatted_text=formatted_text,
            created_at=report["created_at"],
            updated_at=report["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"보고서 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="보고서 조회 중 오류가 발생했습니다")

@router.delete("/{report_id}")
async def delete_report(report_id: str):
    """
    5단계: 보고서 삭제
    
    Args:
        report_id: 보고서 ID
    
    Returns:
        삭제 결과
    """
    try:
        db = await get_db()
        db_ops = DatabaseOperations(db)
        
        success = await db_ops.delete_report(report_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다")
        
        # 백그라운드 상태에서도 제거
        if report_id in background_reports:
            del background_reports[report_id]
        
        logger.info(f"보고서 {report_id} 삭제 완료")
        
        return {
            "message": "보고서가 성공적으로 삭제되었습니다",
            "report_id": report_id,
            "deleted_at": datetime.utcnow()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"보고서 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail="보고서 삭제 중 오류가 발생했습니다")

@router.get("/statistics/summary")
async def get_report_statistics(folder_id: Optional[str] = Query(None, description="폴더 ID로 필터링")):
    """
    6단계: 보고서 통계 조회
    
    Args:
        folder_id: 폴더 ID (선택사항)
    
    Returns:
        보고서 통계 정보
    """
    try:
        db = await get_db()
        db_ops = DatabaseOperations(db)
        
        # 폴더 ID 검증
        if folder_id and len(folder_id) != 24:
            folder = await db_ops.find_one("folders", {"title": folder_id})
            if folder:
                folder_id = str(folder["_id"])
            else:
                folder_id = None
        
        # 통계 조회
        if folder_id:
            total_reports = await db_ops.count_documents("reports", {"folder_id": folder_id})
            recent_reports = await db_ops.get_reports_by_folder(folder_id, 5, 0)
        else:
            total_reports = await db_ops.count_documents("reports", {})
            recent_reports = await db_ops.get_all_reports(5, 0)
        
        logger.info(f"보고서 통계 조회 완료 - 총 {total_reports}개")
        
        return {
            "total_reports": total_reports,
            "recent_reports_count": len(recent_reports),
            "folder_id": folder_id,
            "generated_at": datetime.utcnow(),
            "recent_reports": [
                {
                    "report_id": report["report_id"],
                    "title": report["title"],
                    "created_at": report["created_at"]
                }
                for report in recent_reports
            ]
        }
        
    except Exception as e:
        logger.error(f"보고서 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="통계 조회 중 오류가 발생했습니다")

# === 백그라운드 처리 함수들 ===

async def _generate_report_background(
    report_id: str,
    folder_id: str,
    selected_files: List[FileSelection],
    custom_title: Optional[str]
):
    """백그라운드 보고서 생성 (특수한 경우에만 사용)"""
    try:
        # 상태 업데이트
        background_reports[report_id]["status"] = "generating"
        
        # 실제 보고서 생성
        report_data = await _generate_report_sync(
            report_id,
            folder_id,
            selected_files,
            custom_title
        )
        
        # 완료 상태로 변경
        background_reports[report_id]["status"] = "completed"
        background_reports[report_id]["completed_at"] = datetime.utcnow()
        
        logger.info(f"백그라운드 보고서 생성 완료: {report_id}")
        
    except Exception as e:
        background_reports[report_id]["status"] = "failed"
        background_reports[report_id]["error"] = str(e)
        logger.error(f"백그라운드 보고서 생성 실패: {e}")

async def _generate_report_sync(
    report_id: str,
    folder_id: str,
    selected_files: List[FileSelection],
    custom_title: Optional[str]
) -> Dict:
    """동기 보고서 생성 (기본 방식)"""
    try:
        db = await get_db()
        db_ops = DatabaseOperations(db)
        
        # 폴더 정보 조회
        folder_info = await db_ops.get_folder_by_id(folder_id)
        if not folder_info:
            raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다")
        
        # 선택된 파일들의 내용 조회
        file_contents = []
        for file_sel in selected_files:
            if file_sel.selected:
                chunks = await db_ops.get_file_chunks(file_sel.file_id)
                if chunks:
                    content = " ".join([chunk["content"] for chunk in chunks])
                    file_contents.append({
                        "file_id": file_sel.file_id,
                        "filename": file_sel.filename,
                        "content": content,
                        "file_type": file_sel.file_type
                    })
        
        if not file_contents:
            raise HTTPException(status_code=400, detail="선택된 파일의 내용을 찾을 수 없습니다")
        
        # 보고서 생성
        report_generator = ReportGenerator()
        report_data = await report_generator.generate_academic_report(
            file_contents=file_contents,
            folder_title=folder_info["title"],
            custom_title=custom_title
        )
        
        # 데이터베이스에 저장
        report_document = {
            "report_id": report_id,
            "title": report_data["title"],
            "subtitle": report_data["subtitle"],
            "folder_id": folder_id,
            "selected_files": [
                {
                    "file_id": f.file_id,
                    "filename": f.filename,
                    "file_type": f.file_type
                }
                for f in selected_files if f.selected
            ],
            "report_structure": report_data["structure"],
            "analysis_summary": report_data["analysis_summary"],
            "metadata": report_data["metadata"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await db_ops.insert_one("reports", report_document)
        
        logger.info(f"보고서 생성 완료: {report_id}")
        return report_document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"보고서 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="보고서 생성 중 오류가 발생했습니다") 