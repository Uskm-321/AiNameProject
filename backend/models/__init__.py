from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from settings import DB_URL

engine = create_async_engine(
    DB_URL,
    echo=True,
    pool_size=10,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
)

AsyncSession = async_sessionmaker(
    bind=engine,
    autoflush=True,
    expire_on_commit=False,
)

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(column_0_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s"
        }
    )


from . import user
from . import admin
from . import community
