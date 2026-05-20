#!/bin/bash
# =============================================================================
# 跨性别资源搜索引擎 - 一键部署脚本
# =============================================================================
# 支持三种部署模式：
#   minimal  - 仅搜索（PHP + Docker）
#   full     - 搜索+API+OAuth（PHP + Python + Docker）
#   docker   - 全部容器化（Docker Compose）
#
# 用法：
#   交互式: ./scripts/install.sh
#   自动模式: ./scripts/install.sh --mode minimal --auto --domain example.com
# =============================================================================

set -euo pipefail

# ---- 颜色定义 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ---- 默认配置 ----
MODE=""
AUTO=false
DOMAIN=""
TITLE=""
DEPLOY_PATH="/var/www/html"
GITHUB_CLIENT_ID=""
GITHUB_SECRET=""
ADMIN_USERS=""

# ---- 项目路径（自动检测） ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ---- 环境检测结果 ----
HAS_PHP=false
PHP_VERSION=""
HAS_DOCKER=false
DOCKER_VERSION=""
HAS_PYTHON=false
PYTHON_VERSION=""
HAS_NGINX=false
NGINX_VERSION=""
HAS_GIT=false
GIT_VERSION=""
HAS_DOCKER_COMPOSE=false

# =============================================================================
# 工具函数
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BOLD}${CYAN}==>$1${NC}"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if command_exists ss; then
        ss -tuln 2>/dev/null | grep -q ":$port " && return 0
    elif command_exists netstat; then
        netstat -tuln 2>/dev/null | grep -q ":$port " && return 0
    elif command_exists lsof; then
        lsof -i :"$port" >/dev/null 2>&1 && return 0
    fi
    return 1
}

# 生成随机字符串
generate_secret() {
    local length=${1:-32}
    if command_exists openssl; then
        openssl rand -base64 "$length" | tr -dc 'a-zA-Z0-9' | head -c "$length"
    else
        tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c "$length"
    fi
}

# 备份文件
backup_file() {
    local file=$1
    if [ -f "$file" ]; then
        local backup="${file}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$file" "$backup"
        log_info "已备份现有配置: $backup"
    fi
}

# 替换文件中的占位符
replace_placeholder() {
    local file=$1
    local placeholder=$2
    local value=$3
    # 使用 | 作为分隔符以避免值中包含 / 的问题
    sed -i "s|${placeholder}|${value}|g" "$file"
}

# =============================================================================
# 参数解析
# =============================================================================

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --mode)
                MODE="$2"
                shift 2
                ;;
            --auto)
                AUTO=true
                shift
                ;;
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            --title)
                TITLE="$2"
                shift 2
                ;;
            --path)
                DEPLOY_PATH="$2"
                shift 2
                ;;
            --github-client-id)
                GITHUB_CLIENT_ID="$2"
                shift 2
                ;;
            --github-secret)
                GITHUB_SECRET="$2"
                shift 2
                ;;
            --admin-users)
                ADMIN_USERS="$2"
                shift 2
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

show_help() {
    cat << 'EOF'
跨性别资源搜索引擎 - 部署脚本

用法:
  ./scripts/install.sh [选项]

交互式模式（默认）:
  ./scripts/install.sh

非交互式模式:
  ./scripts/install.sh --mode minimal --auto --domain example.com --title "My Search"

选项:
  --mode {minimal|full|docker}    部署模式
  --auto                          非交互式（全自动）
  --domain DOMAIN                 域名
  --title TITLE                   站点标题
  --path PATH                     部署路径（默认 /var/www/html）
  --github-client-id ID           GitHub Client ID（完整模式）
  --github-secret SECRET          GitHub Client Secret（完整模式）
  --admin-users USERS             管理员GitHub用户名，逗号分隔（完整模式）
  --help, -h                      显示此帮助

示例:
  # 最小模式（推荐新手）
  ./scripts/install.sh --mode minimal --auto \
    --domain search.example.com \
    --title "My Search" \
    --path /var/www/search

  # 完整模式
  ./scripts/install.sh --mode full --auto \
    --domain search.example.com \
    --title "My Search" \
    --path /var/www/search \
    --github-client-id xxx \
    --github-secret xxx

  # Docker模式
  ./scripts/install.sh --mode docker --auto \
    --domain search.example.com
EOF
}

