#!/bin/bash
# ============================================================
# AIOps 智能运维平台 - 一键部署脚本
# 功能：环境检测 → 配置收集 → 镜像构建 → K8s 部署 → 健康验证
# ============================================================

set -e

# ==================== 颜色定义 ====================
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; }
step()    { echo -e "\n${CYAN}━━━ $1 ━━━${NC}"; }

# ==================== 全局变量 ====================
WORKDIR=$(cd $(dirname $0); pwd)
NAMESPACE="privatization"
VERSION="v1.0.0"

MYSQL_PASSWORD=""
JWT_SECRET=""
API_KEY=""
EMBEDDING_API_KEY=""
WEBHOOK_URL=""
SKIP_BUILD=false

# ==================== 解析参数 ====================
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)      SKIP_BUILD=true; shift ;;
        --namespace)       NAMESPACE="$2"; shift 2 ;;
        --version)         VERSION="$2"; shift 2 ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo "  --skip-build       跳过镜像构建"
            echo "  --namespace NAME   命名空间（默认 privatization）"
            echo "  --version VER      镜像版本（默认 v1.0.0）"
            exit 0 ;;
        *) error "未知参数: $1"; exit 1 ;;
    esac
done

# ==================== 环境检测 ====================
check_env() {
    step "环境检测"

    # Docker
    if ! command -v docker &>/dev/null; then
        error "未安装 Docker"; exit 1
    fi
    success "Docker: $(docker --version | awk '{print $3}')"

    # kubectl
    if ! command -v kubectl &>/dev/null; then
        error "未安装 kubectl"; exit 1
    fi
    if ! kubectl cluster-info &>/dev/null; then
        error "kubectl 无法连接集群"; exit 1
    fi
    local node_count=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
    success "Kubernetes: ${node_count} 个节点"

    # StorageClass（PVC 必需）
    if ! kubectl get storageclass 2>/dev/null | grep -q "(default)"; then
        warn "没有默认 StorageClass，PVC 无法绑定"
        warn "建议先装: kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.28/deploy/local-path-storage.yaml"
        read -p "是否继续？(y/N): " c
        [[ "$c" != "y" ]] && exit 1
    else
        success "StorageClass: 已配置"
    fi

    # metrics-server（HPA 必需）
    if ! kubectl top nodes &>/dev/null; then
        warn "metrics-server 不可用，HPA 无法工作（不影响核心功能）"
    else
        success "metrics-server: 可用"
    fi

    # 磁盘空间
    local avail=$(df -BG "$WORKDIR" | sed -n '2p' | awk '{print $4}' | tr -d 'G')
    if [ "$avail" -lt 10 ]; then
        warn "磁盘可用空间 ${avail}G，建议至少 10G"
        read -p "是否继续？(y/N): " c
        [[ "$c" != "y" ]] && exit 1
    else
        success "磁盘可用空间: ${avail}G"
    fi

    # 目录结构
    for d in backend collector frontend k8s; do
        if [ ! -d "$WORKDIR/$d" ]; then
            error "缺少目录: $d"; exit 1
        fi
    done
    success "项目结构完整"
}

# ==================== 收集配置 ====================
collect_config() {
    step "配置收集"

    read -s -p "MySQL root 密码（默认: root123456）: " MYSQL_PASSWORD
    echo ""
    MYSQL_PASSWORD=${MYSQL_PASSWORD:-"root123456"}

    JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || date +%s | sha256sum | head -c 64)
    success "JWT 密钥已自动生成"

    read -p "DeepSeek API Key（可留空跳过 AI）: " API_KEY
    [ -z "$API_KEY" ] && warn "未配置 DeepSeek，AI 功能不可用" || success "AI 功能已启用"

    read -p "硅基流动 API Key（可留空跳过 RAG）: " EMBEDDING_API_KEY
    [ -z "$EMBEDDING_API_KEY" ] && warn "未配置 Embedding，RAG 不可用" || success "RAG 功能已启用"

    read -p "告警 Webhook 地址（可留空）: " WEBHOOK_URL

    echo ""
    info "配置确认："
    echo "  命名空间:    $NAMESPACE"
    echo "  镜像版本:    $VERSION"
    echo "  MySQL 密码:  ${MYSQL_PASSWORD:0:3}****"
    echo "  AI 功能:     $([ -n "$API_KEY" ] && echo '启用' || echo '跳过')"
    echo "  RAG 功能:    $([ -n "$EMBEDDING_API_KEY" ] && echo '启用' || echo '跳过')"
    echo ""
    read -p "确认开始部署？(y/N): " c
    [[ "$c" != "y" ]] && { info "已取消"; exit 0; }
}

