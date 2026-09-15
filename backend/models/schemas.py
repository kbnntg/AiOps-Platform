# 此模块用来定义模型类，以便后续接口传参方便
from pydantic import BaseModel, Field


# 定义用户登陆请求体模型
class LoginRequest(BaseModel):
    username: str
    password: str


# 定义token请求体模型
class TokenResponse(BaseModel):
    token: str
    username: str
    role: str


# 定义扩容操作请求体模型
class ScaleRequest(BaseModel):
    namespace: str
    deployment: str
    # 限制在0-100
    replicas: int = Field(..., ge=0, le=100)


# 定义告警处理请求模型
class AlertResolveRequest(BaseModel):
    alter_id: int