# =============================================================================
# 环境检测
# =============================================================================

detect_environment() {
    log_step "检测环境..."

    # 检查 root 权限
    if [ "$EUID" -eq 0 ]; then
        log_warn "当前以 root 用户运行。Docker 需要 root 权限，但建议后续使用普通用户运行服务。"
    fi

    # 检测 PHP
    if command_exists php; then
        PHP_VERSION=$(php -v 2>/dev/null | head -n 1 | grep -oP '\d+\.\d+' | head -1 || echo "")
        if [ -n "$PHP_VERSION" ]; then
            HAS_PHP=true
            local major=$(echo "$PHP_VERSION" | cut -d. -f1)
            if [ "$major" -ge 8 ]; then
                log_success "PHP $PHP_VERSION"
            else
                log_warn "PHP $PHP_VERSION (建议 8.0+)"
            fi
        fi
    else
        log_error "PHP 未安装"
    fi

    # 检测 Docker
    if command_exists docker; then
        DOCKER_VERSION=$(docker --version 2>/dev/null | grep -oP '\d+\.\d+(\.\d+)?' | head -1 || echo "")
        if [ -n "$DOCKER_VERSION" ]; then
            HAS_DOCKER=true
            log_success "Docker $DOCKER_VERSION"
        fi
    else
        log_error "Docker 未安装"
    fi

    # 检测 Docker Compose
    if command_exists docker-compose; then
        HAS_DOCKER_COMPOSE=true
        log_success "Docker Compose 已安装"
    elif docker compose version >/dev/null 2>&1; then
        HAS_DOCKER_COMPOSE=true
        log_success "Docker Compose (plugin) 已安装"
    else
        log_warn "Docker Compose 未安装"
    fi

    # 检测 Python
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "")
        if [ -n "$PYTHON_VERSION" ]; then
            HAS_PYTHON=true
            log_success "Python $PYTHON_VERSION"
        fi
    elif command_exists python; then
        PYTHON_VERSION=$(python --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "")
        if [ -n "$PYTHON_VERSION" ]; then
            HAS_PYTHON=true
            log_success "Python $PYTHON_VERSION"
        fi
    else
        log_warn "Python 未安装"
    fi

    # 检测 Nginx
    if command_exists nginx; then
        NGINX_VERSION=$(nginx -v 2>&1 | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "")
        if [ -n "$NGINX_VERSION" ]; then
            HAS_NGINX=true
            log_success "Nginx $NGINX_VERSION"
        fi
    else
        log_warn "Nginx 未安装（可选）"
    fi

    # 检测 Git
    if command_exists git; then
        GIT_VERSION=$(git --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "")
        if [ -n "$GIT_VERSION" ]; then
            HAS_GIT=true
            log_success "Git $GIT_VERSION"
        fi
    else
        log_warn "Git 未安装（可选）"
    fi

    # 检查端口冲突
    log_step "检查端口冲突..."
    if check_port 7700; then
        log_warn "端口 7700 已被占用（Meilisearch 默认端口）"
    else
        log_success "端口 7700 可用"
    fi

    if check_port 5000; then
        log_warn "端口 5000 已被占用（Flask API 默认端口）"
    else
        log_success "端口 5000 可用"
    fi
}

# =============================================================================
# 交互式菜单
# =============================================================================

