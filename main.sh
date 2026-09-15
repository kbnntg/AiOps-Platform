cat  ~aiops-platformdeploy.sh 'DEPLOY_EOF'
#!binbash
# ============================================================
# AIOps 智能运维平台 - 一键部署脚本
# 功能：环境检测 → 配置收集 → 镜像构建 → K8s 部署 → 健康验证
# ============================================================

set -e

# ==================== 颜色定义 ====================
RED='033[0;31m'
GREEN='033[0;32m'
YELLOW='033[1;33m'
BLUE='033[0;34m'
CYAN='033[0;36m'
NC='033[0m'

info()    { echo -e ${BLUE}[INFO]${NC} $1; }
success() { echo -e ${GREEN}[✓]${NC} $1; }
warn()    { echo -e ${YELLOW}[!]${NC} $1; }
error()   { echo -e ${RED}[✗]${NC} $1; }
step()    { echo -e n${CYAN}━━━ $1 ━━━${NC}; }

# ==================== 全局变量 ====================
WORKDIR=$(cd $(dirname $0); pwd)
NAMESPACE=privatization
VERSION=v1.0.0

MYSQL_PASSWORD=
JWT_SECRET=
API_KEY=
WEBHOOK_URL=
SKIP_BUILD=false

# ==================== 解析参数 ====================
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build) SKIP_BUILD=true; shift ;;
        --namespace)  NAMESPACE=$2; shift 2 ;;
        --version)    VERSION=$2; shift 2 ;;
        -h--help)
            echo 用法 $0 [选项]
            echo   --skip-build       跳过镜像构建（镜像已存在时）
            echo   --namespace NAME   指定命名空间（默认 privatization）
            echo   --version VER      指定镜像版本（默认 v1.0.0）
            exit 0
            ;;
        ) error 未知参数 $1; exit 1 ;;
    esac
done

# ==================== 环境检测 ====================
check_env() {
    step 环境检测

    # Docker
    if ! command -v docker &devnull; then
        error 未安装 Docker
        exit 1
    fi
    success Docker $(docker --version  awk '{print $3}')

    # kubectl
    if ! command -v kubectl &devnull; then
        error 未安装 kubectl
        exit 1
    fi
    if ! kubectl cluster-info &devnull; then
        error kubectl 无法连接集群
        exit 1
    fi
    local node_count=$(kubectl get nodes --no-headers 2devnull  wc -l)
    success Kubernetes ${node_count} 个节点

    # 磁盘空间
    local avail=$(df -BG $WORKDIR  sed -n '2p'  awk '{print $4}'  tr -d 'G')
    if [ $avail -lt 10 ]; then
        warn 磁盘可用空间 ${avail}G，建议至少 10G
        read -p 是否继续？(yN)  c
        [[ $c != y ]] && exit 1
    else
        success 磁盘可用空间 ${avail}G
    fi

    # 检查目录结构
    for d in backend collector frontend k8s; do
        if [ ! -d $WORKDIR$d ]; then
            error 缺少目录 $d
            exit 1
        fi
    done
    success 项目结构完整
}

# ==================== 收集配置 ====================
collect_config() {
    step 配置收集

    # MySQL 密码
    read -s -p MySQL root 密码（默认 root123456）  MYSQL_PASSWORD
    echo 
    MYSQL_PASSWORD=${MYSQL_PASSWORD-root123456}

    # JWT 密钥
    JWT_SECRET=$(openssl rand -hex 32 2devnull  date +%s  sha256sum  head -c 64)
    success JWT 密钥已自动生成

    # DeepSeek API Key
    read -p DeepSeek API Key（可留空跳过 AI 功能）  API_KEY
    if [ -z $API_KEY ]; then
        warn 未配置 API Key，AI 功能将不可用
    else
        success AI 功能已启用
    fi

    # Webhook
    read -p 告警 Webhook 地址（可留空）  WEBHOOK_URL

    echo 
    info 配置确认：
    echo   命名空间   $NAMESPACE
    echo   镜像版本   $VERSION
    echo   MySQL 密码 ${MYSQL_PASSWORD03}
    echo   AI 功能    $([ -n $API_KEY ] && echo '启用'  echo '跳过')
    echo 
    read -p 确认开始部署？(yN)  c
    [[ $c != y ]] && { info 已取消; exit 0; }
}

