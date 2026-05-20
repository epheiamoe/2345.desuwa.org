#!/bin/bash
# =============================================================================
# 品牌替换脚本 (rebrand.sh)
# =============================================================================
# 将项目中的默认品牌信息替换为新品牌
#
# 用法：
#   交互式: ./scripts/rebrand.sh
#   非交互式: ./scripts/rebrand.sh --name "MySearch" --domain "search.example.com"
#   预览:   ./scripts/rebrand.sh --dry-run --name "Test"
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

# ---- 默认值 ----
DRY_RUN=false
FORCE=false
NEW_NAME=""
NEW_DOMAIN=""
NEW_TITLE=""
NEW_REPO=""

# 当前品牌值（从 config.json 读取或硬编码回退）
OLD_NAME=""
OLD_DOMAIN=""
OLD_TITLE=""
OLD_REPO=""
OLD_URL=""

# =============================================================================
# 工具函数
# =============================================================================

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "\n${BOLD}${CYAN}==>$1${NC}"; }

# 备份文件
backup_file() {
    local file="$1"
    if [ -f "$file" ]; then
        local backup="${file}.rebrand.bak.$(date +%Y%m%d_%H%M%S)"
        cp "$file" "$backup"
        echo "  已备份: $(basename "$file") → $(basename "$backup")"
    fi
}

# 安全替换（sed，兼容 GNU 和 BSD）
safe_replace() {
    local file="$1"
    local old="$2"
    local new="$3"

    if [ ! -f "$file" ]; then
        return 0
    fi

    # 转义 sed 特殊字符
    local escaped_old
    local escaped_new
    escaped_old=$(printf '%s' "$old" | sed 's/[&/\\]/\\&/g')
    escaped_new=$(printf '%s' "$new" | sed 's/[&/\\]/\\&/g')

    if [ "$DRY_RUN" = true ]; then
        local count
        count=$(grep -oF "$old" "$file" 2>/dev/null | wc -l || echo 0)
        count=$(echo "$count" | tr -d '[:space:]')
        if [ "$count" -gt 0 ] 2>/dev/null; then
            echo "  [预览] 将替换 $count 处: $file"
            grep -nF "$old" "$file" 2>/dev/null | head -5 | while read -r line; do
                echo "    $line"
            done
            if [ "$count" -gt 5 ]; then
                echo "    ... 还有 $((count - 5)) 处"
            fi
        fi
    else
        # 尝试 GNU sed，回退到 BSD sed
        if sed -i "s/${escaped_old}/${escaped_new}/g" "$file" 2>/dev/null; then
            :
        elif sed -i '' "s/${escaped_old}/${escaped_new}/g" "$file" 2>/dev/null; then
            :
        else
            log_error "无法替换文件: $file"
            return 1
        fi
    fi
}

# 替换 JSON 字段（使用 jq 优先，回退到 sed）
replace_json_field() {
    local file="$1"
    local field="$2"
    local value="$3"

    if [ ! -f "$file" ]; then
        return 0
    fi

    if command -v jq >/dev/null 2>&1; then
        if [ "$DRY_RUN" = true ]; then
            local old_val
            old_val=$(jq -r "$field" "$file" 2>/dev/null || echo "null")
            if [ "$old_val" != "null" ] && [ "$old_val" != "$value" ]; then
                echo "  [预览] config.json: $field = \"$value\" (旧值: \"$old_val\")"
            fi
        else
            local tmpfile
            tmpfile=$(mktemp)
            jq "$field = \"$value\"" "$file" > "$tmpfile" && mv "$tmpfile" "$file"
        fi
    else
        # 回退到 sed（简单字段替换）
        local field_escaped
        field_escaped=$(echo "$field" | sed 's/\./\\./')
        safe_replace "$file" "\"$field_escaped\": \"" "\"$field_escaped\": \"$value\""
    fi
}

# =============================================================================
# 参数解析
# =============================================================================

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --name)
                NEW_NAME="$2"
                shift 2
                ;;
            --domain)
                NEW_DOMAIN="$2"
                shift 2
                ;;
            --title)
                NEW_TITLE="$2"
                shift 2
                ;;
            --repo)
                NEW_REPO="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
                shift
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
品牌替换脚本 (rebrand.sh)

用法:
  ./scripts/rebrand.sh [选项]

交互式模式（默认）:
  ./scripts/rebrand.sh

非交互式模式:
  ./scripts/rebrand.sh \
    --name "MySearch" \
    --domain "search.example.com" \
    --title "My Trans Search" \
    --repo "https://github.com/myname/search"

选项:
  --name NAME        新站点名称
  --domain DOMAIN    新域名（自动添加 https://）
  --title TITLE      新站点标题
  --repo REPO        新 GitHub 仓库地址
  --dry-run          预览模式（不实际修改）
  --force            跳过确认
  --help, -h         显示此帮助

