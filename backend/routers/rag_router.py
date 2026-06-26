import os
import shutil
from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.concurrency import run_in_threadpool
from core.auth import AuthHandler
from core.rag_service import process_and_store_file
from models.user import User

auth_handler = AuthHandler()
router = APIRouter(prefix="/knowledge", tags=["知识库"])

UPLOAD_DIR = "./uploads"
# 确保上传目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(
        file: UploadFile = File(...),
        current_user: User = Depends(auth_handler.auth_user_dependency)
):
    """
    用户上传专属参考文件（TXT/PDF）并直接构建个人知识库。
    """
    user_id = current_user.id
    file_path = os.path.join(UPLOAD_DIR, f"{user_id}_{file.filename}")

    # 注意这里转换成绝对路径，方便后续异步消费者读取
    absolute_path = os.path.abspath(file_path)

    # 第一步：完成文件在服务器的保存
    with open(absolute_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 第二步：直接构建知识库，避免本地开发必须额外启动 RabbitMQ 消费者。
    result = await run_in_threadpool(process_and_store_file, absolute_path, user_id)

    return {
        "result": "success",
        "message": f"文件 {file.filename} 上传成功！已写入专属知识库。",
        "chunks": result.get("chunks", 0),
        "storage": result.get("storage", "unknown"),
    }
