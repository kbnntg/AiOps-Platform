# AIOps 智能运维平台

基于 Kubernetes 的云原生智能运维平台，集 **节点监控、SRE 级告警治理、服务拓扑、AI Copilot、智能诊断、操作审计** 于一体。

> 从单机 Python 脚本演进而来，完成 **容器化 → K8s 部署 → Web 平台化 → AI 智能化 → Agent 化** 的完整升级。

------

## 🌟 核心亮点

### 一、SRE 级告警治理

从固定阈值逐步演进到完整的告警治理链路：

```
原始采集 → 滑动窗口 → 告警聚合 → AI 根因分析 → 一条聚合告警
```



| 层级         | 方案                               | 解决的问题     |
| :----------- | :--------------------------------- | :------------- |
| **滑动窗口** | 10 个采样点中超标占比 ≥ 70% 才告警 | 过滤抖动误报   |
| **冷却机制** | 告警后进入 60 秒冷却期             | 避免连续告警   |
| **告警聚合** | 5 分钟窗口内的告警合并分析         | 减少告警数量   |
| **AI 根因**  | 批量告警交给大模型推断共同根因     | 关联分析       |
| **量化指标** | 压缩率、误报率、MTTA、MTTR         | 治理效果可衡量 |

### 二、五层 AI 能力

| 层级  | 能力                    | 说明                                                         |
| :---- | :---------------------- | :----------------------------------------------------------- |
| **1** | AI 告警分析             | 告警触发时自动调用大模型，结合历史数据生成根因推断           |
| **2** | AI 日志分析             | 一键分析 Pod 日志，输出问题摘要、可能原因、排查步骤          |
| **3** | 多信号融合诊断          | 聚合 Prometheus 指标 + Pod 日志 + K8s 事件 + 历史告警，AI 交叉验证 |
| **4** | 告警聚合根因            | 5 分钟窗口内多条告警批量分析，生成一条根因告警               |
| **5** | **AI Copilot（Agent）** | 基于 Function Calling，AI 自主调用 10 个工具查询集群，SSE 流式输出，标注数据来源 |

**AI Copilot 是核心差异化功能。** 它不是"调 API 生成文本"，而是能**主动调用工具**：

```
用户：nginx 这个 Deployment 有几个副本？
  ↓
AI：我需要调用 list_deployments
  ↓
后端：执行工具，拿到真实数据
  ↓
AI：nginx 有 2 个副本，均已就绪 [来源: list_deployments]
```



### 三、服务拓扑图

通过 K8s 的 `OwnerReference` 和 `Label Selector` 自动推导资源关系：

```
Ingress → Service → Pod ← ReplicaSet ← Deployment
```



前端用 ECharts Graph 力导向布局渲染，节点颜色表示健康度，点击查看详情。

------

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────┐
│                    用户浏览器                         │
│          Vue3 + TypeScript + Element Plus             │
│      Dashboard / 拓扑图 / Copilot / Pod管理 / ...      │
└────────────────────────┬─────────────────────────────┘
                         │ HTTP / SSE / WebSocket