show_interactive_menu() {
    echo -e "\n${BOLD}=== 跨性别资源搜索引擎 安装向导 ===${NC}\n"

    # 显示环境检测结果
    echo -e "${BOLD}检测环境：${NC}"
    if [ "$HAS_PHP" = true ]; then
        echo -e "  ${GREEN}✓${NC} PHP $PHP_VERSION"
    else
        echo -e "  ${RED}✗${NC} PHP (未安装${NC}，必需)"
    fi

    if [ "$HAS_DOCKER" = true ]; then
        echo -e "  ${GREEN}✓${NC} Docker $DOCKER_VERSION"
    else
        echo -e "  ${RED}✗${NC} Docker (未安装${NC}，必需)"
    fi

    if [ "$HAS_PYTHON" = true ]; then
        echo -e "  ${GREEN}✓${NC} Python $PYTHON_VERSION"
    else
        echo -e "  ${YELLOW}✗${NC} Python (未安装，完整模式必需)"
    fi

    if [ "$HAS_NGINX" = true ]; then
        echo -e "  ${GREEN}✓${NC} Nginx $NGINX_VERSION"
    else
        echo -e "  ${YELLOW}✗${NC} Nginx (未安装，可选)"
    fi

    echo ""

    # 根据环境推荐模式
    local recommended=1
    if [ "$HAS_PHP" = false ] || [ "$HAS_DOCKER" = false ]; then
        echo -e "${RED}警告: 缺少必需依赖（PHP 或 Docker），请先安装。${NC}\n"
        echo "安装指南:"
        echo "  Ubuntu/Debian: sudo apt install php php-fpm docker.io"
        echo "  CentOS/RHEL:   sudo yum install php php-fpm docker"
        echo ""
        read -p "仍要继续吗? [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    # 显示模式选择
    echo -e "${BOLD}[1] 最小模式 - 仅搜索（推荐新手）${NC}"
    echo "    需要: PHP + Docker"
    echo "    功能: 搜索 + 爬虫（需手动运行）"
    echo "    时间: 约 5 分钟"
    echo ""

    echo -e "${BOLD}[2] 完整模式 - 搜索+API+OAuth${NC}"
    echo "    需要: PHP + Python + Docker"
    echo "    功能: 搜索 + API + OAuth + 爬虫"
    echo "    时间: 约 15 分钟"
    echo ""

    echo -e "${BOLD}[3] Docker模式 - 全部容器化${NC}"
    echo "    需要: Docker Compose"
    echo "    功能: 全部服务容器化"
    echo "    时间: 约 10 分钟"
    echo ""

    # 选择模式
    local default_choice=1
    if [ "$HAS_PYTHON" = true ]; then
        default_choice=2
    fi

    read -p "请选择 [${default_choice}]: " choice
    choice=${choice:-$default_choice}

    case $choice in
        1)
            MODE="minimal"
            ;;
        2)
            MODE="full"
            if [ "$HAS_PYTHON" = false ]; then
                echo -e "\n${RED}错误: 完整模式需要 Python，但未检测到。${NC}"
                echo "请先安装 Python: sudo apt install python3 python3-pip"
                exit 1
            fi
            ;;
        3)
            MODE="docker"
            if [ "$HAS_DOCKER_COMPOSE" = false ]; then
                echo -e "\n${RED}错误: Docker 模式需要 Docker Compose，但未检测到。${NC}"
                echo "安装: sudo apt install docker-compose-plugin"
                exit 1
            fi
            ;;
        *)
            log_error "无效选择: $choice"
            exit 1
            ;;
    esac

    # 输入域名
    echo ""
    read -p "请输入域名 [search.example.com]: " DOMAIN
    DOMAIN=${DOMAIN:-search.example.com}

    # 输入标题
    echo ""
    read -p "请输入站点标题 [跨性别资源搜索]: " TITLE
    TITLE=${TITLE:-跨性别资源搜索}

    # 输入部署路径
    echo ""
    read -p "请输入部署路径 [/var/www/html]: " DEPLOY_PATH
    DEPLOY_PATH=${DEPLOY_PATH:-/var/www/html}

    # 完整模式额外参数
    if [ "$MODE" = "full" ]; then
        echo ""
        echo -e "${BOLD}GitHub OAuth 配置（可选，留空则禁用登录）:${NC}"
        read -p "GitHub Client ID: " GITHUB_CLIENT_ID
        read -p "GitHub Client Secret: " GITHUB_SECRET
        read -p "管理员 GitHub 用户名（逗号分隔）: " ADMIN_USERS
    fi

    echo ""
    echo -e "${CYAN}部署配置确认:${NC}"
    echo "  模式: $MODE"
    echo "  域名: $DOMAIN"
    echo "  标题: $TITLE"
    echo "  路径: $DEPLOY_PATH"
    if [ "$MODE" = "full" ]; then
        echo "  GitHub OAuth: $([ -n "$GITHUB_CLIENT_ID" ] && echo "已配置" || echo "未配置")"
    fi
    echo ""
    read -p "确认开始部署? [Y/n]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "已取消部署。"
        exit 0
    fi
}