# ==================== 构建镜像 ====================
build_images() {
    if [ $SKIP_BUILD = true ]; then
        info 跳过镜像构建
        return
    fi

    step 构建镜像

    # 后端
    info 构建后端镜像...
    cd $WORKDIRbackend
    docker build -t aiops-backend${VERSION} -f Dockerfile.backend .  {
        error 后端镜像构建失败
        exit 1
    }
    success 后端镜像构建完成

    # 前端
    info 构建前端镜像（可能较慢）...
    cd $WORKDIRfrontend
    docker build -t aiops-frontend${VERSION} .  {
        error 前端镜像构建失败
        exit 1
    }
    success 前端镜像构建完成

    # 采集器
    info 构建采集器镜像...
    cd $WORKDIRcollector
    docker build -t aiops-collector${VERSION} .  {
        error 采集器镜像构建失败
        exit 1
    }
    success 采集器镜像构建完成

    cd $WORKDIR
}

# ==================== 创建命名空间和 Secret ====================
create_namespace_and_secret() {
    step 初始化命名空间和 Secret

    # 命名空间
    if kubectl get namespace $NAMESPACE &devnull; then
        warn 命名空间 $NAMESPACE 已存在
    else
        kubectl create namespace $NAMESPACE
        success 命名空间 $NAMESPACE 已创建
    fi

    # Secret
    if kubectl -n $NAMESPACE get secret aiops-secret &devnull; then
        warn Secret aiops-secret 已存在，更新中...
        kubectl -n $NAMESPACE delete secret aiops-secret
    fi

    kubectl -n $NAMESPACE create secret generic aiops-secret 
        --from-literal=mysql-password=$MYSQL_PASSWORD 
        --from-literal=jwt-secret=$JWT_SECRET 
        --from-literal=webhook-url=$WEBHOOK_URL 
        --from-literal=api-key=$API_KEY
    success Secret 已创建
}

# ==================== 部署各组件 ====================
deploy_mysql() {
    step 部署 MySQL
    kubectl apply -f $WORKDIRk8smysql.yaml
    info 等待 MySQL 就绪（最多 3 分钟）...
    kubectl -n $NAMESPACE wait --for=condition=ready pod -l app=aiops-mysql --timeout=180s  {
        error MySQL 启动失败，查看日志：kubectl -n $NAMESPACE logs -l app=aiops-mysql
        exit 1
    }
    success MySQL 就绪
}

deploy_collector() {
    step 部署采集器 DaemonSet
    kubectl apply -f $WORKDIRk8scollector-daemonset.yaml
    sleep 5
    local ready=$(kubectl -n $NAMESPACE get pods -l app=node-monitor --no-headers 2devnull  grep -c 11  echo 0)
    if [ $ready -gt 0 ]; then
        success 采集器已部署（${ready} 个节点就绪）
    else
        warn 采集器正在启动中...
    fi
}

deploy_backend() {
    step 部署后端

    # RBAC
    kubectl apply -f $WORKDIRk8srbac.yaml
    success RBAC 已创建

    # 替换镜像版本
    sed simage aiops-backend.image aiops-backend${VERSION} 
        $WORKDIRk8sbackend.yaml  kubectl apply -f -
    info 等待后端就绪...
    kubectl -n $NAMESPACE wait --for=condition=ready pod -l app=aiops-backend --timeout=180s  {
        error 后端启动失败，查看日志：kubectl -n $NAMESPACE logs -l app=aiops-backend
        exit 1
    }
    success 后端就绪
}