┌────────────────────────▼─────────────────────────────┐
│                  Nginx（前端容器）                     │
│         /api/* 反向代理 + SSE 透传 + WebSocket         │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────┐
│              后端（FastAPI + Uvicorn）                │
│  ┌────────┬────────┬────────┬────────┬────────────┐  │
│  │ JWT认证 │ K8s API│ Prom API│拓扑推导 │ AI Copilot │  │
│  └────────┴────────┴────────┴────────┴────────────┘  │
└────┬────────────┬────────────┬────────────┬──────────┘
     │            │            │            │
┌────▼────┐  ┌───▼────┐  ┌────▼─────┐  ┌───▼────────┐
│  MySQL  │  │ K8s    │  │Prometheus│  │ DeepSeek   │
│  存储   │  │ API    │  │  TSDB    │  │   大模型    │
└────▲────┘  └────────┘  └────▲─────┘  └────────────┘
     │                        │
┌────┴────────────────────────┴─────────────────────┐
│         采集器 DaemonSet（每节点一个）              │
│  采集指标 → 滑动窗口 → 告警聚合 → AI 分析          │
│  暴露 :8000/metrics → Prometheus 抓取              │
└───────────────────────────────────────────────────┘
```



------

## ✨ 功能特性

### 一、节点监控与告警治理

- 多维度采集：CPU、内存、磁盘、磁盘 I/O、网络流量
- DaemonSet 部署，挂载宿主机 `/proc`、`/sys`
- 滑动窗口告警（过滤抖动）
- 告警聚合（窗口内合并）
- Webhook 通知（企业微信/钉钉/飞书）

### 二、AI 智能分析（5 层）

- AI 告警分析
- AI 日志分析
- 多信号融合诊断
- 告警聚合根因
- AI Copilot（Agent）

### 三、服务拓扑图

- K8s 资源关系自动推导
- ECharts Graph 力导向布局
- 健康度可视化
- 点击节点查看详情

### 四、Kubernetes 资源管理

- Pod 管理：列表、实时日志、事件、删除
- Deployment 管理：副本扩缩容
- 命名空间与节点总览

### 五、实时日志流

- WebSocket 推送，无需手动刷新
- 智能滚动（不打扰查看历史）
- 一键导出 `.log`

### 六、安全与审计

- JWT 认证 + RBAC 权限分级
- 操作审计（所有变更留痕）

### 七、监控可视化

- Dashboard 总览（4 个量化指标 + 节点卡片 + 趋势图）
- 告警历史（AI 建议 + 状态管理）
- ECharts 图表

------

## 🛠️ 技术栈

| 层次         | 技术                                                         |
| :----------- | :----------------------------------------------------------- |
| **采集器**   | Python 3.9、psutil、prometheus_client、pymysql               |
| **后端**     | FastAPI、Kubernetes Python Client、PyJWT、bcrypt、Pydantic、OpenAI SDK |
| **前端**     | Vue3、TypeScript、Element Plus、ECharts、Pinia、Vue Router   |
| **存储**     | MySQL 8.0、Prometheus TSDB                                   |
| **部署**     | Docker、Kubernetes（DaemonSet/Deployment/Service/RBAC）      |
| **AI**       | DeepSeek API（Function Calling / SSE）                       |
| **通信**     | HTTP、SSE、WebSocket                                         |
| **告警治理** | 滑动窗口、冷却机制、告警聚合、量化指标                       |

------

## 📁 项目结构

```properties
aiops-platform/
│
├── backend/                              # Web 后端（FastAPI）
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                     # 全局配置
│   │   └── security.py                   # JWT + bcrypt
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py                   # 数据库连接
│   │   └── schemas.py                    # Pydantic 模型
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                       # 认证路由
│   │   ├── pods.py                       # Pod 管理 + AI 诊断
│   │   ├── deployments.py                # 副本管理
│   │   ├── metrics.py                    # 监控查询
│   │   ├── alerts.py                     # 告警 + 量化指标
│   │   ├── audit.py                      # 审计日志
│   │   ├── topology.py                   # 服务拓扑
│   │   └── copilot.py                    # AI Copilot（SSE）
│   ├── services/
│   │   ├── __init__.py
│   │   ├── k8s_service.py                # K8s API 封装
│   │   ├── prometheus_service.py         # Prometheus 查询
│   │   ├── topology_service.py           # 拓扑推导
│   │   ├── alert_service.py              # 告警管理
│   │   ├── audit_service.py              # 审计记录
│   │   ├── ai_log_service.py             # AI 日志分析
│   │   ├── ai_diagnose_service.py        # 多信号融合诊断
│   │   ├── copilot_tools.py              # Copilot 工具定义
│   │   └── copilot_service.py            # Copilot Function Calling
│   ├── Dockerfile.backend
│   ├── main.py                           # FastAPI 入口 + WebSocket
│   └── requirements.txt
│
├── collector/                            # 采集器（DaemonSet）
│   ├── monitor.py                        # 主采集循环 + 滑动窗口告警
│   ├── aggregation.py                    # 告警聚合器
│   ├── Prometheus_config.py              # 指标暴露
│   ├── AI.py                             # AI 告警 + 聚合分析
│   ├── alter.py                          # Webhook 告警
│   ├── history.py                        # 历史查询
│   ├── mysql_config.py                   # MySQL 写入
│   ├── load_config.py                    # 配置加载
│   ├── logger.py                         # 日志输出
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                             # Web 前端（Vue3）
│   ├── src/
│   │   ├── api/
│   │   │   ├── request.ts                # Axios 封装
│   │   │   ├── auth.ts
│   │   │   ├── pods.ts
│   │   │   ├── deployments.ts
│   │   │   ├── metrics.ts
│   │   │   ├── alerts.ts
│   │   │   ├── topology.ts
│   │   │   └── copilot.ts                # SSE 流式请求
│   │   ├── components/
│   │   │   ├── AppBackground.vue
│   │   │   ├── AppearanceSetting.vue
│   │   │   ├── LogViewer.vue
│   │   │   └── ResourceChart.vue
│   │   ├── config/
│   │   │   └── appearance.ts
│   │   ├── layout/
│   │   │   └── MainLayout.vue
│   │   ├── router/
│   │   │   └── index.ts
│   │   ├── stores/
│   │   │   ├── appearance.ts
│   │   │   └── auth.ts
│   │   ├── styles/
│   │   │   └── styles.css
│   │   ├── utils/
│   │   │   ├── authStorage.ts
│   │   │   └── imageFile.ts
│   │   ├── views/
│   │   │   ├── Login.vue                 # 登录页
│   │   │   ├── Dashboard.vue             # 资源总览 + 量化指标
│   │   │   ├── Topology.vue              # 服务拓扑
│   │   │   ├── Copilot.vue               # AI Copilot
│   │   │   ├── PodManage.vue             # Pod 管理
│   │   │   ├── DeploymentManage.vue      # 副本管理
│   │   │   ├── AlertHistory.vue          # 告警历史
│   │   │   ├── AuditLog.vue              # 审计日志
│   │   │
│   │   ├── App.vue
│   │   └── main.ts
│   ├── Dockerfile
│   ├── index.html
│   ├── nginx.conf                        # 反代 + SSE + WebSocket
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
└── k8s/                                  # K8s 部署清单
    ├── mysql.yaml                        # MySQL + 初始化
    ├── collector-daemonset.yaml          # 采集器 DaemonSet
    ├── rbac.yaml                         # SA + ClusterRole + Binding
    ├── backend.yaml                      # 后端 Deployment + Service
    ├── frontend.yaml                     # 前端 Deployment + Service
    └── prometheus/
        ├── prometheus-rbac.yaml
        ├── prometheus-config.yaml
        └── prometheus.yaml
```

## 🚀 快速开始

### 前置条件

- Kubernetes 集群（v1.20+）
- Docker
- DeepSeek API Key（用于 AI 功能）

### 一键部署

```
git clone https://github.com/你的用户名/aiops-platform.git
cd aiops-platform
chmod +x deploy.sh
./deploy.sh
```



### 手动部署

```
# 1. 命名空间和 Secret
kubectl create namespace privatization
kubectl create secret generic aiops-secret -n privatization \
  --from-literal=mysql-password='root123456' \
  --from-literal=jwt-secret="$(openssl rand -hex 32)" \
  --from-literal=webhook-url='' \
  --from-literal=api-key='sk-你的DeepSeekKey'

# 2. 依次部署
kubectl apply -f k8s/mysql.yaml
kubectl apply -f k8s/collector-daemonset.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/prometheus/

# 3. 获取访问地址
kubectl -n privatization get svc
```

**默认账号**：`admin` / `admin123`

  ------

  ## 📸 项目截图

  ### 登录页

  ![登录页](docs/images/login.png)

  *深紫渐变背景 + 粒子动画 + 玻璃拟态卡片*

  ### Dashboard 资源总览

   ![面板页](docs/images/dashboard.png)

  *节点状态卡片 + CPU/内存实时趋势图*

  ### Pod 管理

   ![Pod页](docs/images/pod.png)

  *Pod 列表 + 日志/事件/诊断/删除*

  ### 实时日志 + AI 分析

  ![分析页](docs/images/AI_Log.png)

  *WebSocket 实时日志 + AI 智能分析*

  ### 多信号融合诊断

  ![混合分析页](docs/images/ai_d.png)

  *四类信号交叉验证 + AI 根因推断*

  ### 告警历史

  ![告警历史页](docs/images/alert_history.png)

  *告警记录 + AI 建议 + 状态管理*

  ### 审计日志

  ![审计页](docs/images/audit.png)

  *所有变更操作留痕*

  ### AI Copilot分析

  ![AICopilot](docs/images/AI_Copilot.png)

  *根据定义的工具相应用户的请求*

  ### 服务拓扑

  ![拓扑图](docs/images/topology.png)

  *pod-service-ingress之间的关系*

  ------

 ## 💡 技术难点与解决方案

### 1. 容器内采集宿主机指标

**问题**：容器有独立命名空间，`psutil` 读到的不是宿主机数据。
**解决**：DaemonSet 挂载宿主机 `/proc`、`/sys`，配合 `privileged` 权限。

### 2. Pod 无法访问外网

**问题**：采集器调用 DeepSeek/企业微信 API 超时。
**排查**：Flannel SNAT 未开启 → MTU 不足 → CDN IP 部分不可达。
**解决**：`EnableSNAT: true` + MTU 1400 + `hostAliases` 固定 IP。

### 3. WebSocket 阻塞事件循环

**问题**：打开日志后后端 Pod 变成 `0/1`，readiness probe 超时。
**根因**：K8s Client 的 `follow=True` 是同步阻塞调用，占住 FastAPI 事件循环。
**解决**：用线程池（`run_in_executor`）隔离同步调用，改为 2 秒轮询 + 增量推送。

### 4. 固定阈值告警误报

**解决**：滑动窗口——10 个采样点中超标占比 ≥ 70% 才告警。

### 5. 多节点告警风暴

**解决**：5 分钟窗口内的告警合并，AI 分析共同根因，输出一条聚合告警。

### 6. SSE 流式输出被缓冲

**问题**：Copilot 的流式输出前端要等很久才显示。
**根因**：Nginx 默认缓冲 SSE 响应。
**解决**：响应头加 `X-Accel-Buffering: no`，Nginx 加 `proxy_buffering off`。

### 7. Python 依赖版本冲突

**问题**：`openai==1.30.0` 与新版 `httpx` 不兼容。
**解决**：升级 `openai>=1.55.0` + 显式声明 `httpx>=0.27.0`。

### 8. RBAC 权限不足

**问题**：拓扑推导报 `Forbidden: services/replicasets/ingresses`。
**解决**：`ClusterRole` 补齐三类资源权限。

------

## 🔑 环境变量说明

### 采集器

| 变量                                           | 说明               | 默认值   |
| :--------------------------------------------- | :----------------- | :------- |
| `CPU_MAXUSE` / `MEMORY_MAXUSE` / `DISK_MAXUSE` | 告警阈值           | 80/90/80 |
| `INTERVAL`                                     | 采集间隔（秒）     | 3        |
| `ALERT_WINDOW_SIZE`                            | 滑动窗口大小       | 10       |
| `ALERT_THRESHOLD_RATIO`                        | 超标占比阈值       | 0.7      |
| `ALERT_COOLDOWN`                               | 冷却时间（秒）     | 60       |
| `AGGREGATE_WINDOW`                             | 告警聚合窗口（秒） | 300      |

### 后端

| 变量                  | 说明            |
| :-------------------- | :-------------- |
| `SECRET_KEY`          | JWT 签名密钥    |
| `MYSQL_*`             | MySQL 连接信息  |
| `PROMETHEUS_URL`      | Prometheus 地址 |
| `API_KEY` / `API_URL` | DeepSeek API    |
| `LOG_MODEL_NAME`      | 日志分析模型    |
| `DIAGNOSE_MODEL_NAME` | 诊断模型        |
| `COPILOT_MODEL_NAME`  | Copilot 模型    |

------

## 📊 项目数据

| 指标         | 数值                                    |
| :----------- | :-------------------------------------- |
| 代码文件     | 100+                                    |
| 后端接口     | 22                                      |
| 前端页面     | 8                                       |
| AI 能力      | 5 层                                    |
| Copilot 工具 | 10 个                                   |
| 告警治理策略 | 滑动窗口 + 冷却 + 聚合 + 量化           |
| K8s 资源     | DaemonSet × 1、Deployment × 5、RBAC × 3 |

------

## 🎯 后续规划

- □ 动态阈值（EWMA / 3-sigma）
- □ 告警规则在线配置
- □ Copilot 支持多轮修改操作（扩容/删除）
- □ 多集群管理
- □ Grafana 集成

------

## 📄 License

MIT License

  