# =============================================================================
# 验证参数
# =============================================================================

validate_arguments() {
    if [ -z "$MODE" ]; then
        log_error "未指定部署模式。使用 --mode {minimal|full|docker} 或运行交互式模式。"
        exit 1
    fi

    if [[ ! "$MODE" =~ ^(minimal|full|docker)$ ]]; then
        log_error "无效的模式: $MODE。必须是 minimal、full 或 docker。"
        exit 1
    fi

    if [ -z "$DOMAIN" ]; then
        log_error "未指定域名。使用 --domain 参数。"
        exit 1
    fi

    if [ -z "$TITLE" ]; then
        TITLE="跨性别资源搜索"
    fi

    # 完整模式验证
    if [ "$MODE" = "full" ]; then
        if [ "$HAS_PYTHON" = false ]; then
            log_error "完整模式需要 Python，但未检测到。"
            exit 1
        fi
    fi

    # Docker 模式验证
    if [ "$MODE" = "docker" ]; then
        if [ "$HAS_DOCKER_COMPOSE" = false ]; then
            log_error "Docker 模式需要 Docker Compose，但未检测到。"
            exit 1
        fi
    fi
}

# =============================================================================
# 生成 .env 文件
# =============================================================================

generate_env_file() {
    log_step "生成环境配置文件 (.env)..."

    local env_file="$PROJECT_ROOT/.env"
    local env_template

    # 选择模板
    case $MODE in
        minimal)
            env_template="$PROJECT_ROOT/.env.minimal.example"
            ;;
        full)
            env_template="$PROJECT_ROOT/.env.full.example"
            ;;
        docker)
            env_template="$PROJECT_ROOT/.env.full.example"
            ;;
    esac

    # 检查模板是否存在
    if [ ! -f "$env_template" ]; then
        log_error "找不到环境变量模板: $env_template"
        log_info "请确保已从仓库正确克隆项目。"
        exit 1
    fi

    # 备份现有配置
    backup_file "$env_file"

    # 复制模板
    cp "$env_template" "$env_file"

    # 生成密钥
    local master_key
    local search_key
    local flask_secret
    master_key=$(generate_secret 32)
    search_key=$(generate_secret 32)
    flask_secret=$(generate_secret 48)

    # 替换占位符
    replace_placeholder "$env_file" "{{DOMAIN}}" "$DOMAIN"
    replace_placeholder "$env_file" "{{SITE_NAME}}" "$DOMAIN"
    replace_placeholder "$env_file" "{{SITE_TITLE}}" "$TITLE"
    replace_placeholder "$env_file" "MEILI_MASTER_KEY=" "MEILI_MASTER_KEY=$master_key"
    replace_placeholder "$env_file" "MEILISEARCH_API_KEY=" "MEILISEARCH_API_KEY=$search_key"

    # 完整模式/Docker模式额外替换
    if [ "$MODE" = "full" ] || [ "$MODE" = "docker" ]; then
        replace_placeholder "$env_file" "{{FLASK_SECRET}}" "$flask_secret"
        replace_placeholder "$env_file" "{{GITHUB_CLIENT_ID}}" "$GITHUB_CLIENT_ID"
        replace_placeholder "$env_file" "{{GITHUB_CLIENT_SECRET}}" "$GITHUB_SECRET"
        replace_placeholder "$env_file" "{{ADMIN_USERS}}" "$ADMIN_USERS"
    fi

    # 设置权限
    chmod 600 "$env_file"

    log_success ".env 文件已生成"
    log_info "Meilisearch Master Key: ${master_key:0:8}...（已保存到 .env）"
}