示例:
  # 预览
  ./scripts/rebrand.sh --dry-run --name "TestBrand"

  # 快速替换
  ./scripts/rebrand.sh --name "MySearch" --domain "search.example.com"
EOF
}

# =============================================================================
# 读取当前品牌
# =============================================================================

detect_current_brand() {
    local config_file="$PROJECT_ROOT/config.json"

    if [ -f "$config_file" ] && command -v jq >/dev/null 2>&1; then
        OLD_NAME=$(jq -r '.site.name // empty' "$config_file" 2>/dev/null || echo "")
        OLD_TITLE=$(jq -r '.site.title // empty' "$config_file" 2>/dev/null || echo "")
        OLD_URL=$(jq -r '.site.url // empty' "$config_file" 2>/dev/null || echo "")
        OLD_REPO=$(jq -r '.site.github_repo // empty' "$config_file" 2>/dev/null || echo "")
    fi

    # 如果无法读取，使用硬编码回退
    if [ -z "$OLD_NAME" ]; then
        OLD_NAME="2345.desuwa.org"
        OLD_TITLE="跨性别资源搜索"
        OLD_URL="https://2345.desuwa.org"
        OLD_REPO="https://github.com/epheiamoe/2345.desuwa.org"
    fi

    # 从 URL 提取域名
    OLD_DOMAIN=$(echo "$OLD_URL" | sed -E 's|https?://||' || echo "")
}

# =============================================================================
# 交互式输入
# =============================================================================

interactive_input() {
    echo -e "\n${BOLD}=== 品牌替换向导 ===${NC}\n"
    echo -e "当前品牌: ${CYAN}${OLD_NAME}${NC}"
    echo -e "当前域名: ${CYAN}${OLD_DOMAIN}${NC}"
    echo -e "当前标题: ${CYAN}${OLD_TITLE}${NC}\n"

    # 站点名称
    read -rp "新站点名称 [${OLD_NAME}]: " input
    NEW_NAME="${input:-$OLD_NAME}"

    # 域名
    read -rp "新域名 [${OLD_DOMAIN}]: " input
    NEW_DOMAIN="${input:-$OLD_DOMAIN}"

    # 标题
    read -rp "新站点标题 [${OLD_TITLE}]: " input
    NEW_TITLE="${input:-$OLD_TITLE}"

    # 仓库
    read -rp "GitHub 仓库地址 [${OLD_REPO}]: " input
    NEW_REPO="${input:-$OLD_REPO}"

    echo ""
}

# =============================================================================
# 验证输入
# =============================================================================

