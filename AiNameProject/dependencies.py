from core.mail import create_mail_instance
from fastapi_mail import FastMail
from models import  AsyncSession



async def get_mail():
    return create_mail_instance()

async def get_session():
    session = AsyncSession()
    try:
        yield session
    finally:
        await session.close()