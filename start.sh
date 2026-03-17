#!/bin/bash
# -*- coding: utf-8 -*-
"""
跨性别资源搜索引擎 - 本地启动脚本

用途：
1. 启动 Meilisearch（Docker）
2. 运行爬虫（可选）
3. 启动 PHP 本地服务器

使用方法：
  ./start.sh          # 启动所有服务
  ./start.sh meili   # 仅启动 Meilisearch
  ./start.sh crawl   # 仅运行爬虫
  ./start.sh php     # 仅启动 PHP 服务器
"""

set -e

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 启动 Meilisearch
start_meilisearch() {
    echo_info "启动 Meilisearch..."
    
    if command -v docker &> /dev/null; then
        docker-compose up -d meilisearch
        echo_info "Meilisearch 启动完成，访问 http://localhost:7700"
    else
        echo_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
}

# 运行爬虫
run_crawler() {
    echo_info "运行爬虫..."
    
    cd "$PROJECT_ROOT/transspider"
    scrapy crawl trans
    
    if [ $? -eq 0 ]; then
        echo_info "爬虫运行完成"
    else
        echo_error "爬虫运行失败"
        exit 1
    fi
}

# 启动 PHP 服务器
start_php() {
    echo_info "启动 PHP 本地服务器..."
    echo_info "访问 http://localhost:8080"
    echo_info "按 Ctrl+C 停止服务器"
    
    cd "$PROJECT_ROOT/frontend"
    php -S localhost:8080
}

# 显示帮助
show_help() {
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  (无参数)   启动所有服务（Meilisearch + PHP）"
    echo "  meili      仅启动 Meilisearch"
    echo "  crawl      运行爬虫"
    echo "  php        仅启动 PHP 服务器"
    echo "  help       显示此帮助"
}

# 主逻辑
case "${1:-all}" in
    meili)
        start_meilisearch
        ;;
    crawl)
        run_crawler
        ;;
    php)
        start_php
        ;;
    all)
        start_meilisearch
        echo ""
        echo_info "Meilisearch 启动中，等待服务就绪..."
        sleep 3
        echo ""
        start_php
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo_error "未知命令: $1"
        show_help
        exit 1
        ;;
esac