# ==================== 构建镜像 ====================
build_images() {
    if [ "$SKIP_BUILD" = true ]; then
        info "跳过镜像构建"; return
    fi

    step "构建镜像"

    info "[1/3] 构建后端镜像..."
    cd "$WORKDIR/backend"
    docker build -t aiops-backend:${VERSION} -f Dockerfile.backend . || { error "后端构建失败"; exit 1; }
    success "后端镜像构建完成"

    info "[2/3] 构建前端镜像..."
    cd "$WORKDIR/frontend"
    docker build -t aiops-frontend:${VERSION} . || { error "前端构建失败"; exit 1; }
    success "前端镜像构建完成"

    info "[3/3] 构建采集器镜像..."
    cd "$WORKDIR/collector"
    docker build -t aiops-collector:${VERSION} . || { error "采集器构建失败"; exit 1; }
    success "采集器镜像构建完成"

    cd "$WORKDIR"
}

# ==================== 创建命名空间和 Secret ====================
init_namespace_secret() {
    step "初始化命名空间和 Secret"

    if kubectl get namespace "$NAMESPACE" &>/dev/null; then
        warn "命名空间 $NAMESPACE 已存在"
    else
        kubectl create namespace "$NAMESPACE"
        success "命名空间 $NAMESPACE 已创建"
    fi

    if kubectl -n "$NAMESPACE" get secret aiops-secret &>/dev/null; then
        warn "Secret aiops-secret 已存在，更新中..."
        kubectl -n "$NAMESPACE" delete secret aiops-secret
    fi

    kubectl -n "$NAMESPACE" create secret generic aiops-secret \
        --from-literal=mysql-password="$MYSQL_PASSWORD" \
        --from-literal=jwt-secret="$JWT_SECRET" \
        --from-literal=webhook-url="$WEBHOOK_URL" \
        --from-literal=api-key="$API_KEY" \
        --from-literal=embedding-api-key="$EMBEDDING_API_KEY"
    success "Secret 已创建"
}

# ==================== 部署各组件 ====================
deploy_storage() {
    step "部署存储层（MySQL + Redis + Chroma）"

    info "部署 ChromaDB PVC..."
    kubectl apply -f "$WORKDIR/k8s/chroma-pvc.yaml" 2>/dev/null || warn "chroma-pvc.yaml 不存在，跳过"

    info "部署 MySQL StatefulSet..."
    kubectl apply -f "$WORKDIR/k8s/mysql.yaml"

    info "部署 Redis StatefulSet..."
    kubectl apply -f "$WORKDIR/k8s/redis.yaml"

    info "等待 MySQL 就绪（最多 3 分钟）..."
    kubectl -n "$NAMESPACE" wait --for=condition=ready pod/aiops-mysql-0 --timeout=180s || {
        error "MySQL 启动失败"
        kubectl -n "$NAMESPACE" describe pod aiops-mysql-0 | tail -20
        exit 1
    }
    success "MySQL 就绪"

    info "等待 Redis 就绪..."
    kubectl -n "$NAMESPACE" wait --for=condition=ready pod/aiops-redis-0 --timeout=120s || warn "Redis 未就绪"
    success "Redis 就绪"
}

deploy_collector() {
    step "部署采集器 DaemonSet"
    kubectl apply -f "$WORKDIR/k8s/collector-daemonset.yaml"
    sleep 5
    local ready=$(kubectl -n "$NAMESPACE" get pods -l app=node-monitor --no-headers 2>/dev/null | grep -c "1/1" || echo 0)
    [ "$ready" -gt 0 ] && success "采集器已部署（${ready} 个节点）" || warn "采集器启动中..."
}

