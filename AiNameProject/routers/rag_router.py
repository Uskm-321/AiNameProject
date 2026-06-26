import os
import json
import shutil
import aio_pika
from fastapi import APIRouter, UploadFile, File, Depends
from core.auth import AuthHandler
from models.user import User

auth_handler = AuthHandler()
router = APIRouter(prefix="/knowledge", tags=["知识库"])

UPLOAD_DIR = "./uploads"
# 确保上传目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

# RabbitMQ 连接配置
RABBITMQ_URL = "amqp://admin:admin123@127.0.0.1:5672/"
QUEUE_NAME = "rag_document_queue"


async def send_to_queue(message_dict: dict):
    """异步将任务发送到 RabbitMQ 队列"""
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        # 声明队列：durable=True 开启持久化，服务器重启任务不丢
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)

        # 将任务字典转为 JSON 字节流发送
        message_body = json.dumps(message_dict).encode("utf-8")
        # 调用默认交换机，把封装好的消息发布出去
        await channel.default_exchange.publish(
            aio_pika.Message(body=message_body),
            routing_key=queue.name,
        )


@router.post("/upload")
async def upload_document(
        file: UploadFile = File(...),
        current_user: User = Depends(auth_handler.auth_user_dependency)
):
    """
    用户上传专属参考文件（TXT/PDF）并投递到消息队列
    """
    user_id = current_user.id
    file_path = os.path.join(UPLOAD_DIR, f"{user_id}_{file.filename}")

    # 注意这里转换成绝对路径，方便后续异步消费者读取
    absolute_path = os.path.abspath(file_path)

    # 第一步：完成文件在服务器的保存
    with open(absolute_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 第二步：构造任务包裹并投递到 RabbitMQ
    task_message = {
        "user_id": user_id,
        "file_path": absolute_path
    }
    await send_to_queue(task_message)

    return {
        "result": "success",
        "message": f"文件 {file.filename} 上传成功！后台正在为您构建专属知识库，请稍候测试起名功能。"
    }