# =============================================================================
# 生成 config.json
# =============================================================================

generate_config_json() {
    log_step "生成共享配置文件 (config.json)..."

    local config_file="$PROJECT_ROOT/config.json"
    local config_template="$PROJECT_ROOT/config.example.json"

    # 检查模板是否存在
    if [ ! -f "$config_template" ]; then
        log_error "找不到配置文件模板: $config_template"
        exit 1
    fi

    # 备份现有配置
    backup_file "$config_file"

    # 复制模板
    cp "$config_template" "$config_file"

    # 替换占位符
    replace_placeholder "$config_file" "{{SITE_NAME}}" "$DOMAIN"
    replace_placeholder "$config_file" "{{SITE_TITLE}}" "$TITLE"
    replace_placeholder "$config_file" "{{SITE_URL}}" "https://$DOMAIN"
    replace_placeholder "$config_file" "{{DEPLOY_MODE}}" "$MODE"

    case $MODE in
        minimal)
            replace_placeholder "$config_file" "{{ENABLE_API}}" "false"
            replace_placeholder "$config_file" "{{ENABLE_OAUTH}}" "false"
            ;;
        full|docker)
            replace_placeholder "$config_file" "{{ENABLE_API}}" "true"
            if [ -n "$GITHUB_CLIENT_ID" ]; then
                replace_placeholder "$config_file" "{{ENABLE_OAUTH}}" "true"
            else
                replace_placeholder "$config_file" "{{ENABLE_OAUTH}}" "false"
            fi
            ;;
    esac

    log_success "config.json 已生成"
}

# =============================================================================
# 启动 Meilisearch
# =============================================================================

start_meilisearch() {
    log_step "启动 Meilisearch..."

    if [ "$HAS_DOCKER" = false ]; then
        log_error "Docker 未安装，无法启动 Meilisearch。"
        log_info "请先安装 Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi

    cd "$PROJECT_ROOT"

    # 加载环境变量以获取 Master Key
    local master_key
    master_key=$(grep "^MEILI_MASTER_KEY=" .env | cut -d= -f2)

    if [ -z "$master_key" ]; then
        log_error "无法从 .env 读取 MEILI_MASTER_KEY"
        exit 1
    fi

    # 导出环境变量供 docker-compose 使用
    export MEILI_MASTER_KEY="$master_key"

    # 启动 Meilisearch
    if docker-compose up -d meilisearch 2>/dev/null; then
        log_success "Meilisearch 容器已启动"
    elif docker compose up -d meilisearch 2>/dev/null; then
        log_success "Meilisearch 容器已启动 (Docker Compose plugin)"
    else
        log_error "启动 Meilisearch 失败"
        log_info "请检查 Docker 服务是否运行: sudo systemctl status docker"
        exit 1
    fi

    # 等待 Meilisearch 就绪
    log_info "等待 Meilisearch 就绪..."
    local retries=30
    local wait_time=0
    while [ $wait_time -lt $retries ]; do
        if curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $master_key" \
            "http://localhost:7700/health" 2>/dev/null | grep -q "200"; then
            log_success "Meilisearch 运行正常"
            return 0
        fi
        sleep 2
        wait_time=$((wait_time + 1))
        echo -n "."
    done
    echo ""

    log_warn "Meilisearch 启动超时，可能需要更长时间初始化。"
    log_info "您可以稍后手动检查: curl http://localhost:7700/health"
}

# =============================================================================
# 运行爬虫和添加直接链接
# =============================================================================

