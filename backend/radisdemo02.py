import redis
import random


REDIS_URL = 'redis://localhost:6379/0'
redis_client = redis.from_url(REDIS_URL, decode_responses=True,encoding='utf-8')

def send_captcha(phone:str):
    code = str(random.randint(100000,999999))

    captcha_key = f"captcha_{phone}"
    redis_client.setex(captcha_key,300, code)
    print(f"[模拟发送] 手机号 {phone} 的验证码是: {code} (60秒内有效)")

    return code

def vertify_captcha(phone:str,code:str):
    captcha_key = f"captcha_{phone}"
    saved_code = redis_client.get(captcha_key)
    if not saved_code:
        print(f"[验证失败] 手机号 {phone} 的验证码已过期或不存在")
        return False
    if saved_code != code:
        print("验证码输入错误")
    else:
        redis_client.delete(captcha_key)
        print("[验证成功]")
        return True

test_phone = "123123123123"

print(vertify_captcha(test_phone,"123456"))