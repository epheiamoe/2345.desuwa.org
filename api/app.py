# -*- coding: utf-8 -*-
"""
2345.desuwa.org API 服务

重构后的 Flask API，使用新的安全组件：
- api.config: 统一配置管理
- api.database: SQLite 数据库替代 JSON 文件
- api.rate_limiter: 持久化速率限制
- api.validators: 输入验证

作者: TransSearch Team
许可证: MIT
"""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional

from flask import Flask, jsonify, redirect, request, send_from_directory, session
from flask_cors import CORS
import meilisearch
import requests

from api.config import ConfigError, config
from api.database import DatabaseError, db
from api.rate_limiter import RateLimitError, rate_limiter
from api.validators import InputValidator, ValidationError

# 引入语言检测规则
from language_rules import detect_language_from_url

logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置验证
if config is None:
    raise RuntimeError("Configuration initialization failed. Check .env file.")

# 配置 - 输出 UTF-8 而非 unicode 转义
app.json.ensure_ascii = False

# Session Cookie 安全配置
# Secure: 仅 HTTPS 传输（生产环境必须启用 HTTPS）
# HttpOnly: 禁止 JavaScript 访问 Cookie
# SameSite=Lax: 防范 CSRF 攻击
app.config.update(
    SECRET_KEY=config.flask_secret,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 限制请求体大小为 10MB
)

# GitHub OAuth 配置
GITHUB_CLIENT_ID = config.env_var("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = config.env_var("GITHUB_CLIENT_SECRET", "")

# Meilisearch 配置
MEILISEARCH_HOST = config.env_var("MEILISEARCH_HOST", "localhost")
MEILISEARCH_PORT = config.env_var("MEILISEARCH_PORT", "7700")
MEILISEARCH_INDEX = config.env_var("MEILISEARCH_INDEX", "trans_resources")
MEILISEARCH_API_KEY = config.env_var("MEILISEARCH_API_KEY", "")

# 站点配置
SITE_URL = config.env_var("SITE_URL", "https://2345.desuwa.org")

# CORS 配置
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [SITE_URL],
            "methods": ["GET", "POST"],
            "allow_headers": ["Authorization", "Content-Type"],
        }
    },
)

# 管理员配置（GitHub username）
ADMIN_USERS = [
    u.strip() for u in config.env_var("ADMIN_USERS", "").split(",") if u.strip()
]

# 数据库迁移：从 db.json 迁移到 SQLite（向后兼容）
DB_JSON_PATH = os.path.join(os.path.dirname(__file__), "db.json")
if os.path.exists(DB_JSON_PATH):
    try:
        migrated = db.migrate_from_json(DB_JSON_PATH)
        logger.info("Migrated %d records from db.json", migrated)
    except Exception as exc:
        logger.warning("Database migration failed: %s", exc)


def get_meilisearch_client() -> meilisearch.Client:
    """获取 Meilisearch 客户端

    Returns:
        配置好的 Meilisearch 客户端实例
    """
    api_key = MEILISEARCH_API_KEY if MEILISEARCH_API_KEY else None
    return meilisearch.Client(f"http://{MEILISEARCH_HOST}:{MEILISEARCH_PORT}", api_key)