run_crawler_and_direct_links() {
    log_step "导入数据到 Meilisearch..."

    # 检查是否需要运行爬虫
    ENABLE_CRAWLER="${ENABLE_CRAWLER:-true}"
    if [ "$ENABLE_CRAWLER" != "false" ]; then
        log_info "正在运行爬虫抓取网站数据..."
        log_info "这可能需要 10-30 分钟，具体取决于网络速度"
        
        cd "$PROJECT_ROOT/transspider"
        
        # 使用虚拟环境中的 Python
        if [ -f "$PROJECT_ROOT/api/venv/bin/python" ]; then
            local python_cmd="$PROJECT_ROOT/api/venv/bin/python"
        elif [ -f "$PROJECT_ROOT/venv/bin/python" ]; then
            local python_cmd="$PROJECT_ROOT/venv/bin/python"
        else
            local python_cmd="python3"
        fi

        # 加载环境变量
        set -a && source "$PROJECT_ROOT/.env" && set +a

        # 确保日志目录存在
        mkdir -p "$PROJECT_ROOT/logs"

        # 后台运行爬虫
        if $python_cmd -m scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000 > "$PROJECT_ROOT/logs/crawler.log" 2>&1; then
            log_success "爬虫运行完成"
        else
            log_warn "爬虫运行可能遇到问题，请检查日志: $PROJECT_ROOT/logs/crawler.log"
            log_info "您可以稍后手动运行: cd transspider && scrapy crawl trans"
        fi

        cd "$PROJECT_ROOT"

        # 添加直接链接（Steam游戏、社交媒体等）
        log_info "正在添加直接链接..."
        mkdir -p "$PROJECT_ROOT/logs"
        if $python_cmd add_direct_links.py > "$PROJECT_ROOT/logs/direct_links.log" 2>&1; then
            log_success "直接链接添加完成"
        else
            log_warn "直接链接添加可能遇到问题，请检查日志"
            log_info "您可以稍后手动运行: python add_direct_links.py"
        fi
    else
        log_info "跳过爬虫（ENABLE_CRAWLER=false）"
        log_info "您可以稍后手动运行:"
        log_info "  1. cd transspider && scrapy crawl trans"
        log_info "  2. python add_direct_links.py"
    fi

    # 显示当前索引状态
    log_info "检查索引状态..."
    local api_key
    api_key=$(grep "^MEILISEARCH_API_KEY=" "$PROJECT_ROOT/.env" | cut -d= -f2)
    local doc_count
    doc_count=$(curl -s "http://localhost:7700/indexes/trans_resources/stats" \
        -H "Authorization: Bearer $api_key" 2>/dev/null | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('numberOfDocuments', 0))" 2>/dev/null || echo "0")
    
    log_info "当前索引文档数: $doc_count"
}

# =============================================================================
# 生成 Nginx 配置提示
# =============================================================================

setup_nginx() {
    log_step "Nginx 配置..."

    if [ "$HAS_NGINX" = true ]; then
        log_info "检测到 Nginx，以下是推荐配置："
    else
        log_info "未检测到 Nginx，以下是手动配置参考："
    fi

    # 生成配置内容
    local nginx_conf
    if [ "$MODE" = "full" ]; then
        nginx_conf=$(cat << 'EOF'
server {
    listen 80;
    server_name {{DOMAIN}};

    root {{DEPLOY_PATH}}/frontend;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        include fastcgi_params;
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param MEILISEARCH_API_KEY your_search_key_here;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ~ /\. {
        deny all;
    }
}
EOF
)
    else
        nginx_conf=$(cat << 'EOF'
server {
    listen 80;
    server_name {{DOMAIN}};

    root {{DEPLOY_PATH}}/frontend;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        include fastcgi_params;
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param MEILISEARCH_API_KEY your_search_key_here;
    }

    location ~ /\. {
        deny all;
    }
}
EOF
)
    fi

    # 替换变量
    nginx_conf="${nginx_conf//{{DOMAIN}}/$DOMAIN}"
    nginx_conf="${nginx_conf//{{DEPLOY_PATH}}/$DEPLOY_PATH}"

    # 输出配置
    echo ""
    echo -e "${CYAN}=== Nginx 配置 ===${NC}"
    echo "将此配置保存到 /etc/nginx/sites-available/$DOMAIN"
    echo "然后创建符号链接: ln -s /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/"
    echo ""
    echo -e "${YELLOW}${nginx_conf}${NC}"
    echo ""

    # 尝试写入配置文件（如果需要）
    if [ "$AUTO" = true ]; then
        local nginx_dir="/etc/nginx/sites-available"
        if [ -d "$nginx_dir" ] && [ "$EUID" -eq 0 ]; then
            echo "$nginx_conf" > "$nginx_dir/$DOMAIN"
            ln -sf "$nginx_dir/$DOMAIN" /etc/nginx/sites-enabled/ 2>/dev/null || true
            nginx -t 2>/dev/null && systemctl reload nginx 2>/dev/null
            log_success "Nginx 配置已写入并生效"
        else
            log_info "请以 root 权限运行以自动写入 Nginx 配置"
        fi
    fi
}

