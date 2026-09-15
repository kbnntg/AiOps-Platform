import os
import pymysql


def load_config():
    # ========== 从环境变量读取基础配置 ==========
    CPU_MAXUSE = int(os.getenv('CPU_MAXUSE', '80'))
    MEMORY_MAXUSE = int(os.getenv('MEMORY_MAXUSE', '90'))
    DISK_MAXUSE = int(os.getenv('DISK_MAXUSE', '80'))
    INTERVAL = int(os.getenv('INTERVAL', '3'))
    ALTER_INTERVAL = int(os.getenv('ALTER_INTERVAL', '5'))
    DISK_PATH = os.getenv('DISK_PATH', '/')
    URL = os.getenv('URL')

    # ========== MySQL 连接 ==========
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql-service')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'root123456')
    MYSQL_DB = os.getenv('MYSQL_DB', 'aiops_platform')

    conn = None
    cursor = None
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
            password=MYSQL_PASSWORD, database=MYSQL_DB, charset='utf8mb4'
        )
        cursor = conn.cursor()
    except Exception as e:
        print(f"MySQL 连接失败: {e}，将跳过数据库写入。")

    return {
        'CPU_MAXUSE': CPU_MAXUSE,
        'MEMORY_MAXUSE': MEMORY_MAXUSE,
        'DISK_MAXUSE': DISK_MAXUSE,
        'INTERVAL': INTERVAL,
        'DISK_PATH': DISK_PATH,
        'ALTER_INTERVAL': ALTER_INTERVAL,
        'URL': URL,
        'conn': conn,
        'cursor': cursor,
    }
