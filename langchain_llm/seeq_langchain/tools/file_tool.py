"""
File Tool
파일 관리를 위한 LangChain Tool
"""
import json
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_core.tools import Tool

from utils.logger import get_logger

logger = get_logger(__name__)

class FileTool:
    """파일 관리 도구"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def _manage_files(self, action: str, folder_id: Optional[str] = None,
                          file_id: Optional[str] = None) -> str:
        """파일 관리 작업"""
        try:
            if action == "list_folders":
                # 폴더 목록 조회
                folders = await self.db.folders.find().to_list(length=100)
                return json.dumps({
                    "status": "success",
                    "action": "list_folders",
                    "folders": [{
                        "folder_id": str(folder["_id"]),
                        "name": folder.get("name", ""),
                        "file_count": folder.get("file_count", 0)
                    } for folder in folders]
                }, ensure_ascii=False)
            
            elif action == "list_files" and folder_id:
                # 특정 폴더의 파일 목록 조회
                files = await self.db.documents.find(
                    {"folder_id": folder_id}
                ).to_list(length=100)
                
                return json.dumps({
                    "status": "success", 
                    "action": "list_files",
                    "folder_id": folder_id,
                    "files": [{
                        "file_id": str(file["_id"]),
                        "filename": file.get("original_filename", ""),
                        "file_type": file.get("file_type", ""),
                        "upload_date": file.get("upload_date", "").isoformat() if file.get("upload_date") else ""
                    } for file in files]
                }, ensure_ascii=False)
            
            elif action == "file_info" and file_id:
                # 파일 정보 조회
                file_doc = await self.db.documents.find_one({"_id": file_id})
                if not file_doc:
                    return json.dumps({
                        "status": "error",
                        "message": "파일을 찾을 수 없습니다."
                    }, ensure_ascii=False)
                
                return json.dumps({
                    "status": "success",
                    "action": "file_info",
                    "file": {
                        "file_id": str(file_doc["_id"]),
                        "filename": file_doc.get("original_filename", ""),
                        "file_type": file_doc.get("file_type", ""),
                        "file_size": file_doc.get("file_size", 0),
                        "upload_date": file_doc.get("upload_date", "").isoformat() if file_doc.get("upload_date") else "",
                        "summary": file_doc.get("summary", "")
                    }
                }, ensure_ascii=False)
            
            else:
                return json.dumps({
                    "status": "error",
                    "message": "지원하지 않는 작업입니다."
                }, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"파일 관리 실패: {e}")
            return json.dumps({
                "status": "error",
                "message": f"파일 관리 중 오류가 발생했습니다: {str(e)}"
            }, ensure_ascii=False)
    
    async def create_tool(self) -> Tool:
        """LangChain Tool 생성"""
        
        async def file_wrapper(action: str, folder_id: str = None, file_id: str = None) -> str:
            return await self._manage_files(
                action=action,
                folder_id=folder_id if folder_id and folder_id.strip() else None,
                file_id=file_id if file_id and file_id.strip() else None
            )
        
        tool = Tool(
            name="file_management",
            description="""파일과 폴더를 관리하는 도구입니다.
사용법: file_management(action="작업명", folder_id=None, file_id=None)
- action: 수행할 작업 ("list_folders", "list_files", "file_info")
- folder_id: 폴더 ID (list_files 작업 시 필요)
- file_id: 파일 ID (file_info 작업 시 필요)

예시:
- file_management(action="list_folders")
- file_management(action="list_files", folder_id="folder123")
- file_management(action="file_info", file_id="file456")""",
            func=file_wrapper,
            return_direct=False
        )
        
        return tool 