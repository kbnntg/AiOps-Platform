# 该模块用于审计日志，定义一个函数接收用户传入的操作，写入到数据库中
import json

from models.database import get_db


def record_audit(username: str, action: str, resource_type: str = None, resource_name: str = None,
                 namespace: str = None, details: dict = None, result: str = "SUCCESS") -> None:
    # 接收的用户名、操作、资源类型（pod、deployment）、资源名、命名空间、细节（可选）、执行结果
    try:
        # 奖励游标
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO operation_audit
                   (username, action, resource_type, resource_name, namespace, details, result)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (username, action, resource_type, resource_name, namespace,
                 # 需要将字典转为字符串，因为SQL里没法存储字典
                 json.dumps(details) if details else None, result)
                # if details else None：因为 json.dumps(None) 的结果是字符串 "null"，不是真正的 NULL。数据库里存字符串 "null" 和存 NULL 是两回事。
            )
            conn.close()
    except Exception as e:
        print(f'f审计日志写入失败：{e}')


# 后续接口调用就可以写入操作