validate_input() {
    if [ -z "$NEW_NAME" ]; then
        log_error "站点名称不能为空"
        exit 1
    fi

    if [ -z "$NEW_DOMAIN" ]; then
        log_error "域名不能为空"
        exit 1
    fi

    # 自动添加 https://
    if [[ ! "$NEW_DOMAIN" =~ ^https?:// ]]; then
        NEW_DOMAIN="https://${NEW_DOMAIN}"
    fi

    if [ -z "$NEW_TITLE" ]; then
        NEW_TITLE="$NEW_NAME"
    fi

    if [ -z "$NEW_REPO" ]; then
        NEW_REPO="$OLD_REPO"
    fi
}

# =============================================================================
# 确认变更
# =============================================================================

confirm_changes() {
    if [ "$FORCE" = true ] || [ "$DRY_RUN" = true ]; then
        return 0
    fi

    echo -e "\n${BOLD}变更摘要:${NC}"
    echo "  站点名称: ${OLD_NAME} → ${CYAN}${NEW_NAME}${NC}"
    echo "  站点域名: ${OLD_URL} → ${CYAN}${NEW_DOMAIN}${NC}"
    echo "  站点标题: ${OLD_TITLE} → ${CYAN}${NEW_TITLE}${NC}"
    echo "  仓库地址: ${OLD_REPO} → ${CYAN}${NEW_REPO}${NC}"
    echo ""

    # 显示影响文件列表
    local files=(
        "$PROJECT_ROOT/config.json"
        "$PROJECT_ROOT/.env"
        "$PROJECT_ROOT/frontend/template.php"
        "$PROJECT_ROOT/scripts/install.sh"
    )

    # 检查 docs 文件
    for f in "$PROJECT_ROOT"/docs/*.md "$PROJECT_ROOT"/docs/*.html; do
        [ -f "$f" ] && files+=("$f")
    done

    echo -e "${BOLD}将修改的文件:${NC}"
    for f in "${files[@]}"; do
        if [ -f "$f" ]; then
            echo "  - $(basename "$f")"
        fi
    done
    echo ""

    read -rp "确认执行品牌替换? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消。"
        exit 0
    fi
}

# =============================================================================
# 执行替换
# =============================================================================

perform_rebrand() {
    local changes=()
    local changes_file="$PROJECT_ROOT/REBRAND_CHANGES.md"

    log_step "执行品牌替换..."

    # 1. 修改 config.json
    local config_file="$PROJECT_ROOT/config.json"
    if [ -f "$config_file" ]; then
        if [ "$DRY_RUN" = false ]; then
            backup_file "$config_file"
        fi

        if command -v jq >/dev/null 2>&1; then
            if [ "$DRY_RUN" = false ]; then
                local tmpfile
                tmpfile=$(mktemp)
                jq --arg name "$NEW_NAME" \
                   --arg title "$NEW_TITLE" \
                   --arg url "$NEW_DOMAIN" \
                   --arg repo "$NEW_REPO" \
                   '.site.name = $name | .site.title = $title | .site.url = $url | .site.github_repo = $repo' \
                   "$config_file" > "$tmpfile" && mv "$tmpfile" "$config_file"
                changes+=("config.json: 更新 site.name, site.title, site.url, site.github_repo")
            else
                echo "  [预览] config.json: 更新 site 字段"
            fi
        else
            # 回退到 sed
            safe_replace "$config_file" "\"name\": \"$OLD_NAME\"" "\"name\": \"$NEW_NAME\""
            safe_replace "$config_file" "\"title\": \"$OLD_TITLE\"" "\"title\": \"$NEW_TITLE\""
            safe_replace "$config_file" "\"url\": \"$OLD_URL\"" "\"url\": \"$NEW_DOMAIN\""
            safe_replace "$config_file" "\"github_repo\": \"$OLD_REPO\"" "\"github_repo\": \"$NEW_REPO\""
            changes+=("config.json: 使用 sed 替换站点信息")
        fi
    fi

    # 2. 修改 .env（如果存在）
    local env_file="$PROJECT_ROOT/.env"
    if [ -f "$env_file" ]; then
        if [ "$DRY_RUN" = false ]; then
            backup_file "$env_file"
        fi
        safe_replace "$env_file" "SITE_URL=${OLD_URL}" "SITE_URL=${NEW_DOMAIN}"
        safe_replace "$env_file" "SITE_URL=\"${OLD_URL}\"" "SITE_URL=\"${NEW_DOMAIN}\""
        safe_replace "$env_file" "SITE_NAME=${OLD_NAME}" "SITE_NAME=${NEW_NAME}"
        safe_replace "$env_file" "SITE_NAME=\"${OLD_NAME}\"" "SITE_NAME=\"${NEW_NAME}\""
        safe_replace "$env_file" "SITE_TITLE=${OLD_TITLE}" "SITE_TITLE=${NEW_TITLE}"
        safe_replace "$env_file" "SITE_TITLE=\"${OLD_TITLE}\"" "SITE_TITLE=\"${NEW_TITLE}\""
        if [ "$DRY_RUN" = false ]; then
            changes+=(".env: 更新 SITE_URL, SITE_NAME, SITE_TITLE")
        fi
    fi

    # 3. 修改 frontend/template.php（默认值回退）
    local template_file="$PROJECT_ROOT/frontend/template.php"
    if [ -f "$template_file" ]; then
        if [ "$DRY_RUN" = false ]; then
            backup_file "$template_file"
        fi

        # 替换默认值中的品牌信息
        safe_replace "$template_file" "'${OLD_NAME}'" "'${NEW_NAME}'"
        safe_replace "$template_file" "'${OLD_TITLE}'" "'${NEW_TITLE}'"
        safe_replace "$template_file" "'${OLD_URL}'" "'${NEW_DOMAIN}'"
        safe_replace "$template_file" "'${OLD_REPO}'" "'${NEW_REPO}'"

        # 同时替换域名相关
        local old_domain_plain
        old_domain_plain=$(echo "$OLD_URL" | sed 's|https://||')
        local new_domain_plain
        new_domain_plain=$(echo "$NEW_DOMAIN" | sed 's|https://||')

        safe_replace "$template_file" "'https://${old_domain_plain}'" "'https://${new_domain_plain}'"

        if [ "$DRY_RUN" = false ]; then
            changes+=("frontend/template.php: 更新默认回退值")
        fi
    fi

    # 4. 修改 docs/*.md 和 docs/*.html（谨慎替换）
    local docs_dir="$PROJECT_ROOT/docs"
    if [ -d "$docs_dir" ]; then
        for f in "$docs_dir"/*.md "$docs_dir"/*.html; do
            [ -f "$f" ] || continue
            if [ "$DRY_RUN" = false ]; then
                backup_file "$f"
            fi

            # 只替换明确的品牌引用（URL 和标题）
            safe_replace "$f" "$OLD_URL" "$NEW_DOMAIN"
            safe_replace "$f" "$OLD_NAME" "$NEW_NAME"
            safe_replace "$f" "${OLD_NAME} API" "${NEW_NAME} API"
            safe_replace "$f" "title>${OLD_NAME}" "title>${NEW_NAME}"
            safe_replace "$f" ">${OLD_NAME}<" ">${NEW_NAME}<"
            safe_replace "$f" "© 20[0-9][0-9] ${OLD_NAME}" "© $(date +%Y) ${NEW_NAME}"

            if [ "$DRY_RUN" = false ]; then
                changes+=("docs/$(basename "$f"): 更新品牌引用")
            fi
        done
    fi

    # 5. 修改 scripts/install.sh（提示文本中的品牌名）
    local install_file="$PROJECT_ROOT/scripts/install.sh"
    if [ -f "$install_file" ]; then
        if [ "$DRY_RUN" = false ]; then
            backup_file "$install_file"
        fi

        # 替换硬编码的品牌标题
        safe_replace "$install_file" "$OLD_TITLE" "$NEW_TITLE"
        safe_replace "$install_file" "${OLD_NAME} - 部署向导" "${NEW_NAME} - 部署向导"

        if [ "$DRY_RUN" = false ]; then
            changes+=("scripts/install.sh: 更新提示文本")
        fi
    fi

    # 生成变更清单
    if [ "$DRY_RUN" = false ] && [ ${#changes[@]} -gt 0 ]; then
        cat > "$changes_file" << EOF
# 品牌替换变更清单

日期: $(date '+%Y-%m-%d %H:%M:%S')

## 变更信息

- 站点名称: ${OLD_NAME} → ${NEW_NAME}
- 站点标题: ${OLD_TITLE} → ${NEW_TITLE}
- 站点 URL: ${OLD_URL} → ${NEW_DOMAIN}
- 仓库地址: ${OLD_REPO} → ${NEW_REPO}

## 修改文件

EOF
        for change in "${changes[@]}"; do
            echo "- ${change}" >> "$changes_file"
        done

        cat >> "$changes_file" << EOF

## 回滚方法

如需回滚，请恢复以下备份文件（删除 .rebrand.bak.* 后缀）：

EOF
        find "$PROJECT_ROOT" -name "*.rebrand.bak.*" -type f | while read -r bak; do
            local original
            original=$(echo "$bak" | sed 's/\.rebrand\.bak\.[0-9]*$//')
            echo "\`\`\`bash" >> "$changes_file"
            echo "cp \"$bak\" \"$original\"" >> "$changes_file"
            echo "\`\`\`" >> "$changes_file"
        done

        log_success "变更清单已生成: REBRAND_CHANGES.md"
    fi
}

# =============================================================================
# 显示结果
# =============================================================================

show_result() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "\n${BOLD}${YELLOW}=== 预览模式完成 ===${NC}"
        echo "以上是所有将被替换的内容。"
        echo "去掉 --dry-run 参数以实际执行替换。"
        return 0
    fi

    echo -e "\n${BOLD}${GREEN}=== 品牌替换完成 ===${NC}\n"
    echo -e "新品牌信息:"
    echo "  名称: ${CYAN}${NEW_NAME}${NC}"
    echo "  域名: ${CYAN}${NEW_DOMAIN}${NC}"
    echo "  标题: ${CYAN}${NEW_TITLE}${NC}"
    echo "  仓库: ${CYAN}${NEW_REPO}${NC}"
    echo ""
    echo -e "变更记录: ${CYAN}REBRAND_CHANGES.md${NC}"
    echo -e "备份文件: *.rebrand.bak.*${NC}"
    echo ""
    echo -e "${YELLOW}提示: 如果部署了 Nginx，请重启以应用配置变更${NC}"
    echo -e "      sudo systemctl reload nginx"
    echo ""
    echo -e "${YELLOW}提示: 运行验证脚本检查部署状态${NC}"
    echo -e "      ./scripts/verify.sh"
}

# =============================================================================
# 主逻辑
# =============================================================================

main() {
    parse_arguments "$@"
    detect_current_brand

    # 如果是非交互式模式，检查必需参数
    if [ -n "$NEW_NAME" ] || [ -n "$NEW_DOMAIN" ]; then
        if [ -z "$NEW_NAME" ] || [ -z "$NEW_DOMAIN" ]; then
            log_error "非交互式模式需要同时提供 --name 和 --domain"
            exit 1
        fi
    fi

    # 交互式输入
    if [ -z "$NEW_NAME" ] && [ "$DRY_RUN" = false ]; then
        interactive_input
    fi

    # 如果没有提供任何参数且不是 dry-run，进入交互模式
    if [ -z "$NEW_NAME" ] && [ "$DRY_RUN" = true ]; then
        log_error "--dry-run 模式需要至少提供一个参数（如 --name）"
        exit 1
    fi

    validate_input
    confirm_changes
    perform_rebrand
    show_result
}

# 运行主函数
main "$@"