def require_api_key(f):
    """API Key 认证装饰器

    验证请求中的 API Key，检查是否有效、是否被封禁，
    并应用速率限制。

    Args:
        f: 被装饰的视图函数

    Returns:
        装饰后的函数
    """

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        api_key = request.headers.get("Authorization", "").replace("Bearer ", "")

        if not api_key:
            return jsonify({"error": "缺少 API Key"}), 401

        # 验证 API Key 格式
        try:
            InputValidator.validate_api_key(api_key)
        except ValidationError:
            return jsonify({"error": "无效的 API Key 格式"}), 401

        # 检查 API Key 是否有效
        try:
            key_info = db.get_api_key(api_key)
        except DatabaseError:
            return jsonify({"error": "数据库查询失败"}), 500

        if not key_info:
            return jsonify({"error": "无效的 API Key"}), 401

        # 检查用户是否被封禁
        if key_info.get("is_banned", 0):
            return jsonify({"error": "账号已被封禁", "code": "banned"}), 403

        # 检查速率限制
        try:
            allowed, rate_info = rate_limiter.is_allowed(api_key)
        except RateLimitError:
            return jsonify({"error": "速率限制检查失败"}), 500

        if not allowed:
            response = jsonify(
                {
                    "error": "速率限制 exceeded",
                    "code": "rate_limit_exceeded",
                }
            )
            response.status_code = 429
            response.headers["X-RateLimit-Limit"] = str(rate_info["limit_minute"])
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(rate_info["reset_minute"])
            return response

        # 记录使用（审计日志失败不影响主流程）
        try:
            db.log_api_usage(api_key, request.path)
        except Exception:
            pass

        # 将用户信息附加到请求对象
        request.user_id = key_info.get("github_id", "")
        request.api_key = api_key
        request.github_login = key_info.get("github_login", "")
        request.rate_limit_info = rate_info

        return f(*args, **kwargs)

    return decorated


# ============ 错误处理中间件 ============


class APIError(Exception):
    """API 错误基类

    Attributes:
        message: 用户友好的错误信息
        status_code: HTTP 状态码
        code: 错误代码
    """

    def __init__(
        self, message: str, status_code: int = 500, code: str = "INTERNAL_ERROR"
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


@app.errorhandler(APIError)
def handle_api_error(error: APIError) -> Any:
    """处理 API 错误"""
    response = jsonify({"error": {"code": error.code, "message": error.message}})
    response.status_code = error.status_code
    return response


@app.errorhandler(404)
def handle_not_found(error: Any) -> Any:
    """处理 404 错误"""
    return (
        jsonify(
            {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "The requested resource was not found",
                }
            }
        ),
        404,
    )


@app.errorhandler(500)
def handle_internal_error(error: Any) -> Any:
    """处理 500 错误

    生产环境不暴露内部错误信息，仅记录日志。
    """
    app.logger.exception("Internal server error")

    message = "An internal error occurred"
    if app.config.get("DEBUG"):
        message = str(error)

    return (
        jsonify({"error": {"code": "INTERNAL_ERROR", "message": message}}),
        500,
    )


@app.errorhandler(ValidationError)
def handle_validation_error(error: ValidationError) -> Any:
    """处理验证错误"""
    return (
        jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(error)}}),
        400,
    )


# ============ 认证端点 ============


@app.route("/api/auth/login")
def auth_login() -> Any:
    """跳转 GitHub 登录"""
    if not GITHUB_CLIENT_ID:
        return jsonify({"error": "GitHub OAuth 未配置"}), 500

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    return redirect(
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={SITE_URL}/api/auth/callback"
        f"&scope=read:user"
        f"&state={state}"
    )


@app.route("/api/auth/callback")
def auth_callback() -> Any:
    """OAuth 回调处理"""
    error = request.args.get("error")
    if error:
        return jsonify({"error": f"授权失败: {error}"}), 400

    code = request.args.get("code")
    state = request.args.get("state")

    if state != session.get("oauth_state"):
        return jsonify({"error": "状态验证失败"}), 400

    # 换取 access_token
    token_response = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
        },
        headers={"Accept": "application/json"},
    )

    if token_response.status_code != 200:
        return jsonify({"error": "获取 token 失败"}), 400

    access_token = token_response.json().get("access_token")
    if not access_token:
        return jsonify({"error": "获取 token 失败"}), 400

    # 获取用户信息
    user_response = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"token {access_token}"},
    )

    if user_response.status_code != 200:
        return jsonify({"error": "获取用户信息失败"}), 400

    github_user = user_response.json()
    github_id = str(github_user["id"])
    github_login = github_user.get("login", "")

    # 保存或更新用户
    try:
        user = db.get_user_by_github_id(github_id)
    except DatabaseError:
        return jsonify({"error": "数据库查询失败"}), 500

    if not user:
        # 新用户
        api_key = secrets.token_urlsafe(32)
        try:
            db.create_api_key(
                api_key,
                {
                    "github_id": github_id,
                    "github_login": github_login,
                    "credits": rate_limiter.limits.get("per_month", 2000),
                    "credits_used": 0,
                },
            )
        except DatabaseError:
            return jsonify({"error": "创建用户失败"}), 500
    else:
        # 现有用户，更新登录信息
        api_key = user.get("key")
        try:
            db.update_api_key(
                api_key,
                {
                    "github_login": github_login,
                },
            )
        except DatabaseError:
            return jsonify({"error": "更新用户信息失败"}), 500

    # 跳转回控制台
    return redirect("/api/console.html#token=" + api_key)


