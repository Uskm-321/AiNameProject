from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio.session import AsyncSession
from starlette.responses import HTMLResponse
from starlette.responses import Response

from core.alipay_service import AlipayConfigError, AlipaySandboxClient, PAYMENT_PACKAGES
from core.auth import AuthHandler
from dependencies import get_session
from models.payment import PaymentOrder
from models.user import User
from repository.payment_repo import PaymentRepository
from schemas.payment_schemas import (
    PaymentCreateIn,
    PaymentCreateOut,
    PaymentOrderOut,
    PaymentPackageOut,
    PaymentSyncOut,
)


router = APIRouter(prefix="/payments", tags=["payments"])
auth_handler = AuthHandler()


def _order_out(order: PaymentOrder) -> PaymentOrderOut:
    qr_image_url = f"/payments/orders/{order.out_trade_no}/qr" if order.qr_code else None
    expires_at = PaymentRepository.expires_at(order)
    return PaymentOrderOut(
        id=order.id,
        out_trade_no=order.out_trade_no,
        trade_no=order.trade_no,
        package_id=order.package_id,
        api_key_id=order.api_key_id,
        subject=order.subject,
        amount=order.amount,
        quota=order.quota,
        qr_code=order.qr_code,
        qr_image_url=qr_image_url,
        status=order.status,
        created_at=order.created_at,
        expires_at=expires_at,
        paid_at=order.paid_at,
    )


@router.get("/packages", response_model=list[PaymentPackageOut])
async def list_payment_packages():
    return [
        PaymentPackageOut(id=package_id, **package_data)
        for package_id, package_data in PAYMENT_PACKAGES.items()
    ]


@router.post("/create", response_model=PaymentCreateOut)
async def create_payment_order(
    data: PaymentCreateIn,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    package_data = PAYMENT_PACKAGES.get(data.package_id)
    if not package_data:
        raise HTTPException(status_code=400, detail="套餐不存在")

    repository = PaymentRepository(session=session)
    api_key = await repository.get_api_key_for_purchase(current_user.id, data.api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key 不存在")

    subject = f"AI 智能起名 API 调用次数 - {package_data['name']}（{package_data['quota']}次）"
    order = await repository.create_order(
        user_id=current_user.id,
        api_key_id=api_key.id,
        package_id=data.package_id,
        subject=subject,
        amount=package_data["amount"],
        quota=package_data["quota"],
    )

    client = AlipaySandboxClient()
    pay_url = client.page_pay_url(order.out_trade_no, subject, order.amount)
    try:
        precreate_result = client.precreate_order(order.out_trade_no, subject, order.amount)
        order = await repository.set_order_qr_code(
            current_user.id,
            order.out_trade_no,
            precreate_result["qr_code"],
        )
    except AlipayConfigError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"支付宝二维码订单创建失败: {error}") from error

    return PaymentCreateOut(
        id=order.id,
        out_trade_no=order.out_trade_no,
        pay_url=pay_url,
        pay_form_url=f"/payments/orders/{order.out_trade_no}/pay-form",
        qr_code=order.qr_code,
        qr_image_url=f"/payments/orders/{order.out_trade_no}/qr",
        amount=order.amount,
        quota=order.quota,
        subject=order.subject,
        status=order.status,
        expires_at=PaymentRepository.expires_at(order),
    )


@router.get("/orders/{out_trade_no}/qr")
async def get_payment_qr(
    out_trade_no: str,
    session: AsyncSession = Depends(get_session),
):
    order = await PaymentRepository(session=session).get_order_by_out_trade_no(out_trade_no)
    if not order or not order.qr_code:
        raise HTTPException(status_code=404, detail="订单二维码不存在")
    if order.status != "created":
        raise HTTPException(status_code=410, detail="订单已失效，请重新生成二维码")
    png_bytes = AlipaySandboxClient.qr_png_bytes(order.qr_code)
    return Response(content=png_bytes, media_type="image/png")


@router.get("/orders/{out_trade_no}/pay-form", response_class=HTMLResponse)
async def get_payment_form(
    out_trade_no: str,
    session: AsyncSession = Depends(get_session),
):
    order = await PaymentRepository(session=session).get_order_by_out_trade_no(out_trade_no)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != "created":
        raise HTTPException(status_code=410, detail="订单已失效，请重新生成二维码")
    try:
        html = AlipaySandboxClient().page_pay_form_html(order.out_trade_no, order.subject, order.amount)
    except AlipayConfigError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    return HTMLResponse(html)


@router.get("/orders/{out_trade_no}", response_model=PaymentOrderOut)
async def get_payment_order(
    out_trade_no: str,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    order = await PaymentRepository(session=session).get_order(current_user.id, out_trade_no)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return _order_out(order)


@router.post("/orders/{out_trade_no}/sync", response_model=PaymentSyncOut)
async def sync_payment_order(
    out_trade_no: str,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = PaymentRepository(session=session)
    order = await repository.get_order(current_user.id, out_trade_no)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status == "paid":
        return PaymentSyncOut(order=_order_out(order), alipay_status="TRADE_SUCCESS", message="订单已到账")
    if order.status == "closed":
        return PaymentSyncOut(order=_order_out(order), alipay_status="TRADE_CLOSED", message="订单已超过 5 分钟，请重新生成二维码")

    try:
        query_result = AlipaySandboxClient().query_trade(out_trade_no)
    except AlipayConfigError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"支付宝订单查询失败: {error}") from error

    code = query_result.get("code")
    trade_status = query_result.get("trade_status")
    if code != "10000":
        return PaymentSyncOut(
            order=_order_out(order),
            alipay_status=trade_status,
            message=query_result.get("sub_msg") or query_result.get("msg") or "订单未支付",
        )

    if trade_status in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
        order = await repository.mark_paid_and_grant_quota(
            current_user.id,
            out_trade_no,
            query_result.get("trade_no"),
        )
        return PaymentSyncOut(order=_order_out(order), alipay_status=trade_status, message="支付成功，调用次数已到账")

    return PaymentSyncOut(order=_order_out(order), alipay_status=trade_status, message="订单尚未支付完成")


@router.post("/orders/{out_trade_no}/sandbox-complete", response_model=PaymentSyncOut)
async def sandbox_complete_payment_order(
    out_trade_no: str,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = PaymentRepository(session=session)
    order = await repository.get_order(current_user.id, out_trade_no)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status == "closed":
        return PaymentSyncOut(order=_order_out(order), alipay_status="TRADE_CLOSED", message="订单已超过 5 分钟，请重新生成二维码")
    order = await repository.mark_paid_and_grant_quota(
        current_user.id,
        out_trade_no,
        trade_no=f"SANDBOX-{out_trade_no}",
    )
    return PaymentSyncOut(order=_order_out(order), alipay_status="SANDBOX_COMPLETED", message="沙箱模拟支付成功，调用次数已到账")
