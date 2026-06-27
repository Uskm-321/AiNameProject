import secrets
from datetime import date, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio.session import AsyncSession

from models.user import APIKey, APIKeyStatus, APIKeyUsage


class APIKeyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_key(self, user_id: int, name: str):
        async with self.session.begin():
            while True:
                raw_key = secrets.token_urlsafe(32)
                exists = await self.session.scalar(select(APIKey.id).where(APIKey.key == raw_key))
                if not exists:
                    break
            api_key = APIKey(user_id=user_id, key=raw_key, name=name)
            self.session.add(api_key)
            await self.session.flush()
            return api_key

    async def list_keys(self, user_id: int):
        async with self.session.begin():
            result = await self.session.scalars(
                select(APIKey)
                .where(APIKey.user_id == user_id, APIKey.status != APIKeyStatus.DELETED.value)
                .order_by(APIKey.id.desc())
            )
            keys = list(result)
            today = date.today()
            for api_key in keys:
                if api_key.last_used_at and api_key.last_used_at.date() != today and api_key.used_today:
                    api_key.used_today = 0
            return keys

    async def disable_key(self, user_id: int, key_id: int):
        async with self.session.begin():
            api_key = await self.session.scalar(
                select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
            )
            if not api_key:
                return None
            api_key.status = APIKeyStatus.DISABLED.value
            return api_key

    async def enable_key(self, user_id: int, key_id: int):
        async with self.session.begin():
            api_key = await self.session.scalar(
                select(APIKey).where(
                    APIKey.id == key_id,
                    APIKey.user_id == user_id,
                    APIKey.status == APIKeyStatus.DISABLED.value,
                )
            )
            if not api_key:
                return None
            api_key.status = APIKeyStatus.ACTIVE.value
            return api_key

    async def delete_key(self, user_id: int, key_id: int):
        async with self.session.begin():
            api_key = await self.session.scalar(
                select(APIKey).where(
                    APIKey.id == key_id,
                    APIKey.user_id == user_id,
                    APIKey.status != APIKeyStatus.DELETED.value,
                )
            )
            if not api_key:
                return None
            api_key.status = APIKeyStatus.DELETED.value
            return api_key

    async def get_active_key(self, raw_key: str):
        async with self.session.begin():
            api_key = await self.session.scalar(select(APIKey).where(APIKey.key == raw_key))
            if not api_key or api_key.status != APIKeyStatus.ACTIVE.value:
                return None
            return api_key

    async def consume_quota(self, api_key: APIKey, path: str, cost: int = 1):
        async with self.session.begin():
            db_key = await self.session.scalar(select(APIKey).where(APIKey.id == api_key.id))
            if not db_key or db_key.status != APIKeyStatus.ACTIVE.value:
                return None, "disabled", None

            now = datetime.now()
            if db_key.last_used_at and db_key.last_used_at.date() != now.date():
                db_key.used_today = 0

            if db_key.used_today + cost > db_key.total_quota:
                return db_key, "quota_exceeded", None

            db_key.used_today += cost
            db_key.total_used += cost
            db_key.last_used_at = now
            usage = APIKeyUsage(
                api_key_id=db_key.id,
                user_id=db_key.user_id,
                path=path,
                cost=cost,
                status="pending",
            )
            self.session.add(usage)
            await self.session.flush()
            return db_key, None, usage.id

    async def mark_usage_status(self, usage_id: int, status: str):
        await self.session.execute(
            update(APIKeyUsage).where(APIKeyUsage.id == usage_id).values(status=status)
        )
        await self.session.commit()

    async def stats(self, user_id: int):
        async with self.session.begin():
            all_keys = list(await self.session.scalars(select(APIKey).where(APIKey.user_id == user_id)))
            keys = [key for key in all_keys if key.status != APIKeyStatus.DELETED.value]
            today = datetime.now().date()
            used_today = sum(
                key.used_today
                if key.last_used_at and key.last_used_at.date() == today
                else 0
                for key in keys
            )
            remaining_today = sum(
                max(0, key.total_quota - (
                    key.used_today if key.last_used_at and key.last_used_at.date() == today else 0
                ))
                for key in keys
                if key.status == APIKeyStatus.ACTIVE.value
            )

            start_date = today - timedelta(days=6)
            rows = (
                await self.session.execute(
                    select(func.date(APIKeyUsage.created_at), func.coalesce(func.sum(APIKeyUsage.cost), 0))
                    .where(APIKeyUsage.user_id == user_id, APIKeyUsage.created_at >= datetime.combine(start_date, datetime.min.time()))
                    .group_by(func.date(APIKeyUsage.created_at))
                )
            ).all()
            usage_by_day = {str(day): int(total or 0) for day, total in rows}
            recent_7_days = [
                {"date": str(start_date + timedelta(days=index)), "used": usage_by_day.get(str(start_date + timedelta(days=index)), 0)}
                for index in range(7)
            ]
            path_rows = (
                await self.session.execute(
                    select(APIKeyUsage.path, func.coalesce(func.sum(APIKeyUsage.cost), 0))
                    .where(APIKeyUsage.user_id == user_id)
                    .group_by(APIKeyUsage.path)
                )
            ).all()
            distribution = {"NPC": 0, "小说角色": 0, "地名": 0}
            for path, total in path_rows:
                normalized = path.lower()
                if "place" in normalized or "location" in normalized:
                    label = "地名"
                elif "novel" in normalized or "character" in normalized:
                    label = "小说角色"
                else:
                    label = "NPC"
                distribution[label] += int(total or 0)
            return {
                "total_keys": len(keys),
                "used_today": used_today,
                "remaining_today": remaining_today,
                "total_used": sum(key.total_used for key in all_keys),
                "recent_7_days": recent_7_days,
                "endpoint_distribution": [
                    {"name": name, "used": used} for name, used in distribution.items()
                ],
            }

    async def list_usage(self, user_id: int, offset: int = 0, limit: int = 20):
        async with self.session.begin():
            result = await self.session.scalars(
                select(APIKeyUsage)
                .where(APIKeyUsage.user_id == user_id)
                .order_by(APIKeyUsage.id.desc())
                .offset(offset)
                .limit(limit)
            )
            total = await self.session.scalar(select(func.count(APIKeyUsage.id)).where(APIKeyUsage.user_id == user_id))
            return total or 0, list(result)
