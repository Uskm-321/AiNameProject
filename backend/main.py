from pathlib import Path
import secrets

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_mail import FastMail, MessageSchema, MessageType
from starlette.responses import HTMLResponse
from aiosmtplib import SMTPResponseException
from sqlalchemy import inspect, select, text, update

from dependencies import get_mail
# 1. 导入路由
from routers.auth_router import router as auth_router
from routers.admin_router import router as admin_router
from routers.api_key_router import router as api_key_router
from routers.community_router import router as community_router
from routers.invitation_router import router as invitation_router
from routers.name_router import router as name_router
from routers.rag_router import router as rag_router
from routers.visual_router import router as visual_router
from models import Base, engine
from models.user import User

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
app.include_router(api_key_router)
app.include_router(community_router)
app.include_router(invitation_router)
app.include_router(name_router)
app.include_router(rag_router)
app.include_router(visual_router)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# 5. 启动事件：在这里安全地初始化数据库连接池和工作流
@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        usage_columns = await conn.run_sync(
            lambda sync_conn: {
                column["name"] for column in inspect(sync_conn).get_columns("api_key_usage")
            }
        )
        if "status" not in usage_columns:
            await conn.execute(
                text(
                    "ALTER TABLE api_key_usage "
                    "ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'success'"
                )
            )
        user_columns = await conn.run_sync(
            lambda sync_conn: {
                column["name"] for column in inspect(sync_conn).get_columns("user")
            }
        )
        if "invite_code" not in user_columns:
            await conn.execute(text("ALTER TABLE user ADD COLUMN invite_code VARCHAR(32) NULL"))
        if "invited_by_user_id" not in user_columns:
            await conn.execute(text("ALTER TABLE user ADD COLUMN invited_by_user_id INTEGER NULL"))
        if "credits" not in user_columns:
            await conn.execute(
                text("ALTER TABLE user ADD COLUMN credits INTEGER NOT NULL DEFAULT 0")
            )
        sensitive_columns = set()
        table_names = await conn.run_sync(
            lambda sync_conn: set(inspect(sync_conn).get_table_names())
        )
        if "sensitive_word_rule" in table_names:
            sensitive_columns = await conn.run_sync(
                lambda sync_conn: {
                    column["name"] for column in inspect(sync_conn).get_columns("sensitive_word_rule")
                }
            )
        if "severity" in sensitive_columns:
            await conn.execute(text("ALTER TABLE sensitive_word_rule DROP COLUMN severity"))
        users_without_code = (
            await conn.execute(
                select(User.id).where((User.invite_code.is_(None)) | (User.invite_code == ""))
            )
        ).scalars().all()
        for user_id in users_without_code:
            await conn.execute(
                update(User)
                .where(User.id == user_id)
                .values(invite_code=secrets.token_urlsafe(6))
            )
        await conn.execute(
            update(User)
            .where(User.email != "1046399289@qq.com", User.role.in_(["super_admin", "SUPER_ADMIN"]))
            .values(role="admin")
        )
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
@app.get("/", response_class=HTMLResponse)
async def root():
    login_page = Path(__file__).resolve().parent.parent / "ainame" / "login-preview.html"
    return HTMLResponse(
        login_page.read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store"},
    )

@app.get("/page/admin", response_class=HTMLResponse)
async def admin_page():
    page = Path(__file__).resolve().parent.parent / "ainame" / "admin-preview.html"
    return HTMLResponse(page.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})

@app.get("/page/index", response_class=HTMLResponse)
async def index_page():
    page = Path(__file__).resolve().parent.parent / "ainame" / "index-preview.html"
    return HTMLResponse(page.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})

@app.get("/page/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    page = STATIC_DIR / "dashboard-preview.html"
    return HTMLResponse(page.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})

@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9000)
