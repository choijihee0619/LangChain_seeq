#!/usr/bin/env python3
"""
기존 저장된 파일 재처리 스크립트
저장된 raw_text를 기반으로 줄바꿈 보존 방식으로 재처리
CREATED 2025-01-27: 기존 데이터 줄바꿈 보존 재처리
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# 현재 파일의 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 환경변수 로드
load_dotenv()

from database.connection import get_database, init_db, close_db
from data_processing.document_processor import DocumentProcessor
from utils.logger import setup_logger, get_logger

# 로거 설정
setup_logger()
logger = get_logger(__name__)

class FileReprocessor:
    """파일 재처리 클래스"""
    
    def __init__(self):
        self.db = None
        self.processor = None
        
    async def initialize(self):
        """초기화"""
        await init_db()
        self.db = await get_database()
        self.processor = DocumentProcessor(self.db)
        logger.info("재처리 시스템 초기화 완료")
        
    async def get_all_files(self):
        """모든 파일 목록 조회"""
        try:
            # documents 컬렉션에서 파일 목록 조회
            cursor = self.db.documents.find({}, {
                "file_metadata": 1,
                "raw_text": 1,
                "created_at": 1
            })
            
            files = []
            async for doc in cursor:
                file_metadata = doc.get("file_metadata", {})
                if file_metadata and file_metadata.get("file_id"):
                    files.append({
                        "file_id": file_metadata["file_id"],
                        "filename": file_metadata.get("original_filename", "Unknown"),
                        "file_type": file_metadata.get("file_type", "unknown"),
                        "file_size": file_metadata.get("file_size", 0),
                        "folder_id": doc.get("folder_id"),
                        "has_text": bool(doc.get("raw_text")),
                        "text_length": len(doc.get("raw_text", "")),
                        "created_at": doc.get("created_at")
                    })
            
            logger.info(f"총 {len(files)}개 파일 발견")
            return files
            
        except Exception as e:
            logger.error(f"파일 목록 조회 실패: {e}")
            return []
    
    async def filter_processable_files(self, files):
        """재처리 가능한 파일 필터링"""
        processable = []
        
        for file_info in files:
            # PDF, DOCX 파일이고 텍스트가 있는 경우만
            if (file_info["file_type"].lower() in ["pdf", "docx"] and 
                file_info["has_text"] and 
                file_info["text_length"] > 50):  # 최소 50자 이상
                processable.append(file_info)
        
        logger.info(f"재처리 가능한 파일: {len(processable)}개")
        return processable
    
    async def reprocess_single_file(self, file_info):
        """개별 파일 재처리"""
        try:
            file_id = file_info["file_id"]
            filename = file_info["filename"]
            
            logger.info(f"재처리 시작: {filename} ({file_id})")
            
            # 저장된 텍스트로 재처리
            result = await self.processor.reprocess_from_raw_text(
                file_id=file_id,
                preserve_formatting=True  # 줄바꿈 보존
            )
            
            logger.info(f"재처리 완료: {filename} - 청크 {result.get('chunks_count', 0)}개")
            
            return {
                "file_id": file_id,
                "filename": filename,
                "status": "success",
                "chunks_count": result.get("chunks_count", 0),
                "text_length": result.get("text_length", 0)
            }
            
        except Exception as e:
            logger.error(f"파일 재처리 실패: {filename} ({file_id}) - {e}")
            return {
                "file_id": file_id,
                "filename": filename,
                "status": "failed",
                "error": str(e)
            }
    
    async def reprocess_all_files(self, files, batch_size=5):
        """모든 파일 일괄 재처리"""
        total_files = len(files)
        success_count = 0
        failed_count = 0
        results = []
        
        logger.info(f"총 {total_files}개 파일 재처리 시작 (배치 크기: {batch_size})")
        
        # 배치 단위로 처리
        for i in range(0, total_files, batch_size):
            batch = files[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_files + batch_size - 1) // batch_size
            
            logger.info(f"배치 {batch_num}/{total_batches} 처리 중... ({len(batch)}개 파일)")
            
            # 배치 내 파일들 병렬 처리
            tasks = [self.reprocess_single_file(file_info) for file_info in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"배치 처리 중 예외 발생: {result}")
                    failed_count += 1
                elif result["status"] == "success":
                    success_count += 1
                else:
                    failed_count += 1
                
                results.append(result)
            
            # 배치 간 잠시 대기 (서버 부하 방지)
            if i + batch_size < total_files:
                await asyncio.sleep(1)
        
        return {
            "total_files": total_files,
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results
        }
    
    async def cleanup(self):
        """정리"""
        await close_db()
        logger.info("재처리 시스템 종료")

async def main():
    """메인 실행 함수"""
    reprocessor = FileReprocessor()
    
    try:
        # 초기화
        await reprocessor.initialize()
        
        # 파일 목록 조회
        logger.info("=== 파일 목록 조회 중... ===")
        all_files = await reprocessor.get_all_files()
        
        if not all_files:
            logger.warning("처리할 파일이 없습니다.")
            return
        
        # 재처리 가능한 파일 필터링
        processable_files = await reprocessor.filter_processable_files(all_files)
        
        if not processable_files:
            logger.warning("재처리 가능한 파일이 없습니다.")
            return
        
        # 파일 정보 출력
        print("\n=== 재처리 대상 파일 목록 ===")
        for i, file_info in enumerate(processable_files):
            print(f"{i+1:3d}. {file_info['filename']:<30} "
                  f"({file_info['file_type']:>4}) "
                  f"{file_info['text_length']:>8,}자 "
                  f"[{file_info['file_id'][:8]}...]")
        
        print(f"\n총 {len(processable_files)}개 파일을 재처리합니다.")
        
        # 사용자 확인
        response = input("계속 진행하시겠습니까? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            logger.info("사용자에 의해 취소되었습니다.")
            return
        
        # 재처리 실행
        logger.info("=== 파일 재처리 시작 ===")
        start_time = datetime.now()
        
        final_result = await reprocessor.reprocess_all_files(processable_files)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # 결과 출력
        print("\n=== 재처리 결과 ===")
        print(f"총 파일: {final_result['total_files']}")
        print(f"성공: {final_result['success_count']}")
        print(f"실패: {final_result['failed_count']}")
        print(f"소요 시간: {duration.total_seconds():.1f}초")
        
        # 실패한 파일들 출력
        failed_files = [r for r in final_result['results'] if r.get('status') == 'failed']
        if failed_files:
            print(f"\n실패한 파일들:")
            for failed in failed_files:
                print(f"  - {failed['filename']}: {failed.get('error', 'Unknown error')}")
        
        logger.info("=== 재처리 완료 ===")
        
    except Exception as e:
        logger.error(f"재처리 중 오류 발생: {e}")
        raise
    finally:
        await reprocessor.cleanup()

if __name__ == "__main__":
    print("기존 파일 재처리 스크립트")
    print("저장된 raw_text를 줄바꿈 보존 방식으로 재처리합니다.")
    print("=" * 50)
    
    asyncio.run(main()) 