# =============================================================================
# 设置 Flask API（完整模式）
# =============================================================================

setup_api() {
    log_step "设置 Flask API..."

    if [ "$HAS_PYTHON" = false ]; then
        log_error "Python 未安装，无法设置 Flask API。"
        return 1
    fi

    local api_dir="$PROJECT_ROOT/api"
    cd "$api_dir"

    # 创建虚拟环境
    log_info "创建 Python 虚拟环境..."
    if [ ! -d "$api_dir/venv" ]; then
        if python3 -m venv venv 2>/dev/null; then
            log_success "虚拟环境已创建"
        else
            log_warn "无法创建虚拟环境，将使用系统 Python"
        fi
    fi

    # 安装依赖
    log_info "安装 Python 依赖..."
    if [ -f "$api_dir/venv/bin/pip" ]; then
        "$api_dir/venv/bin/pip" install -q -r requirements.txt
    elif [ -f "$api_dir/venv/Scripts/pip" ]; then
        "$api_dir/venv/Scripts/pip" install -q -r requirements.txt
    else
        pip3 install -q -r requirements.txt
    fi
    log_success "依赖安装完成"

    # 生成 systemd 服务文件（仅 root）
    if [ "$EUID" -eq 0 ]; then
        local service_file="/etc/systemd/system/transsearch-api.service"
        local python_path
        if [ -f "$api_dir/venv/bin/python" ]; then
            python_path="$api_dir/venv/bin/python"
        elif [ -f "$api_dir/venv/Scripts/python" ]; then
            python_path="$api_dir/venv/Scripts/python"
        else
            python_path="$(command -v python3)"
        fi

        cat > "$service_file" << EOF
[Unit]
Description=TransSearch Flask API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$PROJECT_ROOT
Environment=PATH=$python_path
EnvironmentFile=$PROJECT_ROOT/.env
ExecStart=$python_path $api_dir/wsgi.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

        systemctl daemon-reload
        systemctl enable transsearch-api
        systemctl start transsearch-api
        log_success "systemd 服务已创建并启动: transsearch-api"
    else
        log_info "请以 root 权限运行以自动创建 systemd 服务"
        log_info "或手动运行: cd $api_dir && python3 wsgi.py"
    fi
}

# =============================================================================
# Docker 模式部署
# =============================================================================

setup_docker_mode() {
    log_step "Docker 模式部署..."

    if [ "$HAS_DOCKER_COMPOSE" = false ]; then
        log_error "Docker Compose 未安装"
        exit 1
    fi

    cd "$PROJECT_ROOT"

    # 检查是否存在 docker-compose.full.yml
    if [ ! -f "$PROJECT_ROOT/docker-compose.full.yml" ]; then
        log_warn "未找到 docker-compose.full.yml，将使用标准 docker-compose.yml"
        log_info "您可能需要手动配置其他服务容器"
    fi

    # 启动所有服务
    if [ -f "$PROJECT_ROOT/docker-compose.full.yml" ]; then
        if docker-compose -f docker-compose.full.yml up -d 2>/dev/null; then
            log_success "所有 Docker 服务已启动"
        elif docker compose -f docker-compose.full.yml up -d 2>/dev/null; then
            log_success "所有 Docker 服务已启动 (Docker Compose plugin)"
        else
            log_error "启动 Docker 服务失败"
            exit 1
        fi
    else
        docker-compose up -d 2>/dev/null || docker compose up -d 2>/dev/null
        log_success "Meilisearch 已启动"
    fi
}

# =============================================================================
# 部署摘要
# =============================================================================

