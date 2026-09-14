# 该模块用于创建数据库连接池，并且定义一个用户查询方法，接收其他模块传递来的参数
from typing import Optional

import pymysql

from core.config import settings


# 获取连接池
def get_db():
    return pymysql.connect(
        host=settings.MYSQL_HOST,
        password=settings.MYSQL_PASSWORD,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        database=settings.MYSQL_DB,
        charset="utf8mb4",
        # 将元组解析为键值
        cursorclass=pymysql.cursors.DictCursor,
        # 自动提交
        autocommit=True,
    )


# 创建验证用户的函数
def get_user_name(username: str) -> Optional[dict]:
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("select * from users where username = %s", (username,))
            return cursor.fetchone()
    finally:
        conn.close()