@app.route("/api/auth/logout")
def auth_logout() -> Any:
    """退出登录"""
    session.clear()
    return redirect("/")


# ============ API Key 端点 ============


@app.route("/api/keys", methods=["GET"])
def get_keys() -> Any:
    """获取用户的 API Key"""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")

    if not api_key:
        return jsonify({"error": "需要 API Key"}), 401

    try:
        InputValidator.validate_api_key(api_key)
    except ValidationError:
        return jsonify({"error": "无效的 API Key 格式"}), 401

    try:
        key_info = db.get_api_key(api_key)
    except DatabaseError:
        return jsonify({"error": "数据库查询失败"}), 500

    if not key_info:
        return jsonify({"error": "无效的 API Key"}), 401

    credits = key_info.get("credits", 0)
    credits_used = key_info.get("credits_used", 0)

    return jsonify(
        {
            "api_key": api_key,
            "credits_used": credits_used,
            "credits_remaining": max(0, credits - credits_used),
            "created_at": key_info.get("created_at", ""),
        }
    )


@app.route("/api/keys/regenerate", methods=["POST"])
def regenerate_key() -> Any:
    """重新生成 API Key"""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")

    if not api_key:
        return jsonify({"error": "需要 API Key"}), 401

    try:
        InputValidator.validate_api_key(api_key)
    except ValidationError:
        return jsonify({"error": "无效的 API Key 格式"}), 401

    try:
        key_info = db.get_api_key(api_key)
    except DatabaseError:
        return jsonify({"error": "数据库查询失败"}), 500

    if not key_info:
        return jsonify({"error": "无效的 API Key"}), 401

    # 删除旧 key
    try:
        db.delete_api_key(api_key)
    except DatabaseError:
        return jsonify({"error": "删除旧 API Key 失败"}), 500

    # 生成新 key，保留所有用户信息
    new_key = secrets.token_urlsafe(32)
    try:
        db.create_api_key(
            new_key,
            {
                "github_id": key_info.get("github_id"),
                "github_login": key_info.get("github_login"),
                "email": key_info.get("email"),
                "avatar_url": key_info.get("avatar_url"),
                "is_admin": key_info.get("is_admin", 0),
                "credits": key_info.get("credits", 2000),
                "credits_used": key_info.get("credits_used", 0),
            },
        )
    except DatabaseError:
        return jsonify({"error": "创建新 API Key 失败"}), 500

    return jsonify({"api_key": new_key, "message": "API Key 已重新生成"})


# ============ 搜索端点 ============


