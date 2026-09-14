# AIOps 智能运维平台
基于 Kubernetes 的云原生智能运维平台，集节点监控、AI 智能分析、Pod 生命周期管理、告警历史追溯、操作审计于一体。
📖 项目简介
本项目从最初的一个单机 Python 监控脚本演进而来，逐步完成了容器化 → K8s 部署 → Web 平台化 → AI 智能化的完整升级。

平台通过 DaemonSet 在每个节点采集系统指标，使用 FastAPI 提供后端 API，Vue3 构建可视化管理界面，集成 Prometheus 实现时序监控，并引入 DeepSeek 大模型实现告警根因分析和日志智能分析两大 AI 能力。

✨ 功能特性
一、节点监控与告警
多维度指标采集：CPU、内存、磁盘、磁盘 I/O、网络流量

DaemonSet 部署：每个节点精准采集，挂载宿主机 /proc、/sys

Prometheus 集成：暴露标准指标端点，自动发现抓取

阈值告警：支持自定义阈值和冷却时间，避免告警风暴

Webhook 通知：告警通过企业微信/钉钉/飞书推送

二、AI 智能分析
告警根因分析：触发告警时自动调用大模型，结合历史数据生成根因推断和排查建议

日志智能分析：点击按钮即可让 AI 分析 Pod 日志，输出问题摘要、可能原因、排查步骤

三、Kubernetes 资源管理
Pod 管理：列表查询、实时日志、事件查看、删除重建

Deployment 管理：副本扩缩容、滚动重启

命名空间与节点：集群资源总览

四、实时日志流
WebSocket 推送：日志实时追加，无需手动刷新

自动滚动：智能识别用户滚动位置，不打扰查看历史日志

日志导出：一键下载为 .log 文件

五、安全与审计
JWT 认证：Token 有效期管理

RBAC 权限分级：管理员/只读用户

操作审计：所有变更操作记录数据库，可追溯

六、监控可视化
Dashboard 总览：节点状态卡片 + 实时趋势图

告警历史：告警记录 + AI 建议 + 状态管理

ECharts 图表：CPU/内存趋势曲线

🏗️ 系统架构
text
┌──────────────────────────────────────────────────────┐
│                    用户浏览器                         │
│          Vue3 + TypeScript + Element Plus             │
└────────────────────────┬─────────────────────────────┘
                         │ HTTP / WebSocket
