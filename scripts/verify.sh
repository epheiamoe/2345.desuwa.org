#!/bin/bash
# =============================================================================
# 部署验证脚本 (verify.sh)
# =============================================================================
# 验证部署是否成功，检查各项依赖和服务状态
#
# 用法：
#   ./scripts/verify.sh
#   ./scripts/verify.sh --help
# =============================================================================

set -euo pipefail

# ---- 颜色定义 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ---- 路径定义 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ---- 状态统计 ----
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARN_CHECKS=0

# ---- 配置读取 ----
MEILISEARCH_HOST="localhost"
MEILISEARCH_PORT="7700"
MEILISEARCH_API_KEY=""
SITE_URL=""
INDEX_NAME="trans_resources"
ENABLE_API="false"

# =============================================================================
# 输出函数
# =============================================================================

check_pass() {
    echo -e "  ${GREEN}✅${NC} $1"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
}

check_fail() {
    echo -e "  ${RED}❌${NC} $1"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

check_warn() {
    echo -e "  ${YELLOW}⚠️${NC}  $1"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    WARN_CHECKS=$((WARN_CHECKS + 1))
}

print_section() {
    echo -e "\n${BOLD}$1${NC}"
}

# =============================================================================
# 配置加载
# =============================================================================

load_config() {
    # 从 .env 加载
    local env_file="$PROJECT_ROOT/.env"
    if [ -f "$env_file" ]; then
        # shellcheck source=/dev/null
        set -a
        # shellcheck source=/dev/null
        source "$env_file" 2>/dev/null || true
        set +a
    fi

    # 从 config.json 加载
    local config_file="$PROJECT_ROOT/config.json"
    if [ -f "$config_file" ] && command -v jq >/dev/null 2>&1; then
        MEILISEARCH_HOST=$(jq -r '.meilisearch.host // "localhost"' "$config_file" 2>/dev/null || echo "localhost")
        MEILISEARCH_PORT=$(jq -r '.meilisearch.port // "7700"' "$config_file" 2>/dev/null || echo "7700")
        INDEX_NAME=$(jq -r '.search.index_name // "trans_resources"' "$config_file" 2>/dev/null || echo "trans_resources")
        SITE_URL=$(jq -r '.site.url // ""' "$config_file" 2>/dev/null || echo "")
    fi

    # 环境变量优先
    MEILISEARCH_HOST="${MEILISEARCH_HOST:-localhost}"
    MEILISEARCH_PORT="${MEILISEARCH_PORT:-7700}"
    MEILISEARCH_API_KEY="${MEILISEARCH_API_KEY:-}"
    INDEX_NAME="${INDEX_NAME:-trans_resources}"
    ENABLE_API="${ENABLE_API:-false}"
}

# =============================================================================
# 检查项
# =============================================================================

check_php() {
    print_section "[环境]"

    if command -v php >/dev/null 2>&1; then
        local version
        version=$(php -v 2>/dev/null | head -n 1 | grep -oP '\d+\.\d+' | head -1 || echo "")
        if [ -n "$version" ]; then
            local major minor
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            if [ "$major" -gt 7 ] || ([ "$major" -eq 7 ] && [ "$minor" -ge 4 ]); then
                check_pass "PHP ${version}"
            else
                check_fail "PHP ${version}（需要 ≥7.4）"
            fi
        else
            check_fail "PHP 已安装但无法获取版本"
        fi
    else
        check_fail "PHP 未安装"
    fi
}

check_docker() {
    if command -v docker >/dev/null 2>&1; then
        local version
        version=$(docker --version 2>/dev/null | grep -oP '\d+\.\d+(\.\d+)?' | head -1 || echo "")
        if docker info >/dev/null 2>&1; then
            check_pass "Docker ${version}"
        else
            check_warn "Docker ${version}（守护进程未运行）"
        fi
    else
        check_fail "Docker 未安装"
    fi
}

check_meilisearch() {
    print_section "[服务]"

    local health_url="http://${MEILISEARCH_HOST}:${MEILISEARCH_PORT}/health"
    local health_response
    local http_code

    health_response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer ${MEILISEARCH_API_KEY}" \
        "$health_url" 2>/dev/null || echo "000")

    if [ "$health_response" = "200" ]; then
        local version
        version=$(curl -s \
            -H "Authorization: Bearer ${MEILISEARCH_API_KEY}" \
            "http://${MEILISEARCH_HOST}:${MEILISEARCH_PORT}/version" 2>/dev/null | \
            grep -oP '"pkgVersion":"\K[^"]+' || echo "未知")
        check_pass "Meilisearch 运行中 (v${version})"

        # 检查索引
        check_index
    elif [ "$health_response" = "000" ]; then
        check_fail "Meilisearch 无法连接 (${MEILISEARCH_HOST}:${MEILISEARCH_PORT})"
    elif [ "$health_response" = "401" ]; then
        check_warn "Meilisearch 需要认证（API Key 无效）"
    else
        check_fail "Meilisearch 返回 HTTP ${health_response}"
    fi
}

check_index() {
    local index_url="http://${MEILISEARCH_HOST}:${MEILISEARCH_PORT}/indexes/${INDEX_NAME}/stats"
    local stats_response

    stats_response=$(curl -s \
        -H "Authorization: Bearer ${MEILISEARCH_API_KEY}" \
        "$index_url" 2>/dev/null || echo "")

    if [ -n "$stats_response" ]; then
        local doc_count
        doc_count=$(echo "$stats_response" | grep -oP '"numberOfDocuments":\K\d+' || echo "0")
        if [ "$doc_count" -gt 0 ] 2>/dev/null; then
            check_pass "索引 '${INDEX_NAME}' 存在 (${doc_count} 条文档)"
        else
            check_warn "索引 '${INDEX_NAME}' 存在但文档数为 0"
        fi
    else
        check_warn "索引 '${INDEX_NAME}' 状态未知"
    fi
}

check_config() {
    print_section "[配置]"

    local config_file="$PROJECT_ROOT/config.json"
    if [ -f "$config_file" ]; then
        if command -v jq >/dev/null 2>&1; then
            if jq empty "$config_file" 2>/dev/null; then
                check_pass "config.json 有效"
            else
                check_fail "config.json 格式无效"
            fi
        else
            check_pass "config.json 存在（未安装 jq，跳过格式验证）"
        fi
    else
        check_fail "config.json 不存在"
    fi
}

check_env() {
    local env_file="$PROJECT_ROOT/.env"
    if [ -f "$env_file" ]; then
        # 检查必填项
        local has_url=false
        local has_name=false

        if grep -qE '^SITE_URL=' "$env_file"; then
            local url
            url=$(grep -E '^SITE_URL=' "$env_file" | cut -d= -f2)
            if [ -n "$url" ] && [ "$url" != "{{SITE_URL}}" ]; then
                has_url=true
            fi
        fi

        if grep -qE '^SITE_NAME=' "$env_file"; then
            local name
            name=$(grep -E '^SITE_NAME=' "$env_file" | cut -d= -f2)
            if [ -n "$name" ] && [ "$name" != "{{SITE_NAME}}" ]; then
                has_name=true
            fi
        fi

        if [ "$has_url" = true ] && [ "$has_name" = true ]; then
            check_pass ".env 已配置"
        else
            check_warn ".env 存在但必填项未完整配置"
        fi
    else
        check_warn ".env 不存在（使用默认配置）"
    fi
}

check_nginx() {
    print_section "[Nginx]"

    if command -v nginx >/dev/null 2>&1; then
        local version
        version=$(nginx -v 2>&1 | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "")
        check_pass "Nginx ${version}"

        # 检查配置是否有效
        if nginx -t >/dev/null 2>&1; then
            check_pass "Nginx 配置有效"
        else
            check_warn "Nginx 配置测试失败"
        fi

        # 检查站点配置是否存在
        local site_conf="/etc/nginx/sites-enabled"
        if [ -d "$site_conf" ] && [ -n "$SITE_URL" ]; then
            local domain
            domain=$(echo "$SITE_URL" | sed 's|https\?://||')
            if find "$site_conf" -type l -o -type f 2>/dev/null | xargs grep -l "$domain" 2>/dev/null | grep -q .; then
                check_pass "Nginx 站点配置存在 (${domain})"
            else
                check_warn "Nginx 站点配置未找到 (${domain})"
            fi
        fi
    else
        check_warn "Nginx 未安装（可选）"
    fi
}

check_frontend() {
    print_section "[前端]"

    if [ -n "$SITE_URL" ]; then
        local response
        response=$(curl -s -o /dev/null -w "%{http_code}" "$SITE_URL" 2>/dev/null || echo "000")

        if [ "$response" = "200" ]; then
            check_pass "${SITE_URL} 可访问"

            # 检查搜索功能（尝试搜索 "HRT"）
            local search_response
            search_response=$(curl -s "${SITE_URL}/?q=HRT" 2>/dev/null | grep -oP '找到约 \K[0-9,]+' | head -1 || echo "")
            if [ -n "$search_response" ]; then
                check_pass "搜索功能正常（找到约 ${search_response} 个结果）"
            else
                check_warn "搜索页面可访问但无法确认搜索功能"
            fi
        elif [ "$response" = "000" ]; then
            check_warn "${SITE_URL} 无法连接（请检查域名解析）"
        else
            check_warn "${SITE_URL} 返回 HTTP ${response}"
        fi
    else
        check_warn "站点 URL 未配置，跳过前端检查"
    fi
}

check_api() {
    print_section "[API]"

    if [ "$ENABLE_API" = "true" ] || [ "$ENABLE_API" = "True" ] || [ "$ENABLE_API" = "1" ]; then
        local api_url="${SITE_URL}/api/health"
        if [ -z "$SITE_URL" ]; then
            api_url="http://localhost:5000/api/health"
        fi

        local response
        response=$(curl -s -o /dev/null -w "%{http_code}" "$api_url" 2>/dev/null || echo "000")

        if [ "$response" = "200" ]; then
            check_pass "API 运行中 (${api_url})"
        elif [ "$response" = "503" ]; then
            check_warn "API 已禁用（返回 503）"
        elif [ "$response" = "000" ]; then
            check_fail "API 无法连接"
        else
            check_warn "API 返回 HTTP ${response}"
        fi

        # 检查 OAuth 配置
        if [ -n "${GITHUB_CLIENT_ID:-}" ]; then
            check_pass "GitHub OAuth 已配置"
        else
            check_warn "GitHub OAuth 未配置"
        fi
    else
        check_warn "API 未启用（ENABLE_API=false）"
    fi
}

# =============================================================================
# 总结
# =============================================================================

show_summary() {
    echo -e "\n${BOLD}========================================${NC}"
    echo -e "${BOLD}           验证完成${NC}"
    echo -e "${BOLD}========================================${NC}\n"

    echo -e "  总检查项: ${TOTAL_CHECKS}"
    echo -e "  ${GREEN}通过: ${PASSED_CHECKS}${NC}"
    echo -e "  ${YELLOW}警告: ${WARN_CHECKS}${NC}"
    echo -e "  ${RED}失败: ${FAILED_CHECKS}${NC}"
    echo ""

    if [ $FAILED_CHECKS -eq 0 ]; then
        if [ $WARN_CHECKS -eq 0 ]; then
            echo -e "${BOLD}${GREEN}总体状态: ✅ 部署成功${NC}"
        else
            echo -e "${BOLD}${YELLOW}总体状态: ⚠️ 部署基本成功，但有警告${NC}"
        fi
    else
        echo -e "${BOLD}${RED}总体状态: ❌ 部署存在问题${NC}"
        echo ""
        echo -e "${YELLOW}建议:${NC}"
        echo "  1. 检查失败项并修复"
        echo "  2. 重新运行 ./scripts/verify.sh"
        echo "  3. 查看文档: docs/deploy/TROUBLESHOOTING.md"
    fi
    echo ""
}

show_help() {
    cat << 'EOF'
部署验证脚本 (verify.sh)

用法:
  ./scripts/verify.sh

检查项:
  - PHP 版本 (≥7.4)
  - Docker 运行状态
  - Meilisearch 可访问性
  - config.json 有效性
  - .env 配置完整性
  - Nginx 配置
  - 前端可访问性
  - 搜索功能
  - API 健康（如果启用）

选项:
  --help, -h    显示此帮助
EOF
}

# =============================================================================
# 主逻辑
# =============================================================================

main() {
    if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
        show_help
        exit 0
    fi

    echo -e "${BOLD}${CYAN}=== 部署验证 ===${NC}"

    load_config
    check_php
    check_docker
    check_config
    check_env
    check_meilisearch
    check_nginx
    check_frontend
    check_api
    show_summary

    # 如果有失败，返回非零退出码
    if [ $FAILED_CHECKS -gt 0 ]; then
        exit 1
    fi
}

# 运行主函数
main "$@"
