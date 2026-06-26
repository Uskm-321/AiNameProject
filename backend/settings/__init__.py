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