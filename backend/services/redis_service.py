# 定义Redis缓存，API等
import json
from typing import Optional, Any

import redis

from core import config


class Session:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    # 定义redis客户端
    def _init(self):
        # 连接池
        host = config.Setting.REDIS_HOST
        port = config.Setting.REDIS_PORT

        # decode_responses自动decode成字符串
        pool = redis.ConnectionPool(
            host=host, port=port, decode_responses=True, max_connections=10,
        )
        self.client = redis.Redis(connection_pool=pool)
        print(f"[Cache]Redis连接：{host}:{port}")

    # 定义获取缓存,成功就返回，没成功命中缓存就返回None
    def get(self, value: str) -> Optional[Any]:
        try:
            key = self.client.get(value)
            if key is None:
                return None
            return json.loads(key)
        except Exception as e:
            print(f'[Cache]get失败{e}')
            return None

    # 定义设置缓存，以便后期命中
    def set(self, key: str, value: str, ttl: int = 30) -> bool:
        try:
            self.client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            print(f'[Cache]set失败:{e}')
            return False

    # 定义删除缓存方法
    def delete(self, key: str) -> bool:
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f'[Cache]delete失败{e}')
            return False

    # 按照前缀删除缓存
    def delete_prefix(self, key: str) -> int:
        try:
            keys = self.client.keys(f'{key}*')
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f'[Cache]delete_prefix失败{e}')
            return 0