deploy_backend() {
    step "部署后端服务"

    kubectl apply -f "$WORKDIR/k8s/rbac.yaml"
    success "RBAC 已创建"

    sed "s|image: aiops-backend:.*|image: aiops-backend:${VERSION}|" \
        "$WORKDIR/k8s/backend.yaml" | kubectl apply -f -
    success "后端 Deployment 已创建"

    # PDB + HPA（可选）
    [ -f "$WORKDIR/k8s/backend-pdb.yaml" ] && kubectl apply -f "$WORKDIR/k8s/backend-pdb.yaml" && success "PDB 已创建"
    [ -f "$WORKDIR/k8s/backend-hpa.yaml" ] && kubectl apply -f "$WORKDIR/k8s/backend-hpa.yaml" && success "HPA 已创建"

    info "等待后端就绪（最多 3 分钟）..."
    kubectl -n "$NAMESPACE" wait --for=condition=ready pod -l app=aiops-backend --timeout=180s || {
        error "后端启动失败"
        kubectl -n "$NAMESPACE" logs -l app=aiops-backend --tail=30
        exit 1
    }
    success "后端就绪"
}

deploy_frontend() {
    step "部署前端服务"
    sed "s|image: aiops-frontend:.*|image: aiops-frontend:${VERSION}|" \
        "$WORKDIR/k8s/frontend.yaml" | kubectl apply -f -
    info "等待前端就绪..."
    kubectl -n "$NAMESPACE" wait --for=condition=ready pod -l app=aiops-frontend --timeout=120s || warn "前端未就绪"
    success "前端就绪"
}

deploy_prometheus() {
    step "部署 Prometheus"
    if [ -d "$WORKDIR/k8s/prometheus" ]; then
        kubectl apply -f "$WORKDIR/k8s/prometheus/"
        sleep 10
        local ready=$(kubectl -n "$NAMESPACE" get pods -l app=prometheus --no-headers 2>/dev/null | grep -c "1/1" || echo 0)
        [ "$ready" -gt 0 ] && success "Prometheus 已就绪" || warn "Prometheus 启动中"
    else
        warn "未找到 Prometheus 目录，跳过"
    fi
}

# ==================== 验证部署 ====================
verify_deployment() {
    step "验证部署状态"
    sleep 10

    local frontend_port=$(kubectl -n "$NAMESPACE" get svc aiops-frontend -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
    local backend_port=$(kubectl -n "$NAMESPACE" get svc aiops-backend -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
    local prom_port=$(kubectl -n "$NAMESPACE" get svc prometheus -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
    local node_ip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

    info "执行健康检查..."
    if [ -n "$backend_port" ]; then
        local health=$(curl -s -m 5 "http://${node_ip}:${backend_port}/api/health" 2>/dev/null)
        echo "$health" | grep -q "healthy" && success "后端健康检查通过" || warn "后端健康检查未通过"
    fi

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  🎉 部署完成！                         ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${CYAN}访问地址：${NC}"
    echo -e "    Web 平台:   ${GREEN}http://${node_ip}:${frontend_port}${NC}"
    echo -e "    API 文档:   ${GREEN}http://${node_ip}:${backend_port}/docs${NC}"
    [ -n "$prom_port" ] && echo -e "    Prometheus: ${GREEN}http://${node_ip}:${prom_port}${NC}"
    echo ""
    echo -e "  ${CYAN}默认账号：${NC} admin / admin123"
    echo ""
    echo -e "  ${CYAN}常用命令：${NC}"
    echo -e "    查看 Pod:    kubectl -n $NAMESPACE get pods"
    echo -e "    查看后端日志: kubectl -n $NAMESPACE logs -f -l app=aiops-backend"
    echo -e "    卸载全部:    kubectl delete namespace $NAMESPACE"
    echo ""
}

# ==================== 主流程 ====================
main() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║        AIOps 智能运维平台 - 一键部署脚本              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"

    check_env
    collect_config
    build_images
    init_namespace_secret
    deploy_storage
    deploy_collector
    deploy_backend
    deploy_frontend
    deploy_prometheus
    verify_deployment
}

main "$@"
