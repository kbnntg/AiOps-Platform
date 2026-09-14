# 这个文件主要是创建一个类，类里创建类属性用来存储验证信息（如MySQL_HOST、MySQL_PASSWORD、与secret_key等等参数）
# 后面通过一个实例将该类进行调用

import os


# 创建一个类
class Setting:
    # Secret_key，getenv('环境变量定义的', '默认的')
    SECRET_KEY = os.getenv('SECRET_KEY', 'tgismymaster1')
    ALGORITHM = "HS256"
    ACCESS_TOKEN_HOURS = int(os.getenv('TOKEN_EXPIER_HOURS', '8'))  # 默认8

    # MySQL的一些验证信息
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql-service')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'root123456')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_DB = os.getenv("MYSQL_DB", "aiops_platform")

    # Prometheus的
    PROMETHEUS_URL = os.getenv(
        "PROMETHEUS_URL",
        "http://prometheus:9090"
    )


settings = Setting()
