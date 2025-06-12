#!/usr/bin/env python3
"""
데이터베이스 상태 확인 스크립트
"""

import asyncio
import os
import sys
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

async def check_db_status():
    """데이터베이스 상태 확인"""
    try:
        uri = os.getenv('MONGODB_URI')
        if not uri:
            print("MONGODB_URI 환경변수가 설정되지 않았습니다.")
            return
        
        client = AsyncIOMotorClient(uri)
        db = client.rag_database
        
        print("=== 데이터베이스 상태 확인 ===")
        
        # documents 컬렉션 확인
        doc_count = await db.documents.count_documents({})
        print(f"documents 컬렉션 문서 수: {doc_count}")
        
        # chunks 컬렉션 확인  
        chunk_count = await db.chunks.count_documents({})
        print(f"chunks 컬렉션 문서 수: {chunk_count}")
        
        # file_info 컬렉션 확인
        file_info_count = await db.file_info.count_documents({})
        print(f"file_info 컬렉션 문서 수: {file_info_count}")
        
        # 샘플 문서 확인
        print("\n=== 샘플 문서 정보 ===")
        sample_doc = await db.documents.find_one({})
        if sample_doc:
            file_metadata = sample_doc.get("file_metadata", {})
            print(f"파일명: {file_metadata.get('original_filename', 'None')}")
            print(f"파일 ID: {file_metadata.get('file_id', 'None')}")
            print(f"raw_text 길이: {len(sample_doc.get('raw_text', ''))}")
            print(f"raw_text 처음 100자: {sample_doc.get('raw_text', '')[:100]}...")
        else:
            print("documents 컬렉션이 비어있습니다!")
        
        # 모든 파일 목록
        print("\n=== 모든 파일 목록 ===")
        cursor = db.documents.find({}, {"file_metadata": 1, "raw_text": 1})
        async for doc in cursor:
            file_metadata = doc.get("file_metadata", {})
            filename = file_metadata.get("original_filename", "Unknown")
            file_id = file_metadata.get("file_id", "None")[:8]
            text_len = len(doc.get("raw_text", ""))
            print(f"- {filename} [{file_id}...] ({text_len:,}자)")
        
        client.close()
        
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    asyncio.run(check_db_status()) 