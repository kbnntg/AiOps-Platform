# 这个文件就是创建哈希值与Token验证
# 主要技术栈：bcrypt、jwt

"""
大致路线：
1. 定义生成hash的方法，通过盐值与password返回一个hash值
2. 定义验证hash的方法，看看新生成的hash是否与接收来的一致，
此时如果验证成功，前端就登陆成功了，然后生成一个token（通过一下方法）
3. 定义生成token的方法，基于config的settings实例的类属性进行token验证生成，之后将token返回给前端
4. 前端收到token后登陆后会将token通过HTTPBearer返回给事先定义的变量，之后通过以下验证token的方法判断
5. 验证token的方法里定义一个credentials然后将通过Depends解析的接收HTTPBearer的值。进行token验证，验证成功就返回payload的键值
6. 最后定义一个判断是否为管理员的方法，接收user的dict值，将验证token的返回值解析赋值给user，之后判断role（角色类别）是否为admin，不是就返回403错误
"""
from datetime import datetime, timedelta

# 导入模块
import bcrypt
import jwt
import fastapi
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.config import settings

# 定义接受前端发送token的值（HTTPBearer）
security = HTTPBearer()


# 创建生成hash值的函数
def create_hash(password: str) -> str:
    # 盐值
    salt = bcrypt.gensalt(rounds=12)
    # 将盐值与password混合后转换为字符串返回
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


# 创建验证hash值的函数
def verity_hash(password: str, password_hash: str) -> bool:
    # 验证值
    try:
        # 检查他俩转换是否一样
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


# 此时前端如果已经登陆成功，就要创建token给前端
# 创建生成token的函数
def create_token(username: str, role: str) -> str:
    payload = {
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_HOURS),
        'iat': datetime.utcnow(),
    }
    # 返回生成token值
    return jwt.encode(payload, settings.SECRET_KEY, settings.ALGORITHM)


# 此时已将token返回给前端，需要判断

# 创建验证token的函数
def verity_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    # token就是接收前端发送的token值（通过Depends（security））解析了
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return {"username": payload.get("username"), "role": payload.get('role', 'viewer')}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token已过期，重新登陆')
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='Token无效')


# 创建判断token角色类别方法
def verity_role(user: dict = Depends(verity_token)) -> dict:
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail='角色不是admin，权限不够')
    return user


if __name__ == '__main__':
    token = create_token('admin', 'admin')
    print(token)
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    print(decoded)
