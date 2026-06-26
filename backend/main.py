from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_mail import FastMail, MessageSchema, MessageType
from starlette.responses import HTMLResponse
from aiosmtplib import SMTPResponseException

from dependencies import get_mail
# 1. 导入路由
from routers.auth_router import router as auth_router
from routers.admin_router import router as admin_router
from routers.name_router import router as name_router
from routers.rag_router import router as rag_router
from routers.visual_router import router as visual_router

# 2. 导入工作流初始化函数 (对应最新的 workflow.py)
from core.workflow import get_naming_graph

# 3. 创建 FastAPI 实例
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. 注册路由
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(name_router)
app.include_router(rag_router)
app.include_router(visual_router)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# 5. 启动事件：在这里安全地初始化数据库连接池和工作流
@app.on_event("startup")
async def startup_event():
    # 调用我们封装好的初始化函数
    # 此时 Uvicorn 的异步事件循环已经启动，所以 AsyncConnectionPool 不会报错
    await get_naming_graph()
    print("FastAPI startup complete: workflow is ready")


# 6. 邮件测试接口
@app.get("/mail/test")
async def test(email: str, mail: FastMail = Depends(get_mail)):
    message = MessageSchema(
        subject="Hello World",
        recipients=[email],
        body=f"Hello {email}",
        subtype=MessageType.plain
    )
    try:
        await mail.send_message(message)
    except SMTPResponseException as e:
        if e.code == -1 and b"\\x00\\x00\\x00" in str(e).encode():
            print("忽略QQ邮箱和SMTP关闭阶段的非标准响应，邮箱已发送成功")

    return {"message": "邮箱发送成功"}


# 7. 基础测试接口
@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