┌────────────────────────▼─────────────────────────────┐
│                  Nginx（前端容器）                     │
│              /api/* 反向代理 + WebSocket               │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────┐
│              后端（FastAPI + Uvicorn）                │
│  ┌──────────┬──────────┬──────────┬──────────────┐   │
│  │ JWT 认证  │ K8s API  │ Prom API │  AI 分析服务  │   │
│  └──────────┴──────────┴──────────┴──────────────┘   │
└────┬────────────┬────────────┬────────────┬──────────┘
     │            │            │            │
┌────▼────┐  ┌───▼────┐  ┌────▼─────┐  ┌───▼────────┐
│  MySQL  │  │ K8s    │  │Prometheus│  │ DeepSeek   │
│  存储   │  │ API    │  │  TSDB    │  │   大模型    │
└────▲────┘  └────────┘  └────▲─────┘  └────────────┘
     │                        │
┌────┴────────────────────────┴─────────────────────┐
│         采集器 DaemonSet（每节点一个）              │
│  采集指标 → 暴露 :8000/metrics → AI 告警 → 写 MySQL │
└───────────────────────────────────────────────────┘
🛠️ 技术栈
层次	技术
采集器	Python 3.9、psutil、prometheus_client、requests、pymysql
后端	FastAPI、Kubernetes Python Client、PyJWT、bcrypt、Pydantic
前端	Vue3、TypeScript、Element Plus、ECharts、Pinia、Vue Router
存储	MySQL 8.0、Prometheus TSDB
部署	Docker、Kubernetes（DaemonSet/Deployment/Service/RBAC）
AI	DeepSeek API（OpenAI 兼容接口）
认证	JWT、HTTPBearer、RBAC
📁 项目结构
text
aiops-platform/
├── collector/                       # 采集器（DaemonSet）
│   ├── monitor.py                   # 主采集循环
│   ├── Prometheus_config.py         # 指标暴露
│   ├── AI.py                        # AI 告警分析
│   ├── alter.py                     # Webhook 告警
│   ├── history.py                   # 历史查询
│   ├── mysql_config.py              # MySQL 写入
│   ├── load_config.py               # 配置加载
│   ├── logger.py                    # 日志输出
│   ├── requirements.txt
│   └── Dockerfile
│
├── backend/                         # Web 后端
│   ├── main.py                      # FastAPI 入口 + WebSocket
│   ├── core/
│   │   ├── config.py                # 全局配置
│   │   └── security.py              # JWT + bcrypt
│   ├── models/
│   │   ├── database.py              # 数据库连接
│   │   └── schemas.py               # Pydantic 模型
│   ├── services/
│   │   ├── k8s_service.py           # K8s API 封装
│   │   ├── prometheus_service.py    # Prometheus 查询
│   │   ├── alert_service.py         # 告警管理
│   │   ├── audit_service.py         # 审计记录
│   │   └── ai_log_service.py        # AI 日志分析
│   ├── routers/
│   │   ├── auth.py                  # 认证路由
│   │   ├── pods.py                  # Pod 路由
│   │   ├── deployments.py           # 副本路由
│   │   ├── metrics.py               # 监控路由
│   │   ├── alerts.py                # 告警路由
│   │   └── audit.py                 # 审计路由
│   ├── requirements.txt
│   └── Dockerfile.backend
│
├── frontend/                        # Web 前端
│   ├── src/
│   │   ├── api/                     # API 请求封装
│   │   ├── views/                   # 6 个核心页面
│   │   ├── components/              # 组件（图表、日志查看器）
│   │   ├── layout/                  # 主布局
│   │   ├── router/                  # 路由
│   │   └── stores/                  # Pinia 状态管理
│   ├── package.json
│   ├── vite.config.ts
│   ├── nginx.conf
│   └── Dockerfile
│
└── k8s/                             # K8s 部署清单
    ├── mysql.yaml
    ├── collector-daemonset.yaml
    ├── rbac.yaml
    ├── backend.yaml
    ├── frontend.yaml
    └── prometheus/
        ├── prometheus-rbac.yaml
        ├── prometheus-config.yaml
        └── prometheus.yaml
🚀 快速开始
前置条件
Kubernetes 集群（v1.20+）

Docker

镜像仓库（Harbor 或 Docker Hub）

DeepSeek API Key（可选，用于 AI 功能）

部署步骤
1. 创建命名空间和 Secret
bash
kubectl create namespace privatization

kubectl create secret generic aiops-secret \
  -n privatization \
  --from-literal=mysql-password='root123456' \
  --from-literal=jwt-secret="$(openssl rand -hex 32)" \
  --from-literal=webhook-url='' \
  --from-literal=api-key='sk-你的DeepSeekKey'
2. 部署 MySQL
bash
kubectl apply -f k8s/mysql.yaml
kubectl -n privatization get pods -l app=aiops-mysql -w
3. 构建并部署采集器
bash
cd collector
docker build -t aiops-collector:v1 .
cd ..

kubectl apply -f k8s/collector-daemonset.yaml
4. 构建并部署后端
bash
cd backend
docker build -t aiops-backend:v1 -f Dockerfile.backend .
cd ..

kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/backend.yaml
5. 构建并部署前端
bash
cd frontend
docker build -t aiops-frontend:v1 .
cd ..

kubectl apply -f k8s/frontend.yaml
6. 部署 Prometheus（可选）
bash
kubectl apply -f k8s/prometheus/
7. 获取访问地址
bash
kubectl -n privatization get svc
默认账号：admin / admin123

📸 项目截图
登录页
https://docs/images/login.png

深紫渐变背景 + 粒子动画 + 玻璃拟态卡片

Dashboard
https://docs/images/dashboard.png

节点状态卡片 + CPU/内存趋势图

Pod 管理
https://docs/images/pods.png

Pod 列表 + 日志/事件/删除操作

实时日志 + AI 分析
https://docs/images/ai-analysis.png

WebSocket 实时日志 + AI 分析结果

告警历史
https://docs/images/alerts.png

告警记录 + AI 建议

审计日志
https://docs/images/audit.png

所有变更操作留痕

🔑 环境变量说明
采集器
变量	说明	默认值
CPU_MAXUSE	CPU 告警阈值	80
MEMORY_MAXUSE	内存告警阈值	90
DISK_MAXUSE	磁盘告警阈值	80
INTERVAL	采集间隔（秒）	3
ALTER_INTERVAL	告警冷却时间（秒）	5
MYSQL_HOST	MySQL 地址	mysql-service
API_KEY	DeepSeek API Key	-
URL	Webhook 地址	-
后端
变量	说明
SECRET_KEY	JWT 签名密钥
MYSQL_*	MySQL 连接信息
PROMETHEUS_URL	Prometheus 地址
API_KEY	DeepSeek API Key
API_URL	DeepSeek API 地址
LOG_MODEL_NAME	日志分析用的模型
💡 技术难点与解决方案
项目在开发过程中遇到了大量生产级问题，以下是典型案例：

1. 容器内采集宿主机指标
问题：容器有独立的命名空间，psutil 读到的不是宿主机数据。

解决：DaemonSet 挂载宿主机 /proc、/sys 到容器内，配合 privileged 权限。

2. Pod 无法访问外网
问题：采集器调用 DeepSeek 和企业微信 API 超时。

排查过程：

检查 Flannel 的 EnableSNAT（默认未开启）

检查 MTU（VXLAN 封装后有效 MTU 不足）

检查 DNS 解析（CDN 返回的 IP 部分不可达）

解决：

Flannel 配置 EnableSNAT: true

设置 MTU 为 1400

使用 hostAliases 固定可达的 CDN IP

3. WebSocket 阻塞事件循环
问题：打开日志后，后端 Pod 变成 0/1，readiness probe 超时。

根因：K8s Python Client 的 follow=True 是同步阻塞调用，占住了 FastAPI 的事件循环。

解决：把同步调用放到线程池执行（run_in_executor），改为每 2 秒轮询日志，对比差异推送。

4. Python 依赖版本冲突
问题：openai==1.30.0 与新版 httpx 不兼容，报 Client.__init__() got an unexpected keyword argument 'proxies'。

解决：升级 openai>=1.55.0 并显式声明 httpx>=0.27.0。

5. admin 密码哈希验证失败
问题：初始 SQL 里的 bcrypt 哈希是示例值，不对应 admin123。

解决：在容器内生成真实哈希并更新数据库；同时更新 mysql.yaml 的 ConfigMap 供以后重装使用。

📊 项目数据
指标	数值
代码文件	70+
后端接口	17
前端页面	6
K8s 资源	DaemonSet × 1、Deployment × 4、Service × 4、RBAC × 3
支持的 AI 能力	2 类（告警分析、日志分析）
🎯 后续规划
□ 告警聚合与根因定位（多告警归并）
□ 滑动窗口告警（替代固定阈值）
□ 告警规则在线配置（Web 界面）
□ 资源 YAML 在线查看与编辑
□ 多集群管理
□ Grafana 集成
📄 License
MIT License

🙏 致谢
psutil

FastAPI

Kubernetes Python Client

Vue3

Element Plus

Prometheus

DeepSeek

⭐ 如果这个项目对你有帮助，欢迎 star！
