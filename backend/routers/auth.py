# 这个是认证路由，前端发起认证的请求都会到这个文件来
from fastapi import APIRouter, HTTPException, Depends

from core.security import verity_hash, create_token, verity_token
from models.database import get_user_name
from models.schemas import TokenResponse, LoginRequest

# 先创建个路由,prefix为前缀，后续调用router时会自动加上定义的前缀，tags就是给个标签，后续好在网页划分
router = APIRouter(prefix='/api/auth', tags=['Auth'])


# 创建接收前端登陆的请求体
@router.post('/login', response_model=TokenResponse)  # 可以把response_model=TokenResponse理解为，后端返回的数据约束为这个模型类的固定字段
# 创建登陆方法，接收到前端发送的登录信息
def login(req: LoginRequest):  # 模型类在schemas中定义的，里面有username、password，接收的前端发来的username和password

    # 将接收到的请求体的username传入到database的get_user_name中，进行用户查询，将查询的值赋值给user
    user = get_user_name(req.username)
    # 如果找到 {"id": 1, "username": "admin", "password_hash": "$2b$12$...", "role": "admin"}

    # 判断user是否存在，密码是否正确
    if not user or not verity_hash(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail='用户或密码错误')

    # 将user的用户名和角色传递到创建token的函数中，返回值给token
    token = create_token(user["username"], user["role"])

    # 返回token、username、role给前端
    return TokenResponse(token=token, username=user["username"], role=user['role'])


# 创建验证自己信息的函数
@router.get('/me')
# Depends提取verity_token的返回值，前端请求后把token发送给验证token函数，之后验证token函数再经过一系列处理返回的值给user
def get_me(user: dict = Depends(verity_token)):
    return user


"""
登录流程：
前端 POST /api/auth/login
Body: {"username": "admin", "password": "admin123"}
        ↓
FastAPI 解析请求体为 LoginRequest 对象
        ↓
get_user_by_username("admin") 查数据库
        ↓ 找到用户
verify_password("admin123", "$2b$12$...") 验证密码
        ↓ 密码正确
create_token("admin", "admin") 生成 token
        ↓
返回 TokenResponse {token, username, role}
        ↓
前端保存 token，后续请求带着它→正是在get_me中需要调用



==========================================================
获取当前用户流程：
前端 GET /api/auth/me
Header: Authorization: Bearer eyJ...
        ↓
HTTPBearer 提取 token
        ↓
jwt.decode 验证 token
        ↓ 有效
返回 {"username": "admin", "role": "admin"}
"""
