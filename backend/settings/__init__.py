DB_URL = "mysql+aiomysql://root:123456@127.0.0.1:3306/ainame?charset=utf8mb4"



MAIL_USERNAME="854068660@qq.com"
MAIL_PASSWORD="ysfgvnlnbcbvbdaa"
MAIL_FROM="854068660@qq.com"
MAIL_PORT=587
MAIL_SERVER="smtp.qq.com"
MAIL_FROM_NAME="ainameapp"
MAIL_STARTTLS=True
MAIL_SSL_TLS=False



from datetime import timedelta
JWT_SECRET_KEY = "wrwetsgsdfrtuighj" # 自定义

INVITE_REGISTER_LINK_TEMPLATE = ""
JWT_ACCESS_TOKEN_EXPIRES=timedelta(days=1)
JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30)

ALIPAY_GATEWAY = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
ALIPAY_CONFIG_FILE = r"C:\Users\854068660\Desktop\alipay.txt"
ALIPAY_RETURN_URL = "http://localhost:5173/#/pages/dashboard/index"
