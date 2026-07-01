import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from models.payment import PaymentOrder, PaymentStatus
from models.user import APIKey, APIKeyStatus

PAYMENT_EXPIRE_MINUTES = 5


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_api_key_for_purchase(self, user_id: int, api_key_id: int):
        async with self.session.begin():
            return await self.session.scalar(
                select(APIKey).where(
                    APIKey.id == api_key_id,
                    APIKey.user_id == user_id,
                    APIKey.status != APIKeyStatus.DELETED.value,
                )
            )

    async def create_order(self, user_id: int, api_key_id: int, package_id: str, subject: str, amount, quota: int):
        async with self.session.begin():
            out_trade_no = f"AINAME{datetime.now():%Y%m%d%H%M%S}{secrets.token_hex(4).upper()}"
            order = PaymentOrder(
                user_id=user_id,
                api_key_id=api_key_id,
                out_trade_no=out_trade_no,
                package_id=package_id,
                subject=subject,
                amount=amount,
                quota=quota,
            )
            self.session.add(order)
            await self.session.flush()
            return order

    @staticmethod
    def expires_at(order: PaymentOrder):
        return order.created_at + timedelta(minutes=PAYMENT_EXPIRE_MINUTES)

    @staticmethod
    def is_expired(order: PaymentOrder):
        return (
            order.status == PaymentStatus.CREATED.value
            and datetime.now() >= PaymentRepository.expires_at(order)
        )

    def close_if_expired(self, order: PaymentOrder | None):
        if order and self.is_expired(order):
            order.status = PaymentStatus.CLOSED.value
        return order

    async def get_order(self, user_id: int, out_trade_no: str):
        async with self.session.begin():
            order = await self.session.scalar(
                select(PaymentOrder).where(
                    PaymentOrder.user_id == user_id,
                    PaymentOrder.out_trade_no == out_trade_no,
                )
            )
            return self.close_if_expired(order)

    async def get_order_by_out_trade_no(self, out_trade_no: str):
        async with self.session.begin():
            order = await self.session.scalar(
                select(PaymentOrder).where(PaymentOrder.out_trade_no == out_trade_no)
            )
            return self.close_if_expired(order)

    async def set_order_qr_code(self, user_id: int, out_trade_no: str, qr_code: str):
        async with self.session.begin():
            order = await self.session.scalar(
                select(PaymentOrder).where(
                    PaymentOrder.user_id == user_id,
                    PaymentOrder.out_trade_no == out_trade_no,
                )
            )
            if not order:
                return None
            order = self.close_if_expired(order)
            if order.status != PaymentStatus.CREATED.value:
                return order
            order.qr_code = qr_code
            return order

    async def mark_paid_and_grant_quota(self, user_id: int, out_trade_no: str, trade_no: str | None = None):
        async with self.session.begin():
            order = await self.session.scalar(
                select(PaymentOrder).where(
                    PaymentOrder.user_id == user_id,
                    PaymentOrder.out_trade_no == out_trade_no,
                )
            )
            if not order:
                return None

            if order.status == PaymentStatus.PAID.value:
                return order
            if self.is_expired(order):
                order.status = PaymentStatus.CLOSED.value
                return order

            api_key = await self.session.scalar(
                select(APIKey).where(
                    APIKey.id == order.api_key_id,
                    APIKey.user_id == user_id,
                    APIKey.status != APIKeyStatus.DELETED.value,
                )
            )
            if not api_key:
                order.status = PaymentStatus.FAILED.value
                return order

            api_key.total_quota += order.quota
            order.status = PaymentStatus.PAID.value
            order.trade_no = trade_no
            order.paid_at = datetime.now()
            return order