deploy_frontend() {
    step 部署前端
    sed simage aiops-frontend.image aiops-frontend${VERSION} 
        $WORKDIRk8sfrontend.yaml  kubectl apply -f -
    info 等待前端就绪...
    kubectl -n $NAMESPACE wait --for=condition=ready pod -l app=aiops-frontend --timeout=120s  {
        error 前端启动失败
        exit 1
    }
    success 前端就绪
}

deploy_prometheus() {
    step 部署 Prometheus
    if [ -d $WORKDIRk8sprometheus ]; then
        kubectl apply -f $WORKDIRk8sprometheus
        sleep 10
        local ready=$(kubectl -n $NAMESPACE get pods -l app=prometheus --no-headers 2devnull  grep -c 11  echo 0)
        if [ $ready -gt 0 ]; then
            success Prometheus 已就绪
        else
            warn Prometheus 启动中，可稍后检查
        fi
    else
        warn 未找到 Prometheus 清单目录，跳过
    fi
}

# ==================== 验证部署 ====================
verify_deployment() {
    step 验证部署状态

    sleep 10

    # 获取各服务 NodePort
    local frontend_port=$(kubectl -n $NAMESPACE get svc aiops-frontend -o jsonpath='{.spec.ports[0].nodePort}' 2devnull)
    local backend_port=$(kubectl -n $NAMESPACE get svc aiops-backend -o jsonpath='{.spec.ports[0].nodePort}' 2devnull)
    local prom_port=$(kubectl -n $NAMESPACE get svc prometheus -o jsonpath='{.spec.ports[0].nodePort}' 2devnull)

    # 获取节点 IP
    local node_ip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[(@.type==InternalIP)].address}')

    # 健康检查
    info 执行健康检查...
    if [ -n $backend_port ]; then
        local health=$(curl -s -m 5 http${node_ip}${backend_port}apihealth 2devnull)
        if echo $health  grep -q healthy; then
            success 后端健康检查通过
        else
            warn 后端健康检查未通过
        fi
    fi

    # 显示最终信息
    echo 
    echo -e ${GREEN}╔════════════════════════════════════════════════════════════╗${NC}
    echo -e ${GREEN}║                  🎉 部署完成！                             ║${NC}
    echo -e ${GREEN}╚════════════════════════════════════════════════════════════╝${NC}
    echo 
    echo -e   ${CYAN}访问地址：${NC}
    echo -e     Web 平台  ${GREEN}http${node_ip}${frontend_port}${NC}
    echo -e     API 文档  ${GREEN}http${node_ip}${backend_port}docs${NC}
    if [ -n $prom_port ]; then
        echo -e     Prometheus ${GREEN}http${node_ip}${prom_port}${NC}
    fi
    echo 
    echo -e   ${CYAN}默认账号：${NC} admin  admin123
    echo 
    echo -e   ${CYAN}常用命令：${NC}
    echo -e     查看所有 Pod  kubectl -n $NAMESPACE get pods
    echo -e     查看后端日志  kubectl -n $NAMESPACE logs -f -l app=aiops-backend
    echo -e     卸载全部      kubectl delete namespace $NAMESPACE
    echo 
}

# ==================== 卸载函数 ====================
uninstall() {
    warn 即将删除命名空间 $NAMESPACE 及所有资源
    read -p 确认卸载？(yN)  c
    if [ $c = y ]; then
        kubectl delete namespace $NAMESPACE
        success 已卸载
    else
        info 已取消
    fi
}

# ==================== 主流程 ====================
main() {
    echo 
    echo -e ${CYAN}╔════════════════════════════════════════════════════════════╗${NC}
    echo -e ${CYAN}║         AIOps 智能运维平台 - 一键部署脚本                  ║${NC}
    echo -e ${CYAN}╚════════════════════════════════════════════════════════════╝${NC}

    check_env
    collect_config
    build_images
    create_namespace_and_secret
    deploy_mysql
    deploy_collector
    deploy_backend
    deploy_frontend
    deploy_prometheus
    verify_deployment
}

main $@
DEPLOY_EOF

chmod +x ~aiops-platformdeploy.sh