import base64
import html
import json
import os
import urllib.parse
import urllib.request
from io import BytesIO
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import qrcode
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from settings import ALIPAY_CONFIG_FILE, ALIPAY_GATEWAY, ALIPAY_RETURN_URL


PAYMENT_PACKAGES = {
    "sandbox_10": {"name": "沙箱测试包", "amount": Decimal("0.01"), "quota": 10},
    "basic_100": {"name": "基础包", "amount": Decimal("9.90"), "quota": 100},
    "pro_500": {"name": "进阶包", "amount": Decimal("29.90"), "quota": 500},
}


class AlipayConfigError(RuntimeError):
    pass


def _read_key_value_file(path: str) -> dict[str, str]:
    file_path = Path(path)
    if not file_path.exists():
        return {}

    values: dict[str, str] = {}
    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip().lstrip("\ufeff")] = value.strip()
    return values


def _pem_block(raw_key: str, title: str) -> bytes:
    cleaned = raw_key.strip()
    if "BEGIN" in cleaned:
        return cleaned.encode("utf-8")
    lines = [cleaned[index:index + 64] for index in range(0, len(cleaned), 64)]
    pem = f"-----BEGIN {title}-----\n" + "\n".join(lines) + f"\n-----END {title}-----\n"
    return pem.encode("utf-8")


def _to_sign_content(params: dict[str, str]) -> str:
    filtered = {
        key: value
        for key, value in params.items()
        if value is not None and value != "" and key != "sign"
    }
    return "&".join(f"{key}={filtered[key]}" for key in sorted(filtered))


class AlipaySandboxClient:
    def __init__(self):
        file_values = _read_key_value_file(os.getenv("ALIPAY_CONFIG_FILE", ALIPAY_CONFIG_FILE))
        self.app_id = self._normalize_app_id(os.getenv("ALIPAY_APP_ID") or file_values.get("APP_ID"))
        self.private_key = os.getenv("ALIPAY_APP_PRIVATE_KEY") or file_values.get("APP_PRIVATE_KEY")
        self.public_key = os.getenv("ALIPAY_PUBLIC_KEY") or file_values.get("ALIPAY_PUBLIC_KEY")
        self.gateway = os.getenv("ALIPAY_GATEWAY", ALIPAY_GATEWAY).replace("http://", "https://", 1)
        self.return_url = os.getenv("ALIPAY_RETURN_URL", ALIPAY_RETURN_URL)

        if not self.app_id or not self.private_key:
            raise AlipayConfigError("支付宝沙箱配置缺少 APP_ID 或 APP_PRIVATE_KEY")

    @staticmethod
    def _normalize_app_id(app_id: str | None) -> str | None:
        if not app_id:
            return None
        cleaned = app_id.strip()
        if cleaned.isdigit():
            return cleaned
        digits = "".join(char for char in cleaned if char.isdigit())
        if digits:
            print(f"Alipay APP_ID contains non-digit characters, normalized to {digits}")
            return digits
        return cleaned

    def _base_params(self, method: str, biz_content: dict) -> dict[str, str]:
        return {
            "app_id": self.app_id,
            "method": method,
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "biz_content": json.dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
        }

    def _sign(self, params: dict[str, str]) -> str:
        private_key = serialization.load_pem_private_key(
            _pem_block(self.private_key, "PRIVATE KEY"),
            password=None,
        )
        signature = private_key.sign(
            _to_sign_content(params).encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def _request(self, method: str, biz_content: dict) -> dict:
        params = self._base_params(method, biz_content)
        params["sign"] = self._sign(params)
        encoded = urllib.parse.urlencode(params).encode("utf-8")
        request = urllib.request.Request(
            self.gateway,
            data=encoded,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        response_key = method.replace(".", "_") + "_response"
        return payload.get(response_key, payload)

    def precreate_order(self, out_trade_no: str, subject: str, amount: Decimal) -> dict:
        result = self._request(
            "alipay.trade.precreate",
            {
                "out_trade_no": out_trade_no,
                "total_amount": f"{amount:.2f}",
                "subject": subject,
            },
        )
        if result.get("code") != "10000" or not result.get("qr_code"):
            message = result.get("sub_msg") or result.get("msg") or "支付宝预创建订单失败"
            raise AlipayConfigError(message)
        return result

    @staticmethod
    def qr_png_bytes(qr_code: str) -> bytes:
        image = qrcode.make(qr_code)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def page_pay_params(self, out_trade_no: str, subject: str, amount: Decimal) -> dict[str, str]:
        params = self._base_params(
            "alipay.trade.page.pay",
            {
                "out_trade_no": out_trade_no,
                "product_code": "FAST_INSTANT_TRADE_PAY",
                "total_amount": f"{amount:.2f}",
                "subject": subject,
            },
        )
        params["return_url"] = self.return_url
        params["sign"] = self._sign(params)
        return params

    def page_pay_url(self, out_trade_no: str, subject: str, amount: Decimal) -> str:
        params = self.page_pay_params(out_trade_no, subject, amount)
        return f"{self.gateway}?{urllib.parse.urlencode(params)}"

    def page_pay_form_html(self, out_trade_no: str, subject: str, amount: Decimal) -> str:
        params = self.page_pay_params(out_trade_no, subject, amount)
        fields = "\n".join(
            f'<input type="hidden" name="{html.escape(key)}" value="{html.escape(str(value), quote=True)}" />'
            for key, value in params.items()
        )
        action = html.escape(self.gateway, quote=True)
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>正在跳转支付宝沙箱</title>
</head>
<body>
  <form id="alipay-submit" method="post" action="{action}">
    {fields}
  </form>
  <script>document.getElementById("alipay-submit").submit();</script>
  <noscript><button type="submit" form="alipay-submit">继续支付</button></noscript>
</body>
</html>"""

    def query_trade(self, out_trade_no: str) -> dict:
        return self._request(
            "alipay.trade.query",
            {"out_trade_no": out_trade_no},
        )
