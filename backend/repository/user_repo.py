from datetime import datetime, timedelta

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio.session import AsyncSession

from models.admin import (
    AdminActionLog,
    ModerationDecision,
    ModerationRecord,
    ReviewStatus,
    SensitiveWordRule,
)
from models.user import EmailCode, User, UserRole, UserSegment, UserStatus
from schemas.user_schemas import UserCreateSchema


class EmailCodeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, email: str, email_code: str):
        async with self.session.begin():
            email_code_obj = EmailCode(email=email, code=email_code)
            self.session.add(email_code_obj)
        return email_code_obj

    async def check_email_code(self, email: str, email_code: str):
        async with self.session.begin():
            email_code_obj = await self.session.scalar(
                select(EmailCode).where(EmailCode.email == email, EmailCode.code == email_code)
            )
            if not email_code_obj:
                return False
            if (datetime.now() - email_code_obj.created_time) > timedelta(minutes=5):
                return False
            return True


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_schema: UserCreateSchema):
        async with self.session.begin():
            user = User(**user_schema.model_dump())
            self.session.add(user)
            return user

    async def get_by_email(self, email: str):
        async with self.session.begin():
            return await self.session.scalar(select(User).where(User.email == email))

    async def get_by_id(self, user_id: int):
        async with self.session.begin():
            return await self.session.scalar(select(User).where(User.id == user_id))

    async def email_is_exist(self, email: str):
        async with self.session.begin():
            stmt = select(exists().where(User.email == email))
            return await self.session.scalar(stmt)

    async def list_users(
        self,
        offset: int = 0,
        limit: int = 20,
        keyword: str | None = None,
        user_segment: str | None = None,
        status: str | None = None,
        blacklisted: bool | None = None,
    ):
        async with self.session.begin():
            stmt = select(User)
            if keyword:
                like = f"%{keyword}%"
                stmt = stmt.where((User.email.like(like)) | (User.username.like(like)))
            if user_segment:
                stmt = stmt.where(User.user_segment == user_segment)
            if status:
                stmt = stmt.where(User.status == status)
            if blacklisted is not None:
                stmt = stmt.where(User.blacklisted.is_(blacklisted))
            stmt = stmt.order_by(User.id.desc()).offset(offset).limit(limit)
            result = await self.session.scalars(stmt)
            return list(result)

    async def count_users(
        self,
        keyword: str | None = None,
        user_segment: str | None = None,
        status: str | None = None,
        blacklisted: bool | None = None,
    ):
        async with self.session.begin():
            stmt = select(func.count(User.id))
            if keyword:
                like = f"%{keyword}%"
                stmt = stmt.where((User.email.like(like)) | (User.username.like(like)))
            if user_segment:
                stmt = stmt.where(User.user_segment == user_segment)
            if status:
                stmt = stmt.where(User.status == status)
            if blacklisted is not None:
                stmt = stmt.where(User.blacklisted.is_(blacklisted))
            return await self.session.scalar(stmt)

    async def update_user_flags(
        self,
        user_id: int,
        *,
        role: str | None = None,
        user_segment: str | None = None,
        status: str | None = None,
        ban_reason: str | None = None,
        banned_until=None,
        blacklisted: bool | None = None,
        blacklist_reason: str | None = None,
        blacklisted_at=None,
    ):
        async with self.session.begin():
            user = await self.session.scalar(select(User).where(User.id == user_id))
            if not user:
                return None
            if role is not None:
                user.role = role
            if user_segment is not None:
                user.user_segment = user_segment
            if status is not None:
                user.status = status
            if ban_reason is not None:
                user.ban_reason = ban_reason
            if banned_until is not None:
                user.banned_until = banned_until
            if blacklisted is not None:
                user.blacklisted = blacklisted
            if blacklist_reason is not None:
                user.blacklist_reason = blacklist_reason
            if blacklisted_at is not None:
                user.blacklisted_at = blacklisted_at
            return user

    async def set_ban(self, user_id: int, ban_reason: str | None = None, banned_until=None):
        async with self.session.begin():
            user = await self.session.scalar(select(User).where(User.id == user_id))
            if not user:
                return None
            user.status = UserStatus.BANNED.value
            user.ban_reason = ban_reason
            user.banned_until = banned_until
            return user

    async def unset_ban(self, user_id: int):
        async with self.session.begin():
            user = await self.session.scalar(select(User).where(User.id == user_id))
            if not user:
                return None
            user.status = UserStatus.ACTIVE.value
            user.ban_reason = None
            user.banned_until = None
            return user

    async def add_blacklist(self, user_id: int, reason: str | None = None):
        async with self.session.begin():
            user = await self.session.scalar(select(User).where(User.id == user_id))
            if not user:
                return None
            user.blacklisted = True
            user.blacklist_reason = reason
            user.blacklisted_at = datetime.now()
            return user

    async def remove_blacklist(self, user_id: int):
        async with self.session.begin():
            user = await self.session.scalar(select(User).where(User.id == user_id))
            if not user:
                return None
            user.blacklisted = False
            user.blacklist_reason = None
            user.blacklisted_at = None
            return user


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_action_log(
        self,
        admin_user_id: int,
        action: str,
        detail: str | None = None,
        target_user_id: int | None = None,
    ):
        async with self.session.begin():
            log = AdminActionLog(
                admin_user_id=admin_user_id,
                target_user_id=target_user_id,
                action=action,
                detail=detail,
            )
            self.session.add(log)
            return log

    async def list_actions(self, offset: int = 0, limit: int = 20):
        async with self.session.begin():
            stmt = select(AdminActionLog).order_by(AdminActionLog.id.desc()).offset(offset).limit(limit)
            result = await self.session.scalars(stmt)
            return list(result)

    async def count_actions(self):
        async with self.session.begin():
            return await self.session.scalar(select(func.count(AdminActionLog.id)))

    async def create_sensitive_word(
        self,
        word: str,
        reason: str | None = None,
        severity: str = "BLOCK",
        created_by: int | None = None,
    ):
        async with self.session.begin():
            rule = await self.session.scalar(select(SensitiveWordRule).where(SensitiveWordRule.word == word))
            if rule:
                rule.reason = reason
                rule.severity = severity
                rule.active = True
                rule.created_by = created_by
                return rule
            rule = SensitiveWordRule(word=word, reason=reason, severity=severity, created_by=created_by)
            self.session.add(rule)
            return rule

    async def disable_sensitive_word(self, word: str):
        async with self.session.begin():
            rule = await self.session.scalar(select(SensitiveWordRule).where(SensitiveWordRule.word == word))
            if not rule:
                return None
            rule.active = False
            return rule

    async def list_sensitive_words(self):
        async with self.session.begin():
            result = await self.session.scalars(select(SensitiveWordRule).order_by(SensitiveWordRule.id.desc()))
            return list(result)

    async def get_active_sensitive_words(self):
        async with self.session.begin():
            result = await self.session.scalars(
                select(SensitiveWordRule).where(SensitiveWordRule.active.is_(True)).order_by(SensitiveWordRule.id.desc())
            )
            return list(result)

    async def create_moderation_record(
        self,
        user_id: int,
        source: str,
        input_text: str,
        output_text: str | None,
        matched_words: str | None,
        decision: str,
        review_status: str = ReviewStatus.PENDING.value,
        review_note: str | None = None,
    ):
        async with self.session.begin():
            record = ModerationRecord(
                user_id=user_id,
                source=source,
                input_text=input_text,
                output_text=output_text,
                matched_words=matched_words,
                decision=decision,
                review_status=review_status,
                review_note=review_note,
            )
            self.session.add(record)
            return record

    async def list_moderation_records(self, offset: int = 0, limit: int = 20):
        async with self.session.begin():
            stmt = select(ModerationRecord).order_by(ModerationRecord.id.desc()).offset(offset).limit(limit)
            result = await self.session.scalars(stmt)
            return list(result)

    async def count_moderation_records(self):
        async with self.session.begin():
            return await self.session.scalar(select(func.count(ModerationRecord.id)))

    async def mark_moderation_reviewed(self, record_id: int, reviewed_by: int, note: str | None = None):
        async with self.session.begin():
            record = await self.session.scalar(select(ModerationRecord).where(ModerationRecord.id == record_id))
            if not record:
                return None
            record.review_status = ReviewStatus.REVIEWED.value
            record.reviewed_by = reviewed_by
            record.review_note = note
            record.reviewed_at = datetime.now()
            return record