@app.route("/api/search")
@require_api_key
def search() -> Any:
    """搜索

    参数:
    - q: 搜索关键词 (必需)
    - lang: 语言筛选 (zh, en, ja, es, nl, all)
    - limit: 返回结果数量 (1-20，默认10)
    - offset: 起始位置 (默认0)
    - domain: 站点筛选
    - tags: 标签筛选 (逗号分隔)
    - script: 中文简繁体筛选 (simplified, traditional, all)
    """
    try:
        query = InputValidator.validate_search_query(request.args.get("q", ""))
        lang = request.args.get("lang", "all")
        limit = InputValidator.validate_limit(request.args.get("limit", 10))
        offset = InputValidator.validate_offset(request.args.get("offset", 0))
        domain = request.args.get("domain", "")
        tags = request.args.get("tags", "")
        script = request.args.get("script", "all")
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    # 构建搜索参数
    search_params: Dict[str, Any] = {
        "q": query,
        "limit": 100,  # 先获取更多结果，再过滤
        "offset": 0,
        "attributesToHighlight": ["title", "content"],
        "highlightPreTag": "<em>",
        "highlightPostTag": "</em>",
        "attributesToCrop": ["content"],
        "cropLength": 200,
    }

    # 添加筛选（标签和域名）
    filters = []

    if tags:
        valid_tags = set(config.get("tags.available", []))
        for tag in tags.split(","):
            tag = tag.strip()
            if tag in valid_tags:
                # 转义单引号以防止 Meilisearch filter 注入
                escaped_tag = tag.replace("'", "\\'")
                filters.append(f"tags = '{escaped_tag}'")

    if domain:
        try:
            validated_domain = InputValidator.validate_domain(domain)
            # 转义单引号以防止 Meilisearch filter 注入
            escaped_domain = validated_domain.replace("'", "\\'")
            filters.append(f"domain = '{escaped_domain}'")
        except ValidationError:
            pass  # 忽略无效域名

    if filters:
        search_params["filter"] = " AND ".join(filters)

    # 搜索
    try:
        client = get_meilisearch_client()
        index = client.index(MEILISEARCH_INDEX)
        results = index.search(query, search_params)
    except Exception as exc:
        app.logger.error("Meilisearch search failed: %s", exc, exc_info=True)
        return jsonify({"error": "搜索服务暂时不可用"}), 500

    hits = results.get("hits", [])

    # 从 URL 路径检测语言并过滤（与 PHP 前端一致）
    if lang != "all" or script != "all":
        filtered_hits = []
        for h in hits:
            url = h.get("url", "")

            # 使用统一的语言检测函数
            doc_lang = detect_language_from_url(url)

            # 判断简繁体
            doc_script = "traditional" if doc_lang == "zh-hant" else "simplified"

            # 语言匹配检查
            if lang == "all":
                lang_match = True
            elif lang == "zh":
                lang_match = doc_lang in ("zh-cn", "zh-hant", "zh")
            else:
                lang_match = doc_lang == lang

            # 简繁体匹配检查
            script_match = script == "all" or doc_script == script

            if lang_match and script_match:
                h["_language"] = doc_lang
                h["_script"] = doc_script
                filtered_hits.append(h)

        hits = filtered_hits

    # 分页
    total = len(hits)
    hits = hits[offset : offset + limit]

    # 获取用户剩余配额并更新
    try:
        key_info = db.get_api_key(request.api_key)
        if key_info:
            credits = key_info.get("credits", 0)
            credits_used = key_info.get("credits_used", 0)
            new_credits_used = credits_used + 1

            db.update_api_key(
                request.api_key,
                {
                    "credits_used": new_credits_used,
                },
            )
        else:
            credits = 0
            credits_used = 0
            new_credits_used = 0
    except DatabaseError:
        credits = 0
        credits_used = 0
        new_credits_used = 0

    return jsonify(
        {
            "results": hits,
            "total": total,
            "query": query,
            "credits_used": new_credits_used,
            "credits_remaining": max(0, credits - new_credits_used),
            "limit": limit,
            "offset": offset,
        }
    )


# ============ 用户信息端点 ============


@app.route("/api/me")
@require_api_key
def get_me() -> Any:
    """获取当前用户信息"""
    try:
        key_info = db.get_api_key(request.api_key)
    except DatabaseError:
        return jsonify({"error": "数据库查询失败"}), 500

    credits = key_info.get("credits", 0) if key_info else 0
    credits_used = key_info.get("credits_used", 0) if key_info else 0

    return jsonify(
        {
            "user_id": request.user_id,
            "credits_used": credits_used,
            "credits_remaining": max(0, credits - credits_used),
            "created_at": key_info.get("created_at", "") if key_info else "",
        }
    )


# ============ 静态文件 ============


@app.route("/api/docs/<path:filename>")
def serve_docs(filename: str) -> Any:
    """提供文档静态文件"""
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), "..", "docs"), filename
    )


