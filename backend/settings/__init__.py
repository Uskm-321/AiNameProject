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

JWT_ACCESS_TOKEN_EXPIRES=timedelta(days=1)
JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30)

# 邀请注册链接模板。留空则使用当前请求域名 + uni-app 注册页 hash 路由。
# 示例: "http://127.0.0.1:5173/#/pages/register/register?invite_code={invite_code}"
INVITE_REGISTER_LINK_TEMPLATE = ""