#!/bin/bash
# -*- coding: utf-8 -*-
# =============================================================================
# 部署脚本
# 2345.desuwa.org - 跨性别资源搜索引擎
# =============================================================================
set -euo pipefail

# 颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# 配置
readonly PROJECT_DIR="/www/wwwroot/2345.desuwa.org"
readonly BACKUP_DIR="/www/backup/2345.desuwa.org"
readonly VENV_DIR="${PROJECT_DIR}/api/venv"
readonly API_DIR="${PROJECT_DIR}/api"
readonly LOG_DIR="/var/log/2345.desuwa.org"

# 必需的环境变量
readonly REQUIRED_ENVS=(
    "MEILI_MASTER_KEY"
    "MEILISEARCH_API_KEY"
    "FLASK_SECRET"
    "GITHUB_CLIENT_ID"
    "GITHUB_CLIENT_SECRET"
)

log_info() {
    printf "${GREEN}[INFO]${NC} %s\n" "$1"
}

log_warn() {
    printf "${YELLOW}[WARN]${NC} %s\n" "$1"
}

log_error() {
    printf "${RED}[ERROR]${NC} %s\n" "$1"
}

# =============================================================================
# 1. 检查环境变量
# =============================================================================
check_env_vars() {
    log_info "检查环境变量..."
    local missing=()

    for var in "${REQUIRED_ENVS[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing+=("$var")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "缺少必需的环境变量:"
        printf '  - %s\n' "${missing[@]}"
        exit 1
    fi

    log_info "环境变量检查通过"
}

# =============================================================================
# 2. 备份现有数据
# =============================================================================
backup_data() {
    log_info "备份现有数据..."

    local backup_timestamp
    backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="${BACKUP_DIR}/${backup_timestamp}"

    mkdir -p "$backup_path"

    # 备份数据库
    if [[ -f "${API_DIR}/db.json" ]]; then
        cp "${API_DIR}/db.json" "${backup_path}/db.json"
        log_info "数据库已备份到 ${backup_path}/db.json"
    fi

    # 备份 SQLite 数据库（如果存在）
    if [[ -f "${API_DIR}/db.sqlite" ]]; then
        cp "${API_DIR}/db.sqlite" "${backup_path}/db.sqlite"
        log_info "SQLite 数据库已备份到 ${backup_path}/db.sqlite"
    fi

    # 备份配置
    if [[ -f "${API_DIR}/.env" ]]; then
        cp "${API_DIR}/.env" "${backup_path}/.env"
        log_info "环境配置已备份"
    fi

    # 保留最近 10 个备份
    if [[ -d "$BACKUP_DIR" ]]; then
        local backup_count
        backup_count=$(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)
        if [[ $backup_count -gt 10 ]]; then
            log_info "清理旧备份..."
            find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d | sort | head -n -10 | xargs rm -rf
        fi
    fi

    log_info "备份完成"
}

# =============================================================================
# 3. 创建虚拟环境
# =============================================================================
setup_venv() {
    log_info "设置 Python 虚拟环境..."

    if [[ ! -d "$VENV_DIR" ]]; then
        python3 -m venv "$VENV_DIR"
        log_info "虚拟环境已创建"
    else
        log_info "虚拟环境已存在"
    fi

    # 激活虚拟环境
    source "${VENV_DIR}/bin/activate"

    # 升级 pip
    pip install --upgrade pip

    log_info "虚拟环境准备就绪"
}

# =============================================================================
# 4. 安装依赖
# =============================================================================
install_dependencies() {
    log_info "安装 Python 依赖..."

    source "${VENV_DIR}/bin/activate"

    if [[ -f "${API_DIR}/requirements.lock.txt" ]]; then
        pip install -r "${API_DIR}/requirements.lock.txt"
    else
        pip install -r "${API_DIR}/requirements.txt"
    fi

    log_info "依赖安装完成"
}

# =============================================================================
# 5. 运行数据库迁移
# =============================================================================
run_migrations() {
    log_info "运行数据库迁移..."

    source "${VENV_DIR}/bin/activate"

    if [[ -f "${API_DIR}/db.json" && ! -f "${API_DIR}/db.sqlite" ]]; then
        python3 "${PROJECT_DIR}/scripts/migrate_db.py" \
            --source "${API_DIR}/db.json" \
            --target "${API_DIR}/db.sqlite"
        log_info "数据库迁移完成"
    else
        log_info "跳过数据库迁移（db.json 不存在或 db.sqlite 已存在）"
    fi
}

# =============================================================================
# 6. 重启服务
# =============================================================================
restart_services() {
    log_info "重启服务..."

    # 重启 Meilisearch
    if command -v docker-compose &> /dev/null; then
        cd "$PROJECT_DIR"
        docker-compose up -d meilisearch
        log_info "Meilisearch 已重启"
    elif command -v docker &> /dev/null; then
        cd "$PROJECT_DIR"
        docker compose up -d meilisearch
        log_info "Meilisearch 已重启"
    fi

    # 重启 Flask API
    log_info "重启 Flask API..."
    pkill -f 'python.*api/app.py' || true

    sleep 2

    cd "$API_DIR"
    nohup python3 app.py > "${LOG_DIR}/api.log" 2>&1 &

    log_info "Flask API 已重启"
}

# =============================================================================
# 7. 健康检查
# =============================================================================
health_check() {
    log_info "执行健康检查..."

    sleep 5

    bash "${PROJECT_DIR}/scripts/health_check.sh"
}

# =============================================================================
# 主流程
# =============================================================================
main() {
    log_info "开始部署 2345.desuwa.org..."

    # 创建日志目录
    mkdir -p "$LOG_DIR"

    check_env_vars
    backup_data
    setup_venv
    install_dependencies
    run_migrations
    restart_services
    health_check

    log_info "部署完成！"
}

main "$@"
