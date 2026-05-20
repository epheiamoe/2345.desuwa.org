#!/bin/bash
# -*- coding: utf-8 -*-
# =============================================================================
# 健康检查脚本
# 检查 Meilisearch、Flask API 和前端可访问性
# =============================================================================
set -euo pipefail

# 颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

# 配置
readonly MEILISEARCH_URL="http://127.0.0.1:7700"
readonly API_URL="http://127.0.0.1:5000"
readonly FRONTEND_URL="https://2345.desuwa.org"

log_pass() {
    printf "${GREEN}[PASS]${NC} %s\n" "$1"
}

log_fail() {
    printf "${RED}[FAIL]${NC} %s\n" "$1"
}

log_info() {
    printf "${YELLOW}[INFO]${NC} %s\n" "$1"
}

# =============================================================================
# 检查 Meilisearch 健康
# =============================================================================
check_meilisearch() {
    log_info "检查 Meilisearch 健康状态..."

    local response
    local status_code

    response=$(curl -s -o /dev/null -w "%{http_code}" \
        "${MEILISEARCH_URL}/health" 2>/dev/null || echo "000")

    if [[ "$response" == "200" ]]; then
        log_pass "Meilisearch 运行正常"
        return 0
    else
        log_fail "Meilisearch 健康检查失败 (HTTP ${response})"
        return 1
    fi
}

# =============================================================================
# 检查 Flask API 健康
# =============================================================================
check_api() {
    log_info "检查 Flask API 健康状态..."

    local response
    local status_code

    response=$(curl -s -o /dev/null -w "%{http_code}" \
        "${API_URL}/api/health" 2>/dev/null || echo "000")

    if [[ "$response" == "200" ]]; then
        log_pass "Flask API 运行正常"
        return 0
    else
        log_fail "Flask API 健康检查失败 (HTTP ${response})"
        return 1
    fi
}

# =============================================================================
# 检查前端可访问性
# =============================================================================
check_frontend() {
    log_info "检查前端可访问性..."

    local response
    local status_code

    response=$(curl -s -o /dev/null -w "%{http_code}" \
        "${FRONTEND_URL}" 2>/dev/null || echo "000")

    if [[ "$response" == "200" ]]; then
        log_pass "前端可访问"
        return 0
    else
        log_fail "前端访问失败 (HTTP ${response})"
        return 1
    fi
}

# =============================================================================
# 主流程
# =============================================================================
main() {
    log_info "开始健康检查..."

    local exit_code=0

    check_meilisearch || exit_code=1
    check_api || exit_code=1
    check_frontend || exit_code=1

    if [[ $exit_code -eq 0 ]]; then
        log_pass "所有检查通过"
    else
        log_fail "部分检查失败"
    fi

    return $exit_code
}

main "$@"