show_summary() {
    echo ""
    echo -e "${BOLD}${GREEN}========================================${NC}"
    echo -e "${BOLD}${GREEN}  部署完成！${NC}"
    echo -e "${BOLD}${GREEN}========================================${NC}"
    echo ""

    echo -e "${BOLD}部署摘要:${NC}"
    echo "  模式:     $MODE"
    echo "  域名:     $DOMAIN"
    echo "  标题:     $TITLE"
    echo "  路径:     $DEPLOY_PATH"
    echo ""

    echo -e "${BOLD}服务状态:${NC}"
    if [ "$HAS_DOCKER" = true ]; then
        echo "  Meilisearch: http://localhost:7700"
    fi
    if [ "$MODE" = "full" ]; then
        echo "  Flask API:   http://localhost:5000"
    fi
    echo ""

    echo -e "${BOLD}数据导入状态:${NC}"
    if [ "$ENABLE_CRAWLER" != "false" ]; then
        echo "  ✓ 爬虫已自动运行（抓取网站数据）"
        echo "  ✓ 直接链接已自动添加（Steam游戏、社交媒体等）"
        echo "  日志: $PROJECT_ROOT/logs/crawler.log"
        echo "  日志: $PROJECT_ROOT/logs/direct_links.log"
    else
        echo "  ⚠ 爬虫已跳过（ENABLE_CRAWLER=false）"
        echo "  手动运行: cd $PROJECT_ROOT/transspider && scrapy crawl trans"
        echo "  手动运行: cd $PROJECT_ROOT && python add_direct_links.py"
    fi
    echo ""

    echo -e "${BOLD}下一步操作:${NC}"
    echo "  1. 配置 Nginx（参考上方输出的配置）"
    echo "  2. 配置 SSL/TLS（推荐使用 Certbot: certbot --nginx）"
    echo ""

    if [ "$MODE" = "full" ] && [ -n "$GITHUB_CLIENT_ID" ]; then
        echo -e "${BOLD}GitHub OAuth 配置:${NC}"
        echo "  1. 在 GitHub 开发者设置中配置回调 URL:"
        echo "     https://$DOMAIN/api/auth/callback"
        echo "  2. 确认 ADMIN_USERS 包含您的 GitHub 用户名"
        echo ""
    fi

    echo -e "${BOLD}验证部署:${NC}"
    echo "  运行验证脚本: $SCRIPT_DIR/verify.sh"
    echo ""

    echo -e "${BOLD}文档:${NC}"
    echo "  快速开始: $PROJECT_ROOT/docs/deploy/QUICKSTART.md"
    echo "  故障排查: $PROJECT_ROOT/docs/deploy/TROUBLESHOOTING.md"
    echo ""

    # 显示 .env 位置提醒
    echo -e "${YELLOW}重要: 配置文件已生成在 $PROJECT_ROOT/.env${NC}"
    echo -e "${YELLOW}请妥善保管 MEILI_MASTER_KEY 和 MEILISEARCH_API_KEY${NC}"
    echo ""
}

# =============================================================================
# 主逻辑
# =============================================================================

main() {
    # 解析参数
    parse_arguments "$@"

    # 显示欢迎信息
    if [ "$AUTO" = false ]; then
        echo -e "\n${BOLD}${CYAN}跨性别资源搜索引擎 - 部署向导${NC}"
        echo -e "${CYAN}让任何人都能部署自己的搜索引擎${NC}\n"
    fi

    # 检测环境
    detect_environment

    # 交互式模式显示菜单
    if [ "$AUTO" = false ]; then
        show_interactive_menu
    fi

    # 验证参数
    validate_arguments

    # 生成配置文件
    generate_env_file
    generate_config_json

    # 根据模式启动服务
    case $MODE in
        minimal)
            start_meilisearch
            ;;
        full)
            start_meilisearch
            setup_api
            ;;
        docker)
            setup_docker_mode
            ;;
    esac

    # 运行爬虫和添加直接链接
    run_crawler_and_direct_links

    # 配置 Nginx
    setup_nginx

    # 显示摘要
    show_summary
}

# 运行主函数
main "$@"
