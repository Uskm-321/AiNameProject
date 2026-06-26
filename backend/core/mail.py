from fastapi_mail import FastMail,ConnectionConfig
from pydantic import SecretStr,EmailStr
import settings

def create_mail_instance():
    mail_config = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=SecretStr(settings.MAIL_PASSWORD),
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )
    return FastMail(mail_config)