@app.route("/api/console.html")
def serve_console() -> Any:
    """提供控制台页面"""
    return send_from_directory(os.path.dirname(__file__), "console.html")


# ============ 管理员端点 ============


def require_admin(f):
    """管理员认证装饰器

    验证请求者是否为管理员用户。

    Args:
        f: 被装饰的视图函数

    Returns:
        装饰后的函数
    """

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        api_key = request.headers.get("Authorization", "").replace("Bearer ", "")

        if not api_key:
            return jsonify({"error": "需要 API Key"}), 401

        try:
            InputValidator.validate_api_key(api_key)
        except ValidationError:
            return jsonify({"error": "无效的 API Key 格式"}), 401

        try:
            key_info = db.get_api_key(api_key)
        except DatabaseError:
            return jsonify({"error": "数据库查询失败"}), 500

        if not key_info:
            return jsonify({"error": "无效的 API Key"}), 401

        github_login = key_info.get("github_login", "")

        if github_login not in ADMIN_USERS:
            return jsonify({"error": "需要管理员权限"}), 403

        request.admin_user = key_info.get("github_id", "")
        request.admin_login = github_login

        return f(*args, **kwargs)

    return decorated


@app.route("/api/admin/users")
@require_admin
def admin_list_users() -> Any:
    """获取所有用户列表"""
    try:
        users = db.list_api_keys()
    except DatabaseError:
        return jsonify({"error": "数据库查询失败"}), 500

    user_list = []
    for user in users:
        user_list.append(
            {
                "id": user.get("github_id", ""),
                "github_login": user.get("github_login", ""),
                "created_at": user.get("created_at", ""),
                "credits": user.get("credits", 0),
                "credits_used": user.get("credits_used", 0),
                "banned": bool(user.get("is_banned", 0)),
            }
        )
    return jsonify({"users": user_list, "total": len(user_list)})


@app.route("/api/admin/users/<user_id>/ban", methods=["POST"])
@require_admin
def admin_ban_user(user_id: str) -> Any:
    """封禁用户

    Args:
        user_id: GitHub 用户 ID
    """
    try:
        user = db.get_user_by_github_id(user_id)
    except DatabaseError:
        return jsonify({"error": "数据库查询失败"}), 500

    if not user:
        return jsonify({"error": "用户不存在"}), 404

    try:
        db.update_api_key(
            user.get("key"),
            {
                "is_banned": 1,
            },
        )
    except DatabaseError:
        return jsonify({"error": "封禁用户失败"}), 500

    return jsonify({"message": "用户已封禁", "user_id": user_id})


@app.route("/api/admin/users/<user_id>/unban", methods=["POST"])
@require_admin
def admin_unban_user(user_id: str) -> Any:
    """解封用户

    解封用户并生成新的 API Key。

    Args:
        user_id: GitHub 用户 ID
    """
    try:
        user = db.get_user_by_github_id(user_id)
    except DatabaseError:
        return jsonify({"error": "数据库查询失败"}), 500

    if not user:
        return jsonify({"error": "用户不存在"}), 404

    # 生成新的 API Key
    new_key = secrets.token_urlsafe(32)
    old_key = user.get("key")

    try:
        # 删除旧 key，创建新 key（保留所有用户信息并解封）
        db.delete_api_key(old_key)
        db.create_api_key(
            new_key,
            {
                "github_id": user.get("github_id"),
                "github_login": user.get("github_login"),
                "email": user.get("email"),
                "avatar_url": user.get("avatar_url"),
                "is_admin": user.get("is_admin", 0),
                "credits": user.get("credits", 2000),
                "credits_used": user.get("credits_used", 0),
            },
        )
    except DatabaseError:
        return jsonify({"error": "解封用户失败"}), 500

    return jsonify({"message": "用户已解封", "user_id": user_id, "api_key": new_key})


# ============ 健康检查 ============


@app.route("/api/health")
def health() -> Any:
    """健康检查端点"""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(config.env_var("API_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
